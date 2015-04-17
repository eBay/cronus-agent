#pylint: disable=R0904,W0105
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
""" Thread Manager """

import threading
import time
from agent.lib.errors import Errors, ConcurrentActivityException
from agent.lib.errors import AgentException

import logging
from agent.lib import manifestutil
from agent.lib.agent_thread.agent_thread import DummyThread
import copy

LOG = logging.getLogger(__name__)

class NullThreadMgr():
    """ thread manager that does nothing
    """
    def __init__(self):
        """ constructor"""
        pass

    def addThread(self, thread):
        """ Do nothing """
        pass

    def stop(self):
        """ Do nothing """
        pass

    def hasActive(self):
        """ any active thread? """
        return False

    def activeSize(self):
        """ # of active threads """
        return 0
    
NULL_THREADMGR = NullThreadMgr()

class ThreadMgr(threading.Thread):
    """ This class manages all the threads that we use in the system.
    It will be used to figure out the progress of all threads. """

    def __init__(self, garbageFreq = 60, maxThreadAge = 72000):
        """ constructor
        initialize the threads dictionary.
        Key = uuid of thread
        Value = tuple (timestamp, threadObj)
        """
        threading.Thread.__init__(self)

        self.__threads = {}
        self.__lock = threading.RLock()
        self.__garbageFreq = float(garbageFreq)
        self.__maxThreadAge = float(maxThreadAge)
        self.__rejectRequest = False
        self.__runGC = True

    ###############################################################
    # Methods to add/query threads in thread mgr
    ###############################################################

    def rejectRequest(self):
        """ stop this threadmgr from adding any thread """
        self.__rejectRequest = True

    def allowRequest(self):
        """ allow this threadmgr to add more threads """
        self.__rejectRequest = False

    def getUuids(self):
        """ return all the keys in the mgr """
        return self.__threads.keys()

    def getThreadByUuid(self, uuid):
        """ get the thread from uuid """
        ret = None
        pair = self.__threads.get(uuid)
        if pair:
            ret = pair[0]

        return ret

    def getThreadByCat(self, cat, onlylive = True, fastbreak = True):
        """ get thread by category """
        return self.getLiveThreadByCatsAndName([cat], None, onlylive, fastbreak)

    def hasLiveThreadByCat(self, cat):
        """ is there live thread by cat """
        catThreads = self.getThreadByCat(cat, onlylive = True, fastbreak = True)
        if catThreads:
            return True
        return False

    def getLiveThreadByCatsAndName(self, cats, name, onlylive = True, fastbreak = True, haslock = False):
        """ get live threads by cats and name
            empty cats match ALL cats
            empty name match ALL names
        """
        ret = []
        # read only access, shallow copy is fine
        threads = self.__threads if haslock else copy.copy(self.__threads)
        for thread, _ in threads.itervalues():
            # check live
            if onlylive and not thread.isAlive():
                continue

            # check name
            if name and name != thread.getName():
                continue

            tCats = thread.getCat()
            try:
                #check overlap between cats
                found = False
                if not cats:
                    found = True
                else:
                    if not tCats:
                        continue

                    for cat in cats:
                        if cat in tCats:
                            found = True
                            break

                if not found:
                    continue

                ret.append(thread)
                if fastbreak:
                    break
                
            except ValueError:
                pass

        return ret

    def addThread(self, thread):
        """ add thread to the thread list
        this may fail as only 1 active thread for a category is allowed
        returns None if success
        return (errorCode, errorMessage)
        """
        uuid = thread.getUuid()
        cat_list = thread.getCat()

        # disallow threads with of the same categories
        if self.__rejectRequest:
            raise AgentException(Errors.AGENT_STOPPING, 'Agent is stopping')
            
        with self.__lock:
            if (uuid in self.__threads):
                errMsg = 'Warning: adding thread(%s) which already exists.  Ignoring add' % uuid
                LOG.warning(errMsg)
                return (errMsg, Errors.THREAD_ALREADY_ADDED)

            if cat_list:
                catThreads = self.getLiveThreadByCatsAndName(cat_list, None, haslock = True)
                for catThread in catThreads:
                    errMsg = ('Concurrent activity is detected (%s / %s) on resource (%s).  Another thread (%s / %s) already running '
                                % (thread.getName(), uuid, cat_list, catThread.getName(), catThread.getUuid()))
                    LOG.warning(errMsg)
                    # add this thread anyway, but raise an exception
                    # the catcher of this exception should set the correct errors
                    # and kill itself
                    # Bin: if thread has merge on found flag, do not add it to the map
                    # thread will merge with existing by change its uuid
                    if not thread.isMergeOnFound(): 
                        self.__threads[uuid] = (thread, None)
                    raise ConcurrentActivityException(errMsg, catThread.getUuid())

            #check thread counter
            maxCounter = getattr(thread, "MAX_INSTANCE", 0)
            if maxCounter:
                nameThreads = self.getLiveThreadByCatsAndName(None, thread.getName(), haslock = True)
                if maxCounter <= len(nameThreads):
                    errMsg = ('Too many instances are detected (%s / %s). Other threads uuids %s'
                            % (thread.getName(), uuid, [t.getUuid() for t in nameThreads]))
                    LOG.warning(errMsg)
                    # add this thread anyway, but raise an exception
                    # the catcher of this exception should set the correct errors
                    # and kill itself
                    self.__threads[uuid] = (thread, None)
                    raise AgentException(Errors.THREAD_CAT_ALREADY_EXISTS, errMsg)

            LOG.info('adding thread: %s with cat %s' % (uuid, cat_list))
            self.__threads[uuid] = (thread, None)

    ###############################################################
    # Methods for thread garbage collection
    ###############################################################

    def stopServiceThread(self):
        """ stop all service threads """
        from agent.controllers.service import ServiceController
        LOG.info("Stopping service thread")
        with self.__lock:
            services = ServiceController.getServices()
            for service in services:
                threads = self.getThreadByCat(ServiceController.serviceCat(service), fastbreak = False)
                for thread in threads:
                    thread.stop()

    def snapshot(self, killLiveWithStatus = None, withLock = False):
        """ take a snapshot of the current threadmap """
        data = self.getInfo(killLiveWithStatus, withLock)
        manifestutil.writeJson('agent', '.threadmgr', data)

    def stop(self):
        """ trigger to stop the GC
        cannot be undone
        should only be called right before shutdown """

        LOG.info("Stopping GC")
        self.__runGC = False
        self.__rejectRequest = True
        # dump thread status to json
        killStatus = {}
        killStatus['httpStatus'] = 500
        killStatus['error'] = Errors.THREAD_KILLED_AGENT_RESTART
        killStatus['errorMsg'] = 'thread killed, agent restart'
        
        data = self.getInfo(killLiveWithStatus = killStatus, withLock=True)
        manifestutil.writeJson('agent', '.threadmgr', data)

    def run(self):
        """ thread mgr garbage collection routine.
        This should be the only function that removes threads from the thread hash
        """
        # load persisted thread status from last shutdown
        try:
            data = manifestutil.readJson('agent', '.threadmgr')
            if data is not None and 'threads' in data:
                threads = data['threads']
                for athread in threads:
                    uuid = athread['uuid']
                    status = athread['status']
                    dummyThread = DummyThread(self, uuid, status)
                    dummyThread.start()
        except BaseException:
            pass # ignore any exception

        while (self.__runGC == True):
            time.sleep(float(self.__garbageFreq))

            with self.__lock:
                for uuid in self.__threads.keys():
                    value = self.__threads[uuid]
                    thread = value[0]
                    timestamp = value[1]

                    if (timestamp == None):
                        if (not thread.isAlive()):
                            self.__threads[uuid] = (thread, time.time())
                        continue

                    if (time.time() > timestamp + self.__maxThreadAge):
                        LOG.info("removing thread (%s): oldtimestamp (%d): thresh(%d): time(%d)"
                                  % (uuid, timestamp, self.__maxThreadAge, time.time()))
                        del self.__threads[uuid]

    def getInfo(self, killLiveWithStatus=None, withLock=False):
        """ info of all threads """
        result = {}
        
        if not withLock:
            self.gatherInfo(result, killLiveWithStatus)
        else:
            with self.__lock:
                self.gatherInfo(result, killLiveWithStatus)
                
        return result

    def gatherInfo(self, result, killLiveWithStatus):
        """ gather threads info """
        threads_result = []
        completed, alived = 0, 0
        for uuid, value in self.__threads.iteritems():
            thread = value[0]
            timestamp = str(value[1]) if value[1] is not None else ''
            alive = thread.isAlive()
            thtype = thread.__class__.__name__
            if alive:
                alived += 1
                threads_result.append({'uuid':uuid, 'type':thtype, 'alive':str(alive)})
            else:
                completed += 1
                tstatus = killLiveWithStatus if (thread.isAlive() and killLiveWithStatus) else thread.getStatus() 
                threads_result.append({'uuid':uuid, 'type':thtype, 'alive':str(alive), 'completedby':timestamp, 'status':tstatus})
        
        result['total'] = str(completed + alived)
        result['completed'] = str(completed)
        result['active'] = str(alived)
        result['threads'] = threads_result        

    def hasActive(self):
        """ any active thread? """
        return int(self.getInfo()['active']) > 0

    def activeSize(self):
        """ # of active threads """
        return int(self.getInfo()['active'])

