#pylint: disable=W0703,R0912,R0904,E1101,R0904,W0105
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
""" Thread to perform safe shutdown of agent """

from agent.lib.agent_globals import stopAgentGlobals
from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.errors import AgentException, Errors
import logging
import os
import pylons
import random
import time
import traceback
import signal

LOG = logging.getLogger(__name__)

class SafeShutdown(AgentThread):
    """ This thread will attempt to restart a service
    This means going through each package in ACTIVE manifest
    call the shutdown
    call start
    """
    THREAD_NAME = 'safe_shutdown'
    CAT = 'agent_blocking'

    def __init__(self, threadMgr):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = [SafeShutdown.CAT], name = SafeShutdown.THREAD_NAME)
        
    def beforeRun(self):
        """ set timeout before run """
        # set the timeouts, will kept trying for 24 hour unless cancelled
        timeout = int(pylons.config['safeshutdown_busy_check_timeout'])
        self.setTimeout(timeout)

    def doRun(self):
        """ Main body of the thread """
        errorMsg = ""
        errorCode = None
        failed = False
        try:
            # now check very 30 sec for ongoing activity and activate only when agent is idle
            while True:
                self._checkStop()
                if self._threadMgr.activeSize() <= 1:
                    self._shutdown()
                    LOG.info('Done: agent shutdown')
                    break
                delay = random.randint(10, 30)
                time.sleep(delay)

        except AgentException as exc:
            failed = True
            errorMsg = 'Agent safe shutdown - Agent Exception - %s' % exc.getMsg()
            errorCode = exc.getCode()

        except Exception as exc:
            failed = True
            errorMsg = 'Agent safe shutdown - Unknown error - %s - %s' % (str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR

        finally:
            if failed:
                LOG.error(errorMsg)
                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)

            self._updateStatus(progress = 100)
            
    def _shutdown(self):
        """ shutdown agent """
        stopAgentGlobals()
        pid = os.getpid()
        if (hasattr(signal, 'SIGKILL')):
            os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGTERM)
                    

