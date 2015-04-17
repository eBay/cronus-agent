#pylint: disable=W0703,W0106,W0612,R0904,R0914,W0105
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
""" Service Controller """

from agent.lib import manifestutil
from agent.lib.base import BaseController
from agent.lib.errors import Errors, AgentException
from agent.lib.result import doneResult, errorResult, statusResult
from agent.lib.security.agentauth import authorize
from agent.lib.utils import readlink, trackable
from pylons import request, response, config
import json
import logging
import os
import traceback
from agent.lib.agent_thread.module_create import ModuleCreate
from agent.lib.agent_thread.module_delete import ModuleDelete


LOG = logging.getLogger(__name__)

class ModuleController(BaseController):
    """ Module Controller Class.  This class handles all module rest calls. """

    @trackable()
    def listModules(self):
        """ list all the modules in the agent """
        try:
            LOG.info('Got a list service request')
            modules = manifestutil.getModules()
            return  doneResult(request, response, result = modules, controller = self)
        
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when listing modules %s - %s' %
                               (str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def post(self, module):
        """ Create a new module object """
        try:

            LOG.info('Got a post request for module ' + module)

            if (request.body == ""):
                return errorResult(request, response, Errors.MODULE_PACKAGE_PARSING_ERROR,
                                   'No body found in post command',
                                   controller = self)

            body = json.loads(request.body)

            package = body['package']

            LOG.debug('pkgs = %s', package)

            appGlobal = config['pylons.app_globals']
            # start a thread to create the package
            moduleThread = ModuleCreate(appGlobal.threadMgr, module, package)
            self.injectJobCtx(moduleThread)
            moduleThread.start()
            moduleThread.threadMgrEvent.wait()

            return statusResult(request, response, moduleThread, controller = self)

        except AgentException as excep:
            return errorResult(request, response, error = excep.getCode(), errorMsg = excep.getMsg(), controller = self)
        
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for create module(%s/%s) - %s - %s' %
                               ('agent', module, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def delete(self, module):
        """ Delete a new service object """
        try:
            LOG.info('Got a delete request for module ' + module)

            path = manifestutil.modulePath('agent', module)

            if (not os.path.exists(path) and not os.path.isdir(path)):
                return doneResult(request, response, controller = self)

            # start the delete thread
            appGlobal = config['pylons.app_globals']
            deleteThread = ModuleDelete(appGlobal.threadMgr, module)
            self.injectJobCtx(deleteThread)
            deleteThread.start()
            deleteThread.threadMgrEvent.wait()

            return statusResult(request, response, deleteThread, controller = self)
        
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when deleting module(%s) %s - %s' %
                               (module, str(excep), traceback.format_exc(2)),
                               controller = self)

    @trackable()
    def get(self, module):
        """ Get a new service object """
        try:
            # make sure the service path exists
            path = manifestutil.modulePath('agent', module)
            if (not os.path.exists(path)):
                return errorResult(request, response, error = Errors.SERVICE_NOT_FOUND,
                                   errorMsg = 'Unable to find module (%s)' % module,
                                   controller = self)

            result = {}
            modulePackage = readlink(path)
            result['package'] = modulePackage

            return  doneResult(request, response, result = result, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when getting module (%s) %s - %s' %
                               (module, str(excep), traceback.format_exc(2)),
                               controller = self)

    #####################################################
    # utility members
    #####################################################

    @staticmethod
    def loadModuleOnAgentStartup():
        """
        when agent is restarted,
        load agent modules
        """
        if os.path.exists(manifestutil.moduleRootPath('agent')):
            for module in manifestutil.getModules():
                try:
                    manifestutil.processModule('agent', module, True)
                except Exception as excep:
                    LOG.error('Unknown error loading module (%s) - %s - %s' % (module, str(excep), traceback.format_exc(2)))
