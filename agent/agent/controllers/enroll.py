#pylint: disable=W0703,E1101,W0105
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
""" ENROLLMENT Controller """

from agent.lib.base import BaseController
from agent.lib.errors import Errors
from agent.lib.result import errorResult, doneResult
from agent.lib.utils import trackable
from agent.lib import manifestutil
from agent.lib.security.agentauth import authorize

from threading import Lock
from pylons import request, response, config
import json
import traceback
import logging

LOG = logging.getLogger(__name__)

class EnrollController(BaseController):
    """ Enroll Controller class.  Responsible for telling agent where is state-hub """
    def __init__(self):
        super(EnrollController, self).__init__()
        self.lock = Lock()

    @authorize()
    @trackable()
    def post(self):
        """ enroll agent """
        try:
            body = json.loads(request.body)
            if 'hardwarePath' not in body:
                LOG.error('failed when enrolling: hardwarePath is not provided')
                return errorResult(request, response, error = Errors.UNKNOWN_ERROR, errorMsg='hardwarePath is not specified', controller = self)

            with self.lock:
                LOG.info('enroll agent with hardwarePath %s' % (body['hardwarePath']))
                
                hardwarePath = body['hardwarePath']
                manifestutil.updateServiceMetaFile('agent', {'hwPath': hardwarePath,})

                appGlobal = config['pylons.app_globals']
                appGlobal.hwPath = hardwarePath
                appGlobal.enrolled = True
                
                appGlobal.agentMonitor.reloadMonitors()

                return doneResult(request, response, controller = self)

            return errorResult(request, response,
                               error = Errors.THREAD_ALREADY_ADDED,
                               errorMsg = "Cann't acquire lock for enrollment",
                               controller = self )

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for enroll - %s - %s' %
                               (str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def delete(self):
        """ un-enroll agent """
        LOG.info('unenroll agent')
        try:
            with self.lock:
                appGlobal = config['pylons.app_globals']
                if hasattr(appGlobal, 'hwPath'):
                    setattr(appGlobal, 'hwPath', None)
                manifestutil.updateServiceMetaFile('agent', {'hwPath':None})
                appGlobal.enrolled = False
                appGlobal.agentMonitor.reloadMonitors()
                    
                return doneResult(request, response, controller = self)

            return errorResult(request, response,
                   error = Errors.THREAD_ALREADY_ADDED,
                   errorMsg = "Cann't acquire lock for un-enrollment",
                   controller = self )

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for un-enroll - %s - %s' %
                               (str(excep), traceback.format_exc(2)),
                               controller = self)
