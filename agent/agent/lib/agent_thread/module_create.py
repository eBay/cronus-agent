#pylint: disable=W0703,R0915,R0912,R0904,E0102,E1101,E0202,R0914,W0105
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
""" Thread to perform creation of a service """

import logging
import os
import traceback

from agent.controllers.service import ServiceController
from agent.lib import utils, manifestutil
from agent.lib.agent_thread.download_helper import DownloadHelper
from agent.lib.errors import AgentException, Errors
from agent.lib.package import PackageUtil
from agent.lib.utils import symlink, rmlink, isHigherPrivilegeService
import pylons
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.contextutils import copycontexts


LOG = logging.getLogger(__name__)

class ModuleCreate(DownloadHelper):
    """ This thread will attempt to create new module.
    This means creating the directory.
    Downloading the packages, if necessary.
    Verifying the package.
    Untaring the package.
    verifying the untar'd package.
    and link the package to module
    """

    inProgressExt = '.inprogress'

    def __init__(self, threadMgr, module, package):
        """ Constructor """
        DownloadHelper.__init__(self, threadMgr, cat = ['Module/%s' % module], name = 'create_module')
        self.__service = 'agent'
        self.__module = module
        self.__package = package

    def doRun(self):
        """ Main body of the thread

        Progress Info:
        Look at the list of packages this manifest has and figure out the progress of this manifest
        Progress 1 = manifest directory created
        Progress 2-80 = all packages downloaded
        Progress 81-99 = all packages untarred
        Progress 100 = all links done
        """
        try:
            if self.__service != 'agent':
                utils.checkDiskFull()

            installedPkgPath = manifestutil.installedPkgRootPath(self.__service)

            # figure out which of the packages are already there
            remainingPackages = {}
            pkgDict = PackageUtil.parseUri(self.__package)
            pkgPath = os.path.join(installedPkgPath, pkgDict['packageName'], pkgDict['packageVersion'])
            remainingPackages[self.__package] = pkgDict

            if (not os.path.exists(pkgPath)):
                # now make sure all the packages are downloaded
                try:
                    self._downloadPackages([self.__package])
                except AgentException as exc:
                    # check if it is download error, then modify exception appropriately
                    if exc.getCode() == Errors.DC_FAILED_DOWNLOAD:
                        exc = AgentException(Errors.MANIFEST_PACKAGE_DOWNLOAD_FAILED,
                                            'Manifest (%s/%s) failed downloading package - %s'
                                            % (self.__service, self.__module, exc.getMsg()))
                    raise exc

                LOG.info('Completed download packages for (%s/%s)' % (self.__service, self.__module))

                # now untar the packages
                self._untarPackages(remainingPackages, self.__service, ServiceController.installedPkgPath(self.__service))
                LOG.info('Completed untar all packages for (%s/%s)' % (self.__service, self.__module))

            # now create the links
            for pkgDict in remainingPackages.itervalues():
                pkgPath = os.path.join(installedPkgPath, pkgDict['packageName'], pkgDict['packageVersion'])
                modulePath = os.path.join(manifestutil.moduleRootPath(self.__service), self.__module)
                    
                # validate target folder does exist
                if not os.path.exists(pkgPath):
                    raise AgentException(Errors.PACKAGE_PATH_ERROR, 'invalid untarred package at %s' % pkgPath)
                    
                # remove existing module 
                isExistingModule = os.path.exists(modulePath) 
                if isExistingModule:
                    execThreadTuple = self._getBuiltThread('deactivate')
                    super(ModuleCreate, self)._runExeThread(self, execThreadTuple)
                    rmlink(modulePath)
                    
                execThreadTuple = self._getBuiltThread('activate')
                super(ModuleCreate, self)._runExeThread(execThreadTuple)
                symlink(pkgPath, modulePath)
                
                # load controllers from package
                manifestutil.processModule(self.__service, self.__module, not isExistingModule)
                

            LOG.info('Completed create module for (%s/%s)' % (self.__service, self.__module))
            self._updateStatus(progress = 100)

        except AgentException as exc:
            LOG.info(exc.getMsg())
            self._updateStatus(httpStatus = 500, error = exc.getCode(), errorMsg = exc.getMsg())
            
        except Exception as exc:
            errCode = Errors.UNKNOWN_ERROR
            msg = 'Unknown error for (%s/%s) - %s - %s' % (self.__service, self.__manifest,
                                                           str(exc), traceback.format_exc(2))
            LOG.info(msg)
            self._updateStatus(httpStatus = 500, error = errCode, errorMsg = msg)
    

    def _getBuiltThread(self, scriptName):
        """ build lcm script exec thread """
        # figure out the path to the cronus scripts
        uname = pylons.config['app_user_account']
        execPath = os.path.join(manifestutil.modulePath(self.__service, self.__module), self.__package, 'cronus', 'scripts', scriptName)
        if (isHigherPrivilegeService(self.__service)):
            cmd = execPath
        else:
            cmd = utils.sudoCmd([execPath], uname)

        dummy = not os.path.exists(execPath)
        execThread = ExecThread(self._threadMgr, cmd)
        copycontexts(self, execThread, ['service', 'guid'])
        return execThread, dummy


