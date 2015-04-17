#pylint: disable=W0703,R0904,W0105
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
""" Thread to perform service deletes """

from agent.lib.agent_thread.agent_thread import AgentThread
from pylons import config
from agent.lib.errors import Errors, AgentException
from agent.lib.utils import xstr
import traceback

import logging
LOG = logging.getLogger(__name__)

class AgentThreadCancel(AgentThread):
    """ Cancel distribution """

    def __init__(self, threadMgr, uuid):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = [uuid], name = 'cancel_agentthread')
        self.__uuid = uuid

    def doRun(self):
        """ Main body of the thread """
        try:
            appGlobal = config['pylons.app_globals']
            thread = appGlobal.threadMgr.getThreadByUuid(self.__uuid)
            # Check if indeed trying to stop only distribution client threads
            if thread is None:
                self._updateStatus(httpStatus = 500,
                                   error = Errors.AGENT_THREAD_NOT_CANCELABLE,
                                   errorMsg = 'Non-existing thread %s cannot be canceled' % self.__uuid)
                return

            if not (issubclass(thread.__class__, AgentThread)):
                self._updateStatus(httpStatus = 500,
                                   error = Errors.AGENT_THREAD_NOT_CANCELABLE,
                                   errorMsg = 'thread of type %s cannot be canceled' % xstr(thread.__class__))
                return

            self._updateStatus(progress = 50)
            #Ignore if thread is not alive
            if (thread.isAlive()):
                thread.stop()

            self._updateStatus(progress = 100)
        except AgentException as exc:
            msg = 'Could not cancel distribution thread with uuid %s %s' % (self.__uuid, exc.getMsg)
            self._updateStatus(httpStatus = 500, error = exc.getCode(), errorMsg = msg)
        except Exception as exc:
            code = Errors.UNKNOWN_ERROR
            msg = 'Could not cancel distribution thread with uuid ' + \
                self.__uuid + '(#' + str(code) + '). ' + traceback.format_exc(5)
            self._updateStatus(httpStatus = 500, error = code, errorMsg = msg)
