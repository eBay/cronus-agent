#pylint: disable=W0703,R0912,R0915,E0102,E1101,E0202,R0904,R0914,W0105
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

import pylons
import os
import traceback
import logging
            
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib import manifestutil, utils, contextutils
from agent.lib.agent_thread import threadmgr
from agent.lib.agent_thread.manifest_control import ManifestControl
from agent.lib.agent_thread.manifest_create import ManifestCreate
from agent.lib.agent_thread.activate_manifest import ActivateManifest


class DeployService(ManifestControl):
    """ This thread will attempt 
    1. create service if not exist
    2. create manifets if not exist
    3. activate if not already activated
    """

    THREAD_NAME = 'deploy_service'

    def __init__(self, threadMgr, service, manifest, packages, skipProp = True, skipActivation = False):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, manifest)
        self.setName(DeployService.THREAD_NAME)
        self.__packages = packages
        self.__skipProp = skipProp
        self.__skipActivation = skipActivation
        self.__LOG = manifestutil.getServiceLogger(self, logging.getLogger(__name__))

    def doRun(self):
        """ Main body of the thread """
        spath = manifestutil.servicePath(self._service)

        self._updateProgress(1)

        errorMsg = ""
        errorCode = None
        failed = False
        ctxNames = ['guid', 'service']
        
        try:
            # create service if not already exist
            if not os.path.exists(spath):
                os.makedirs(spath)
                os.makedirs(os.path.join(spath, 'manifests'))
                os.makedirs(os.path.join(spath, 'installed-packages'))
                os.makedirs(os.path.join(spath, 'modules'))
                os.makedirs(os.path.join(spath, 'downloaded-packages'))
                os.makedirs(os.path.join(spath, '.appdata'))
                os.makedirs(os.path.join(spath, '.data'))
                import pwd
                uname = pylons.config['app_user_account']
                uid = pwd.getpwnam(uname).pw_uid
                gid = pwd.getpwnam(uname).pw_gid
                utils.rchown(os.path.join(spath, '.appdata'), uid, gid)

            # verify that the path exists
            if (not os.path.isdir(spath)):
                raise AgentException(Errors.UNKNOWN_ERROR, "Service(%s) was not created" % self._service)

            self._updateProgress(20)

            # create manifest if not already exist
            mpath = manifestutil.manifestPath(self._service, self._manifest)
            if (not os.path.exists(mpath) or not os.path.isdir(mpath)):
                self.__LOG.debug('pkgs = %s', self.__packages)

                # parse the package list
                for idx, package in enumerate(self.__packages):
                    if package.startswith('/'):
                        packageRef = package
                        tokens = package.split('/')
                        pkgnamePrefix = tokens[-1].rstrip()
                        fullPkgLoc = manifestutil.getPackageByName(self._service, manifest = None, pkgnamePrefix = pkgnamePrefix)
                        if fullPkgLoc is None:
                            raise AgentException(Errors.MANIFEST_PACKAGE_DOES_NOT_EXIST, 
                                                 'manifest (%s/%s) package (%s) does not exist' % 
                                                 (self._service, self._manifest, self.__packages))
                        else:
                            self.__LOG.info('expanding package reuse ref %s with full package location %s' % (packageRef, fullPkgLoc))
                            self.__packages[idx] = fullPkgLoc

                # start a thread to create the package
                manThread = ManifestCreate(threadmgr.NULL_THREADMGR, self._service, self._manifest, self.__packages, skipProp = self.__skipProp)
                contextutils.copycontexts(self, manThread, ctxNames)
                manThread.run()
                status = manThread.getStatus()
                if (status['error'] != None):
                    raise AgentException(status['error'], status['errorMsg'])
                
            
            self._updateProgress(60)
            if (not os.path.exists(mpath)):
                raise AgentException(Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                'Manifest(%s, %s) path missing' % (self._service, self._manifest))

            if not self.__skipActivation:                    
                activateThread = ActivateManifest(threadmgr.NULL_THREADMGR, self._service, self._manifest)
                contextutils.copycontexts(self, activateThread, ctxNames)
                activateThread.run()
            
                status = activateThread.getStatus()
                if (status['error'] != None):
                    raise AgentException(status['error'], status['errorMsg'])

                # activte manifest if not already activated
                if manifestutil.getActiveManifest(self._service) != self._manifest:
                    raise AgentException(Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                         'Manifest(%s, %s) path missing' % (self._service, self._manifest))

        except SystemExit as exc:
            failed = True
            if (len(exc.args) == 2):
                # ok we got {err code, err msg}
                errorCode = exc.args[0]
                errorMsg = exc.args[1]
        
        except AgentException as exc:
            failed = True
            errorMsg = 'Deploy Service - Agent Exception - %s' % exc.getMsg()
            errorCode = exc.getCode()
        
        except Exception as exc:
            failed = True
            errorMsg = 'Deploy Service - Unknown error - (%s/%s) - %s - %s' \
                        % (self._service, self._manifest, str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR
        
        finally:
            if failed: 
                self.__LOG.warning(errorMsg)
                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)
            else:
                self._updateProgress(100)

