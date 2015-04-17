#pylint: disable=W0703,W0141,W0105
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
Created on Apr 25, 2014

@author: biyu
'''
import json
import logging
import os
from pylons import request, response, config
import pylons
import signal
import traceback

from agent.lib import manifestutil, configutil, utils
from agent.lib.agent_globals import stopAgentGlobals
from agent.lib.agent_thread.agent_update import AgentUpdate
from agent.lib.agent_thread.safe_shutdown import SafeShutdown
from agent.lib.base import BaseController
from agent.lib.errors import Errors, AgentException
from agent.lib.result import statusResult, errorResult, doneResult
from agent.lib.security.agentauth import authorize
from agent.lib.utils import trackable
import gc
import cPickle
import sys
from pympler.asizeof import asizeof
from beaker.converters import asbool


LOG = logging.getLogger(__name__)

class AgentactionController(BaseController):
    """ Action Controller class.  Responsible for all actions of a service/agent """

    @authorize()
    @trackable()
    def shutdown(self):
        """ This controller shutdown the agent.
        This should not be exposed to external usage.
        This should only be used for testing and also for self update.
        """

        LOG.info('[AGENT_SUICIDE] shutdown called.  exiting the agent. This is an expected behavior when rest api shutdown is called. ')
        stopAgentGlobals()
        pid = os.getpid()
        if (hasattr(signal, 'SIGKILL')):
            os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGTERM)

    @authorize()
    @trackable()
    def safeshutdown(self):
        """ This controller shutdown the agent.
        This should not be exposed to external usage.
        This should only be used for testing and also for self update.
        """

        LOG.info('[AGENT_SUICIDE] safe shutdown called.  exiting the agent. This is an expected behavior when rest api shutdown is called. ')
        try:
            appGlobal = config['pylons.app_globals']
            shutdownThread = SafeShutdown(appGlobal.threadMgr)
            self.injectJobCtx(shutdownThread)
            shutdownThread.start()
            shutdownThread.threadMgrEvent.wait()

            return statusResult(request, response, shutdownThread, controller = self)

        except Exception as excep:
            msg = 'Unknown error for safeshutdown %s - %s' % (str(excep), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = msg, controller = self)

    @authorize()
    @trackable()
    def reloadmonitors(self):
        """ reload all monitors.
        """
        appGlobal = pylons.config['pylons.app_globals']
        appGlobal.agentMonitor.reloadMonitors()

        return doneResult(request, response, controller = self)

    @authorize()
    @trackable()
    def selfupdate(self):
        """ agent selfupdate through api
        """
        LOG.info('selfupdate agent with body: %s', request.body)
        try:
            appGlobal = config['pylons.app_globals']
            wisbVersion = None
            wisbSource = None

            if request.body:
                requestjson = json.loads(request.body)
                if 'version' not in requestjson:
                    raise AgentException(Errors.INVALID_REQUEST, 'version is required')
                
                wisbVersion = requestjson['version']
                wisbSource = requestjson['wisbSource'] if 'wisbSource' in requestjson else configutil.getConfig('selfupdate_source')
                skipProp = asbool(requestjson['skipProp']) if 'skipProp' in requestjson else True

            updateThread = AgentUpdate(appGlobal.threadMgr, wisbVersion, wisbSource, skipProp = skipProp)
            self.injectJobCtx(updateThread)

            updateThread.start()
            updateThread.threadMgrEvent.wait()

            return statusResult(request, response, updateThread, controller = self)

        except AgentException as aexcep:
            return errorResult(request, response, error = aexcep.getCode(),
                               errorMsg = aexcep.getMsg(), controller = self)

        except Exception as excep:
            msg = 'Unknown error for agent update(%s) - %s - %s' % (wisbVersion, str(excep), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = msg, controller = self)

    @authorize()
    @trackable()
    def cancelSelfUpdate(self):
        """ cancel an in-flight agent selfupdate
        """
        appGlobal = config['pylons.app_globals']
        catThreads = appGlobal.threadMgr.getThreadByCat(AgentUpdate.THREAD_NAME, fastbreak = False)
        result = {}

        for catThread in catThreads:
            catThread.stop()
            result['uuid'] = catThread.getUuid()

        return doneResult(request, response, result = result, controller = self)
    
    @trackable()
    def getConfig(self):
        """ get config overrides """
        LOG.info('get config overrides for agent')
        result = {}
        try:
            result = manifestutil.readJsonServiceMeta('agent', ['configs'])
            return doneResult(request, response, result = result, controller = self)
            
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when clean agent configs %s - %s' %
                               (str(excep), traceback.format_exc(2)), controller = self)
        

    @authorize()
    @trackable()
    def pokeConfig(self):
        """ config poke """
        LOG.info('config poke agent with body: %s', request.body)
        configs = None
        result = {}
        try:
            if request.body:
                body = json.loads(request.body)
                if 'configs' in body:
                    configs = body['configs']
                    result = manifestutil.updateServiceMetaFile('agent', {'configs': configs})
                    return doneResult(request, response, result = result, controller = self)
            
            raise AgentException(Errors.INVALID_REQUEST, 'Invalid request, expect configs in request body')
            
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when update agent configs %s - %s' %
                               (str(excep), traceback.format_exc(2)), controller = self)
        finally:
            # reload config overrides
            configutil.loadConfigOverrides()
    
    @authorize()
    @trackable()
    def cleanConfig(self):
        """ clean all configs """
        LOG.info('clean agent config overrides')
        result = {}
        try:
            result = manifestutil.updateServiceMetaFile('agent', {'configs': None})
            return doneResult(request, response, result = result, controller = self)
            
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when clean agent configs %s - %s' %
                               (str(excep), traceback.format_exc(2)), controller = self)
        finally:
            # reload config overrides
            configutil.loadConfigOverrides()
            
    @trackable()
    def getTaskSlaReport(self, task, threshold=0, starttime=0, fmt='raw'):
        """ get task SLA report """
        LOG.info('generating task SLA report')
        try:
            script = os.path.join(manifestutil.manifestPath('agent'), 'agent', 'cronus', 'scripts', 'perfmetric')
            LOG.info('task sla report script %s' % script)
            if not task or task == '':
                raise AgentException(Errors.INVALID_REQUEST, 'task name cannot be empty')
            tmp = [script, task, str(threshold), str(starttime), fmt]
            cmds = []
            for cmd in tmp:
                cmds.append(cmd.encode('ascii', 'ignore'))
            cmdout = utils.runsyscmdwstdout(cmds)
            result = json.loads(cmdout)
            return doneResult(request, response, result=result, controller = self)
            
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Error when getting task sla report %s - %s' %
                               (str(excep), traceback.format_exc(2)), controller = self)
         
    @trackable()
    def getExecOutput(self, uuid):
        """ get script output with an uuid """
        LOG.info('get ouput for %s' % uuid)
        try:
            script = os.path.join(manifestutil.manifestPath('agent'), 'agent', 'cronus', 'scripts', 'execoutput')
            LOG.info('execoutput script %s' % script)
            if not uuid or uuid == '':
                raise AgentException(Errors.INVALID_REQUEST, 'uuid cannot be empty')
            tmp = [script, uuid]
            cmds = []
            for cmd in tmp:
                cmds.append(cmd.encode('ascii', 'ignore'))
            cmdout = utils.runsyscmdwstdout(cmds)
            return cmdout
            
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Error when get execoutput %s - %s' %
                               (str(excep), traceback.format_exc(2)), controller = self)
            
    @trackable()            
    def getRoutes(self):
        """ print all available routes """
        mapper = config['routes.map']
        apistr = mapper.__str__()
        apis = apistr.splitlines()
        result = map(lambda x: x.strip(), apis)
        return doneResult(request, response, result=result, controller = self)


    @authorize()
    @trackable()
    def dumpMemory(self):
        """ dump what's in the class in memory """
        
        dumpFile = os.path.join(manifestutil.manifestPath('agent'), 'agent', 'logs', 'memory.pickle')
        with open(dumpFile, 'w') as dump:
            for obj in gc.get_objects():
                i = id(obj)
                size = sys.getsizeof(obj, 0)
                referents = [id(o) for o in gc.get_referents(obj) if hasattr(o, '__class__')]
                if hasattr(obj, '__class__'):
                    cls = str(obj.__class__)
                    cPickle.dump({'id': i, 'class': cls, 'size': size, 'referents': referents}, dump)
        
        return doneResult(request, response, controller = self)
    
    @trackable()
    def getSizeOfMgrs(self):
        """ get size of object """
        appGlobal = config['pylons.app_globals']
        
        result = {}
        result['threadmgr'] = asizeof(appGlobal.threadMgr)
        result['packagemgr'] = asizeof(appGlobal.packageMgr)
        result['montior'] = asizeof(appGlobal.agentMonitor)
        result['all'] = asizeof(appGlobal)
        
        return doneResult(request, response, result = result, controller = self)