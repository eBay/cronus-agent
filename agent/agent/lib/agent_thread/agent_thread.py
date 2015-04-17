#pylint: disable=R0904,R0912,R0915,W0105
""" 
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

Agent Thread 
"""
import uuid
import threading
import thread
import time
from copy import deepcopy
import traceback

from agent.lib.errors import Errors, ConcurrentActivityException
from agent.lib.errors import AgentException

import logging
from agent.lib import contextutils, configutil
import json

LOG = logging.getLogger(__name__)
UUIDLOG = logging.getLogger('uuid')

class AgentThread(threading.Thread):
    """ All threads used by the agent should be of type agent thread.
    This thread will be used to generate ids, provide categories for the thread mgr. """

    def __init__(self, threadMgr, cat = None, name = 'agent_thread', mergeOnFound = False, reqChecksum = None):
        """ Constructor.
        Creates the uuid.
        Sets the category of this thread """
        threading.Thread.__init__(self)
        self.__lock = threading.Lock()
        self.__stop = False
        
        self._timeout = configutil.getConfigAsInt('agent_thread_timeout')
        self._progressTimeout = 0
        
        self.__lastProgress = None
        self.__timeoutAt = 0

        # thread event to mark when the thread has been added to threadMgr
        self.threadMgrEvent = threading.Event()
        self.threadMgrEvent.clear()

        # thread manager
        self._threadMgr = threadMgr

        # used by status
        self.__uuid = str(uuid.uuid4())
        self.__cat = cat
        self.__name = name
        self.__executionMsec = None
        
        self.__mergeOnFound = mergeOnFound
        self.__reqChecksum = reqChecksum

        # status
        self.__status = {'httpStatus': 200, 'progress': 0, 'fprogress': 0.0, 'result': None, 'error': None, 'errorMsg': None, 'executionMsec': None}

    ##############################################################
    # Thread Running Methods
    ##############################################################

    def run(self):
        """ run - register self with threadmgr """
        self.beforeRun()
        
        self.__timeoutAt += (time.time() + self._timeout)
        
        # start timer
        self.__executionMsec = time.time() * 1000

        try:
            self._threadMgr.addThread(self)
            self.threadMgrEvent.set()
            self.doRun()
            
        except ConcurrentActivityException as excep:
            # found existing, and merge with it if needed
            conflictUuid = excep.getConflictUuid() 
            if self.__mergeOnFound:
                if self.__reqChecksum:
                    conflictThread = self._threadMgr.getThreadByUuid(conflictUuid)
                    if conflictThread and isinstance(conflictThread, AgentThread) and conflictThread.getReqChecksum() == self.__reqChecksum:
                        LOG.info('Thread(%s / %s) merged with existing thread %s' % (self.__name, self.__uuid, excep.getConflictUuid()))
                        self.__uuid = excep.getConflictUuid()
                        self._updateProgress(0)
            else:
                self._updateStatus(httpStatus = 500, progress = 100,
                                   error = excep.getCode(), errorMsg = excep.getMsg())
                LOG.error('Thread(%s / %s) Caught ThreadMgr Exception - exiting (%s) - %s' % (self.__name, self.__uuid, excep, traceback.format_exc(5)))
            thread.exit()
                
        except AgentException, excep:
            self._updateStatus(httpStatus = 500, progress = 100,
                              error = excep.getCode(), errorMsg = excep.getMsg())
            LOG.error('Thread(%s / %s) Caught ThreadMgr Exception - exiting (%s) - %s' % (self.__name, self.__uuid, excep, traceback.format_exc(5)))
            thread.exit()

        except Exception, excep:
            LOG.error('Thread(%s / %s) Caught ThreadMgr Exception - exiting (%s) - %s' % (self.__name, self.__uuid, excep, traceback.format_exc(5)))
            thread.exit()
        
        finally:
            # doesn't hurt set twice since this event is telling whether it's registered by threadMgr
            self.threadMgrEvent.set()
            # calculate execution time
            executionMsec = time.time() * 1000 - self.__executionMsec
            self.__status['executionMsec'] = int(executionMsec)
            # log to uuid, only for user facing threads
            if self.__cat is not None:
                msg = json.dumps(self.status2msg())
                thtype = self.__class__.__name__
                guid = contextutils.getcontext(self, 'guid', 'na')
                UUIDLOG.info('%s output start type=%s, status=%s, guid=%s %s output end' % (self.__uuid, thtype, msg, guid, self.__uuid))
        
    def status2msg(self):
        """ status to msg for logging """
        res = {}
        
        if (self.__status['executionMsec'] != None):
            res['executionMsec'] = self.__status['executionMsec']

        if (self.__status['result'] != None):
            res['result'] = self.__status['result']

        # check if the result is an error not not
        if (self.__status['error'] == None):
            res['progress'] = self.__status['progress']
            
        else:
            res['errorMsg'] = self.__status['errorMsg']
            res['error'] = self.__status['error']
            
        return res
    
    def beforeRun(self):
        """ subclass override for logic before doRun, before timeout values applies"""
        pass

    def doRun(self):
        """ function for subclass override """
        raise NotImplementedError("doRun function not implemented")

    def setName(self, name):
        self.__name = name

    def getName(self):
        return self.__name if self.__name else threading.Thread.getName(self)
    
    def getReqChecksum(self):
        """ get request checksum """
        return self.__reqChecksum
    
    def setReqChecksum(self, reqChecksum):
        """ set request checksum """
        self.__reqChecksum = reqChecksum

    def isMergeOnFound(self):
        """ get merge on found flag """
        return self.__mergeOnFound
    
    def setMergeOnFound(self, mergeOnFound):
        """ set merge on found flag """
        self.__mergeOnFound = mergeOnFound

    def setTimeout(self, timeout):
        """ set the timeout of this thread
        timeout is the amount of seconds from now that you want the thread to timeout
        """
        self._timeout = timeout
        
    def getTimeout(self):
        """ get timeout value """
        return self._timeout
        
    def setProgressTimeout(self, timeout):
        """ set the progress timeout of this thread
        timeout is the amount of seconds you allow progress stay the same
        """
        self._progressTimeout = timeout
        
    def getProgressTimeout(self):
        """ get progress timeout value """
        return self._progressTimeout
        
    def extendTimeout(self, delta):
        """ extend timeoutAt by delta """
        self.__timeoutAt += delta
        self._timeout += delta

    def stop(self):
        """ stop this thread from running at the next check """
        self.__stop = True

    def isStopped(self):
        """ if thread is stopped or being stopped"""
        return self.__stop

    def _checkStop(self, triggerException = True, threadName = None):
        """ check if this thread should stop.  If so exit by throwing exception or return boolean value to indicate whether to stop """
        if threadName is None:
            threadName = self.getName()
        
        if (self.__stop):
            msg = 'Stopping %s(%s) as requested' % (threadName, self.__uuid)
            LOG.warning(msg)
            self._updateStatus(httpStatus = 500, error = Errors.AGENT_THREAD_STOPPED,
                              errorMsg = msg)
            if (triggerException):
                raise SystemExit(Errors.AGENT_THREAD_STOPPED, msg)
            else:
                return msg

        if (time.time() > self.__timeoutAt):
            msg = 'Timeout (%d) reached: stopping %s(%s)' % (self._timeout, threadName, self.__uuid)
            LOG.warning(msg)
            self._updateStatus(httpStatus = 500, error = Errors.AGENT_THREAD_TIMEDOUT,
                              errorMsg = msg)
            if (triggerException):
                raise SystemExit(Errors.AGENT_THREAD_TIMEDOUT, msg)
            else:
                return msg

        if (self._progressTimeout and self._progressTimeout > 0):
            if (self.__lastProgress == None or self.__status['fprogress'] > self.__lastProgress[0]):
                self.__lastProgress = (self.__status['fprogress'], time.time())
            if (self.__lastProgress[0] >= self.__status['fprogress'] and
                time.time() > self.__lastProgress[1] + self._progressTimeout):
                msg = 'Progress timeout (%d) second reached: stopping %s(%s)' % (self._progressTimeout, threadName, self.__uuid)
                LOG.warning(msg)
                self._updateStatus(httpStatus = 500, error = Errors.AGENT_THREAD_PROGRESS_TIMEDOUT,
                                  errorMsg = msg)
                if (triggerException):
                    raise SystemExit(Errors.AGENT_THREAD_PROGRESS_TIMEDOUT, msg)
                else:
                    return msg
        return None


    ##############################################################
    # Http Status Update Methods
    ##############################################################

    def getUuid(self):
        """ get uuid of this thread """
        return self.__uuid

    def getProgress(self):
        """ get uuid of this thread """
        return self.__status['progress']

    def getCat(self):
        """ get cat of this thread """
        return self.__cat

    def getStatus(self):
        """ get status of this thread """
        with self.__lock:
            status = deepcopy(self.__status)

        return status

    def _updateProgress(self, progress):
        """ ensure that the progress does not decrease
        @param progress - new progress to update to
        """
        if (progress > 100):
            LOG.warning('Ignoring attempt to set progress to %s: %s' % (str(progress),
                                                                        traceback.format_exc(2)))
            return

        if (progress < self.getStatus()['progress']):
            # make sure we don't go down in progress
            LOG.warning('Progress reduced from %s to %s' % (str(self.getStatus()['progress']),
                                                            str(progress)))
            progress = self.getStatus()['progress']

        self._updateStatus(progress = progress)

    def _updateStatus(self, httpStatus = None, progress = None, result = None, error = None, errorMsg = None):
        """ update status of this thread """
        with self.__lock:
            if (httpStatus != None):
                self.__status['httpStatus'] = int(httpStatus)
            if (progress != None):
                self.__status['progress'] = int(progress)
            if (progress != None):
                self.__status['fprogress'] = float(progress)
            if (result != None):
                self.__status['result'] = result
            if (error != None):
                self.__status['error'] = int(error)
            if (errorMsg != None):
                self.__status['errorMsg'] = errorMsg

    def _runExeThread(self, execThreadTuple):
        ''' run an execution thread, throw agent exception if it fails '''
        
        execThread, isDummy = execThreadTuple
        #dummy thread, ignore
        if isDummy:
            return {'progress': 0}
        
        execThread.run()

        status = execThread.getStatus()
        if (status['error'] != None):
            raise AgentException(status['error'], status['errorMsg'])
        
        return status

class DummyThread(AgentThread):
    ''' dummy thread used to recover persisted thread status '''
    def __init__(self, threadMgr, auuid, status):
        ''' constructor '''
        AgentThread.__init__(self, threadMgr, None, 'dummy_thread')
        self.__uuid = auuid
        self.__status = status

    def doRun(self):
        self._updateProgress(100)




