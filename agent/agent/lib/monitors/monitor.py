#pylint: disable=W0703, W0141, R0912, R0914, R0915, E1121, E1101, W0612, C0302,W0105
'''
Copyright 2014 eBay Software Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
""" Monitor Manager """

from agent.controllers.manifest import ManifestController
from agent.lib import manifestutil, utils, agenthealth, configutil
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.errors import AgentException, Errors
from agent.lib.scheduler import ThreadedScheduler
from paste.deploy.converters import asbool
from threading import Lock
import copy
import logging
import os
import pylons
import sys
import time
import traceback
from agent.lib.processify import processify
from pympler.asizeof import asizeof


LOG = logging.getLogger(__name__)

METRIC_TAGS_KEY = 'monitoring.metric.tags'
METRIC_TYPE_KEY = 'monitoring.metric.type'
METRIC_CONTEXT = 'monitoring.context'

# allowable resolutions accepted
METRIC_RESOLUTION_SECS = [600.0, 300.0, 60.0, 30.0, 10.0, sys.float_info.min]
METRIC_RESOLUTION_SECS_STR = ['600', '300', '60', '30', '10']

#cmd locks that prevents launching of more subprocess if the previous one has not completed
CMD_LOCKS = {}
CMD_FAILURES = {}

class AgentMonitor():
    """ AgentMonitor class
    This class is responsible for monitoring the agent and all services under it's management
    """

    def __init__(self):
        """ Constructor of the Agent Monitor """
        self.__appGlobal = pylons.config['pylons.app_globals']

        # monitor tasks already scheduled, sample: {(service1,manifest):[monitorReportTask1, monitorTask1, monitorTask2]}
        self.__monitorTasks = {}
        
        # monitor values, sample: {(service1,monitor): {cpu:[50%,ts,pre-ts], memory:[100,ts,pre-ts]}}
        self.__monitorValues = {}
        
        # monitor messages, eg: {(service, monitor): [{'t:name':[tag,ts,ts]},{cpu:[50,ts,ts],disk:[10,ts,ts]},{...}]}
        self.__monitorMessages = {}
        
        # monitor tags, eg: {(service, monitor): [{tag:tagv},{tag:tagv}]}
        self.__monitorTags = {}

        # monitor script probation switch        
        self.__probationEnabled = asbool(pylons.config['monitor_probation_enabled'])
        
        # metrics split count per cal 4k payload limitation
        self.__metricSplitCount = int(pylons.config['cal_metric_split_count']) if 'cal_metric_split_count' in pylons.config else 20

        # schedule a task with scheduler
        self.__monitorSch = ThreadedScheduler()

        # agent monitors
        self._addAgentMonitors()

        # semaphore
        self.__monitorSchLock = Lock()

        # semaphore for monitor change
        self.__addMonitorLock = Lock()
        
    def start(self):
        ''' starts monitor '''
        with self.__monitorSchLock:
            self.__monitorSch.start()

    def stop(self):
        ''' stop monitor '''
        with self.__monitorSchLock:
            self.__monitorSch.stop()

    def dumpMonitorValues(self):
        ''' dump all monitor values as json string '''
        result = {}
        for (service, mname) in self.__monitorValues:
            key = '%s.%s' % (service, mname)
            result[key] = self.__monitorValues[(service, mname)]
        result['values'] = asizeof(self.__monitorValues)
        result['tasks'] = asizeof(self.__monitorTasks)
        result['messages'] = asizeof(self.__monitorMessages)
        result['tags'] = asizeof(self.__monitorTags)
        result['messagekeys'] = '%s' % self.__monitorMessages
        return result

    def reloadMonitors(self):
        ''' reload service monitors '''
        try:
            self.checkMonitorChanges(forceLoad=True)

        except Exception as excep:
            LOG.error('Failed reload monitors (%s) - %s' % (excep, traceback.format_exc(5)))


    def checkAgentHealth(self):
        '''
        Reports the agent health (as of now, based on disk utilization and file descriptors usage)
        as an attribute to be shown in ValidateInternals page.
        '''
        try:
            (health, healthfactor) = agenthealth.checkAgentHealth()

            self.__appGlobal.agentHealth = health
            self.__appGlobal.agentHealthFactor = healthfactor
            
        except Exception as excep:
            LOG.error('Fail to get agent health (%s) - %s' % (excep, traceback.format_exc(5)))

    def checkMonitorChanges(self, forceLoad=False):
        ''' check if there is service or manifest changes, and start/stop monitors'''
        try:

            serviceActiveManifests = manifestutil.getAllServiceActiveManifests()

            #if service is created or activeManifest has been changed
            for (service, activeManifest) in serviceActiveManifests:
                needSchedule = True
                if not forceLoad:
                    for (aservice, amanifest) in self.__monitorTasks.keys():
                        if service == aservice and activeManifest == amanifest:
                            needSchedule = False
                            continue

                if needSchedule:
                    if (service, activeManifest) in self.__monitorTasks:
                        # cancel the same existing if any
                        for task in self.__monitorTasks[(service, activeManifest)]:
                            self.__monitorSch.cancel(task)
                            
                    with self.__addMonitorLock:        
                        self._addMonitors(service, activeManifest)

            #if the service or manifest is deleted
            for key in self.__monitorTasks.keys():
                if key not in serviceActiveManifests:
                    service, _ = key
                    for task in self.__monitorTasks[key]:
                        self.__monitorSch.cancel(task)
                    del self.__monitorTasks[key]
                        
        except OSError:
            # ignore this type of error.  it's too verbose
            pass
        except Exception as excep:
            LOG.error('Cannot check monitor changes (%s) - %s' % (excep, traceback.format_exc(5)))

    def _addAgentMonitors(self):
        ''' add agent monitors, agent health, local manifest '''
        service = 'agent'

        # agent default, snapshot values to show
        self.__monitorValues[(service, 'default')] = {}
        self.__monitorValues[(service, 'agentmon')] = {}
        
        # outgoing messages 
        self.__monitorMessages[(service, 'default')] = {}
        self.__monitorMessages[(service, 'agentmon')] = {}

        # agent health, schedule only, no reporting
        monitorname = 'AgentHealth'
        interval = float(pylons.config['agent_health_report_interval'])
        self.__monitorSch.add_interval_task(self.checkAgentHealth, monitorname, 30, interval, [], None)

        # check service/manifest changes to load/unload monitors, no reporting
        self.__monitorSch.add_interval_task(self.checkMonitorChanges,
                                                'checkMonitorChanges', 1,
                                                float(pylons.config['monitor_check_timeinterval']),
                                                [], None)
        

    def _addMonitors(self, service, activeManifest):
        ''' add monitors for a service's activeManifest '''
        monitorTasks = []
        self.__monitorTasks[(service, activeManifest)] = monitorTasks
        
        # metric tags
        metricTags = {}
        # add default metric tags
        metricTags['fqdn'] = utils.fqdn
        # read tags from agent
        agtMetricTags = manifestutil.readJsonServiceMeta('agent', [METRIC_TAGS_KEY])
        if agtMetricTags and METRIC_TAGS_KEY in agtMetricTags:
            metricTags.update(agtMetricTags[METRIC_TAGS_KEY])
        # read tags from service
        if (service != 'agent'):
            serviceMetricTags = manifestutil.readJsonServiceMeta(service, [METRIC_TAGS_KEY])
            if  serviceMetricTags or METRIC_TAGS_KEY in serviceMetricTags:
                metricTags.update(serviceMetricTags[METRIC_TAGS_KEY])

        # all packages in this manifest
        packages = ManifestController.getPackages(service, os.path.basename(activeManifest))

        # metric tags for externally passed in metrics
        # monitorTags = {additionaltags_dict, datatype_dict, ctx(env.pool.host), appType(Monitor|custom), monitorType(Cronus|CronusApplication)}
        self.__monitorTags[service] = {'default': (metricTags, {}, {})}
        self.__monitorValues[(service, 'default')] = {}
        self.__monitorMessages[(service, 'default')] = {}

        # a unique index for all monitors in the service
        for package in packages:

            # load monitor setting from cronus.ini
            pkgConfigs = manifestutil.getPackageInitConfig(service, activeManifest, package)
            
            if pkgConfigs is not None and 'monitors' in pkgConfigs:
                
                metricCtx = pkgConfigs[METRIC_CONTEXT] if METRIC_CONTEXT in pkgConfigs else {}
                
                metricTypes = {}
                if METRIC_TYPE_KEY in pkgConfigs and pkgConfigs[METRIC_TYPE_KEY]:
                    metricTypes = pkgConfigs[METRIC_TYPE_KEY]
                    
                if METRIC_TAGS_KEY in pkgConfigs and pkgConfigs[METRIC_TAGS_KEY]:
                    metricTags.update(pkgConfigs[METRIC_TAGS_KEY])
                    
                
                monitors = pkgConfigs['monitors']
                for monitor in monitors:
                    try:
                        m_name = str(monitor['name'])
                        
                        # metric tags for externally passed in metrics
                        # monitorTags = {additionaltags_dict, datatype_dict, ctx(env.pool.host), appType(Monitor|custom), monitorType(Cronus|CronusApplication)}
                        self.__monitorTags[service][m_name] = (metricTags, metricTypes, metricCtx)

                        # now normalize the interval to one allowable by EVPS (downcast)
                        if 'reportIntervalSec' not in monitor:
                            continue
                        m_interval = float(monitor['reportIntervalSec'])
                        m_interval = self._normalizeResolution(m_interval)

                        m_timeout = float(monitor['timeoutSec']) if 'timeoutSec' in monitor else m_interval
                        m_timeout = max(1, min(m_interval-1, m_timeout))
                        m_items = monitor['items'] if 'items' in monitor else []

                        # prime monitor value store
                        self.__monitorValues[(service, m_name)] = {}
                        self.__monitorMessages[(service, m_name)] = {}

                        mi_idx = 0
                        for m_item in m_items:
                            if 'type' not in m_item:
                                continue
                            mi_idx += 1
                            mi_type = m_item['type']
                            mi_cmd = None
                            if 'script' == mi_type:
                                mi_script = m_item['script']
                                mi_cmd = manifestutil.getMonitorScriptPath(service, activeManifest, package, mi_script)
                            else:
                                # unknown type, skip
                                LOG.error('Unknown monitor item type %s, can only be script' % mi_type)
                                continue

                            # schedule monitor
                            m_sch_name = '%s.%s' % (service, m_name)
                            try:
                                self.__monitorMessages[(service, m_name)][mi_cmd] = []
                                task = self.__monitorSch.add_interval_task(self._runMonitor, '%s.%s' % (m_sch_name, str(mi_idx)), 0, float(m_interval),
                                    [mi_type,mi_cmd,service,m_name,m_timeout,(str(int(round(m_interval))),metricTags,metricTypes,metricCtx)],None)
                                monitorTasks.append(task)
                            except Exception as excep:
                                LOG.error('Cannot add monitor task for %s.%s - (%s) %s' % (m_sch_name, str(mi_idx), excep, traceback.format_exc(5)))

                    except Exception as excep1:
                        LOG.error('Cannot add report task for %s.%s - (%s) %s' % (service, m_name, excep1, traceback.format_exc(5)))
                        

    def runReport(self, service, monitorname, cmd, metricoptions):
        '''
        20130326 Change to public  Runs reporting to send data. Should not fail or scheduler will fail.
        metricoptions = {resolution, additionaltags_dict, datatype_dict, metadata_ctx_dict)}
        '''
        monitorKey = (service, monitorname)
        
        metricResSec = str(metricoptions[0])
        metricTags = metricoptions[1]
        metricTypes = metricoptions[2]
        metricCtx = metricoptions[3]
        try:
            # if no need to send it out, just skip and return
            isPublishing = configutil.getConfigAsBool('agent_monitor_publish_enabled')
            if isPublishing:
                self._connIfNeeded(metricCtx)

            #report monitor status for new values
            tags = []
            try:
                LOG.debug("self.__monitorMessages %s" % self.__monitorMessages)

                # resolution
                tags.append(('m:resSecs', metricResSec))
                # additional tags
                for tkey, tvalue in metricTags.iteritems():
                    tag = 't:%s' % tkey
                    tags.append((tag, tvalue))
                
                monitorMsg = None
                if monitorKey in self.__monitorMessages and cmd in self.__monitorMessages[monitorKey]:
                    messages = copy.copy(self.__monitorMessages[monitorKey][cmd])
                    del self.__monitorMessages[monitorKey][cmd][:]
                    
                    if not isPublishing:
                        return
                    
                    for message in messages:
                        
                        if monitorMsg is not None:
                            self._publishMonitorMessage(monitorMsg)

                        monitorMsg = self._createMonitorMessage(metricoptions, message)
                        
                        # pre-processing tags from user script
                        overridingTags = set()
                        for (key, value) in message.items():
                            if key.startswith('t:'):
                                overridingTags.add(key)
                                    
                        for tkey, tvalue in tags:
                            if tkey not in overridingTags:
                                self._addTagToMessage(monitorMsg, (tkey, tvalue))
                        
                        for (key, msgvalue) in message.items():
                            # there is possibility that we don't see new/updated data, in that case,
                            # prohibit hb creation so as to not corrupt internal transaction stack
                            value, timestamp, preTimestamp = msgvalue[0], msgvalue[1], msgvalue[2]
                            if timestamp != preTimestamp:
                                msgvalue[2] = timestamp

                                if not key.startswith('t:'):
                                    # add metric types, default g:
                                    newKey = '%s:%s' % (metricTypes[key] if (key in metricTypes) else 'g', key)
                                    self._addValueToMessage(monitorMsg, (newKey, value))


                    if monitorMsg is not None:
                        self._publishMonitorMessage(monitorMsg)
                        
            except Exception as excep:
                LOG.error('error when update monitor for %s status (%s) - %s' % (service, excep, traceback.format_exc(5)))

        except OSError:
            pass # ignore this type of error.  it's too verbose
        except Exception as excep:
            LOG.error('Cannot send monitor heartbeat (%s) - %s' % (excep, traceback.format_exc(5)))


    def _putToProbation(self, cmd):
        ''' set a command to probation
            cmd_failures[0]: skip count since probation
            cmd_failures[1]: skip limit 2 ** cmd_failures[1] since probation, it grows exponentially
        '''
        if self.__probationEnabled:
            if cmd in CMD_FAILURES:
                if CMD_FAILURES[cmd][1] < 10:
                    CMD_FAILURES[cmd][1] += 1
                CMD_FAILURES[cmd][0] = 0
            else:
                CMD_FAILURES[cmd] = [0, 0]
            LOG.info('cmd %s put in probation for %s' % (cmd, CMD_FAILURES[cmd][1]))
            
    def _releaseFromProbation(self, cmd):
        ''' release a command from probation '''
        if self.__probationEnabled and cmd in CMD_FAILURES:
            del CMD_FAILURES[cmd]
            LOG.info('cmd %s released from probation for' % cmd)
        
    def _shouldRunMonitor(self, cmd):
        ''' should run a monitoring cmd '''
        shouldRun = True
        if cmd in CMD_LOCKS:
            # cmd is locked
            LOG.info('Previous monitor cmd %s not yet complete, skip launching a new one' % cmd)
            shouldRun = False
        
        if self.__probationEnabled and cmd in CMD_FAILURES:
            # cmd is in probation
            CMD_FAILURES[cmd][0] += 1
            if CMD_FAILURES[cmd][0] < (2 ** CMD_FAILURES[cmd][1]):
                shouldRun = False
                
        return shouldRun

    
    def _runMonitor(self, monitortype, cmd, service, monitorname, timeout, metricoptions):
        '''
        Runs monitor script. Should not fail or scheduler will fail.
        CAL logging:
        System wide metrics by agent:
        Before enrollment -> Logs using default GLOBAL context connection
        After enrollment -> Establishes new connection based on headers obtained from hw path (of format .env.clusterNode.computeName) and uses it
        App wide metrics by apps:
        Establishes connection for each service based on headers obtained from service instance name (of format .env.appService.serviceInstanceName)
        Note: In case of invalid format in both cases, CAL logging is ignored
        '''
        if not self._shouldRunMonitor(cmd):
            return
        
        try:
            CMD_LOCKS[cmd] = None
            if 'script' == monitortype:
                result = self._executeCommand(cmd, timeout)
            else:
                # unknown type, skip
                return
            
            if type(result) == dict:
                self.processScriptOuput(service, monitorname, cmd, [result])
            elif type(result) == list:
                self.processScriptOuput(service, monitorname, cmd, result)
            else:
                err_msg = 'monitor %s result error, format not accepted: %s' % (cmd, result)
                LOG.warning(err_msg)
                self._putToProbation(cmd)
                return
            
            self.runReport(service, monitorname, cmd, metricoptions)
            self._releaseFromProbation(cmd)

        except Exception as excep:
            err_msg = 'Cannot run monitor (%s) - (%s) - (%s)' % (cmd, excep, traceback.format_exc(2))
            LOG.error(err_msg)
            self._putToProbation(cmd)
            
        finally:
            del CMD_LOCKS[cmd]
    

    def runExtMonitor(self, service, monitorstream, resSec, result, monitorgroup='default'):
        '''
        Report metrics from external
        '''
        LOG.debug('%s, %s, %s, %s' % (service, monitorstream, resSec, result))
        LOG.debug('%s' % self.__monitorTags)
        if resSec not in METRIC_RESOLUTION_SECS_STR:
            raise AgentException(Errors.MONITOR_INVALID_RESOLUTION, 
                                 'Invalid resolution %s, allowable values %s' % (resSec, ','.join(METRIC_RESOLUTION_SECS)))
        
        metricoptions = (resSec,) + (self.__monitorTags[service][monitorgroup] 
                                     if (service in self.__monitorTags and monitorgroup in self.__monitorTags[service]) 
                                     else (None, None, None, None, None))
        
        if (service, monitorgroup) not in self.__monitorMessages:
            self.__monitorMessages[monitorgroup] = {}
        if monitorstream not in self.__monitorMessages[(service, monitorgroup)]:
            self.__monitorMessages[(service, monitorgroup)][monitorstream] = []
        try:
            if type(result) == dict:
                self.processScriptOuput(service, monitorgroup, monitorstream, [result])
            elif type(result) == list:
                self.processScriptOuput(service, monitorgroup, monitorstream, result)
            else:
                err_msg = 'monitor %s result error, format not accepted: %s' % (monitorstream, result)
                LOG.warning(err_msg)
                return
            
            self.runReport(service, monitorgroup, monitorstream, metricoptions)
            
        except Exception as excep:
            err_msg = 'Cannot run monitor %s error (%s) - (%s)' % (monitorstream, excep, traceback.format_exc(2))
            LOG.error(err_msg)

    
    def processScriptOuput(self, service, monitorname, cmd, result):
        '''20130326 Change to public ; process multiple key value pairs in result, with tags '''
        monitorKey = (service, monitorname)
        timeCur = time.time()
        tags = []
        tagPrefix = ''
        message = {}
        messages = self.__monitorMessages[monitorKey][cmd]
        count = 0
        for dic in result:
            if 'key' in dic and 'value' in dic:
                count += 1
                key = str(dic['key'])
                
                if key == 'tagStart' or key == 'tagEnd':
                    if key == 'tagStart':
                        # start tags
                        if type(dic['value']) == dict:
                            tags.append(dic['value'])

                    elif key == 'tagEnd' and tags:
                        # end tags
                        tags.pop()
                            
                    tagFlat = []
                    if message:
                        messages.append(message)
                    message = {}
                    for tagDict in tags:
                        for tagk, tagv in tagDict.items():
                            message[('t:%s' % str(tagk))] = [str(tagv), timeCur, None]
                            tagFlat.append(('%s:%s' % (tagk, str(tagv))))
                    tagPrefix = '.' + '.'.join(tagFlat) + '.' if tagFlat else ''
                        
                else:
                    if count % self.__metricSplitCount == 0:
                        messages.append(message)
                        message = {}
                        for tagDict in tags:
                            for tagk, tagv in tagDict.items():
                                message[('t:%s' % str(tagk))] = [str(tagv), timeCur, None]
                        
                    value = str(dic['value'])
                    # time not logged in heart beat as it's auto inserted by client while logging
                    fqKey = ('%s%s' % (tagPrefix, key))
                    if monitorKey not in self.__monitorValues:
                        self.__monitorValues[monitorKey] = {}
                    if fqKey not in self.__monitorValues[monitorKey]:
                        rValue = [value, timeCur, None]
                        self.__monitorValues[monitorKey][fqKey] = rValue
                        message[key] = rValue 
                    else:
                        rValue = self.__monitorValues[monitorKey][fqKey]
                        rValue[0] = value
                        rValue[1] = timeCur
                        message[key] = rValue
                        
            else:
                # bad format, skip
                err_msg = 'monitor result for service %s error: %s' % (service, dic)
                LOG.debug(err_msg)
        
        if message:
            messages.append(message)

    def _normalizeResolution(self, userInterval):
        ''' normalize user specified resolution to one supported by EVPS '''
        m_interval = userInterval
        for idx, allowable_interval in enumerate(METRIC_RESOLUTION_SECS):
            if m_interval > allowable_interval:
                if idx == 0:
                    m_interval = allowable_interval
                else:
                    m_interval = METRIC_RESOLUTION_SECS[idx - 1]
                    break
        return m_interval

    @processify
    def _executeCommand(self, cmd, timeout = 2, service = None):
        ''' execute command '''
        execThread = ExecThread(None, cmd)
        execThread.setLogLevel('debug')
        execThread.run()

        # now wait for the threads to complete and update progress
        status = execThread.getStatus()
        if (status['error'] != None):
            return None
#             raise AgentException(status['error'], status['errorMsg'])

        return status['result']

    def _connIfNeeded(self, metricCtx):
        ''' connect to monitoring server if needed '''
        pass
        
    def _createMonitorMessage(self, metricmeta, message):
        '''
        this creates publishable message
        metricmeta tuple in (metricResSec, metricTags, metricTypes, metricCtx, appType, metricCat)
        '''
        return {}
        
    def _publishMonitorMessage(self, message):
        '''
        this publish the metrics to its destination, be it event bus, or local logs
        '''
        LOG.info(message)
        
    
    def _addValueToMessage(self, message, values):
        ''' add nvp to message '''
        message.put(values)
        
    
    def _addTagToMessage(self, message, tags):
        ''' add tag nvp to message '''
        message.put(tags)
    

