#pylint: disable=W0703, E1101,W0105
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
""" SERVICES CLEANUP Controller """

from agent.lib.agent_thread.services_cleanup import ServicesCleanup
from agent.lib.base import BaseController
from agent.lib.errors import Errors
from agent.lib.result import errorResult, statusResult, doneResult
from agent.lib.security.agentauth import authorize
from agent.lib.utils import trackable
from pylons import request, response, config
import logging
import traceback
from agent.lib.packagemgr import PackageMgr
import os
from agent.lib.package import PackageUtil



LOG = logging.getLogger(__name__)

class CleanupController(BaseController):
    """ Cleanup Controller class. Responsible for cleanup services/kill processes for each services """
    def __init__(self):
        super(CleanupController, self).__init__()

    @authorize()
    @trackable()
    def post(self):
        """ cleanup services """
        try:
            LOG.info('cleanup all application services')
            appGlobal = config['pylons.app_globals']
            cleanupThread = ServicesCleanup(appGlobal.threadMgr)
            self.injectJobCtx(cleanupThread)
            cleanupThread.start()
            cleanupThread.threadMgrEvent.wait()

            return statusResult(request, response, cleanupThread, controller = self)
        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when deleting services %s - %s' %
                               (str(excp), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def cleanupProcess(self):
        """ cleanup services """
        try:
            LOG.info('cleanup all application services')
            appGlobal = config['pylons.app_globals']
            cleanupThread = ServicesCleanup(appGlobal.threadMgr, stopOnly=True)
            self.injectJobCtx(cleanupThread)
            cleanupThread.start()
            cleanupThread.threadMgrEvent.wait()

            return statusResult(request, response, cleanupThread, controller = self)
        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when deleting services %s - %s' %
                               (str(excp), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def deleteCronusPackage(self, package):
        """ secret !!hack!! API to delete one cronus package in the packages folder. """
        try:
            LOG.info('secret delete called for package %s' % package)
            packagesPath = PackageMgr.packagePath()
            thisPkgPath = os.path.join(packagesPath, package + '.cronus')
            thisPropPath = os.path.join(packagesPath, package + '.cronus.prop')
            thisInprogressPath = PackageUtil.inProgressPath(thisPkgPath)

            PackageUtil.cleanUpPackage(thisInprogressPath, thisPkgPath, thisPropPath)
            return doneResult(request, response, controller=self)
        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when deleting package %s,  %s - %s' %
                               (package, str(excp), traceback.format_exc(2)),
                               controller = self)            
