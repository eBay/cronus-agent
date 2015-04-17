#pylint: disable=W0703,W0105
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
""" status controller """

from agent.lib.base import BaseController
from agent.lib.result import doneResult
from agent.lib.result import errorResult
from agent.lib.result import statusResult
from agent.lib.errors import Errors, AgentException
from agent.lib.utils import trackable
from agent.lib.security.agentauth import authorize

from pylons import request, response, config
import json
import traceback
import logging
from agent.lib.agent_thread.cancel_agentthread import AgentThreadCancel

LOG = logging.getLogger(__name__)

class StatusController(BaseController):
    """ Status Controller.
    Used to return the status of a long running action

    Url looks like http://<host>/status/{uuid}
    The response is there an error or a progress
    """

    @trackable()
    def get(self, uuid):
        """ Get the status of this particular thread.
        Use the uuid to grab the correct thread.
        return the progress and status of the thread. """

        try:
            appGlobal = config['pylons.app_globals']

            thread = appGlobal.threadMgr.getThreadByUuid(uuid)
            if (thread == None):
                return errorResult(request, response, Errors.STATUS_UUID_NOT_FOUND,
                                   'Unable to find thread with uuid(%s)' % uuid,
                                   controller = self)
            
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for get status(%s) - %s, %s' %
                               (uuid, str(excep), traceback.format_exc()),
                               controller = self)
            
        return statusResult(request, response, thread, controller = self, maxProgress = 99 if thread.isAlive() else 100)
    
    @authorize()
    @trackable()
    def delete(self, uuid):
        """ cancel an active thread """
        LOG.info('Cancel thread with uuid ' + uuid)
        try:
            body = json.loads(request.body)
            async = False
            if body.get('async'):
                async = True
            LOG.info('Canceling. async %s' % async)

            comment = body.get('comment')
            LOG.debug('Canceling.  comment: %s' % comment)

            appGlobal = config['pylons.app_globals']
            cancelThread = AgentThreadCancel(appGlobal.threadMgr, uuid)
            self.injectJobCtx(cancelThread)
            cancelThread.start()
            cancelThread.threadMgrEvent.wait()
            if not async:
                cancelThread.join()

            return statusResult(request, response, cancelThread, controller = self)
        except AgentException as exc:
            msg = 'Could not cancel distribution thread with uuid ' + uuid + exc.getMsg
            return errorResult(request, response, error = exc.getCode(), errorMsg = msg, controller = self)
        except Exception:
            code = Errors.UNKNOWN_ERROR
            msg = 'Could not cancel distribution thread with uuid ' + uuid + '(#' + str(code) + '). ' + traceback.format_exc(5)
            return errorResult(request, response, error = code, errorMsg = msg, controller = self)
        

    @trackable()
    def done(self):
        """ just return a good result """
        return doneResult(request, response, controller = self)


