#pylint: disable=W0703,R0912,R0915,E0102,E1101,E0202,R0904,W0105
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
import shutil
import traceback
import time
from time import localtime, strftime
            
from agent.lib.utils import symlink, islink
from agent.lib.utils import readlink
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
#from agent.lib.agent_thread.exec_thread import ExecThread
from agent.controllers.service import ServiceController
import logging
from agent.lib.agent_thread.manifest_control import ManifestControl

#from agent.lib.contextutils import copycontext
from agent.lib import manifestutil


class ActivateManifest(ManifestControl):
    """ This thread will attempt to activate a manifest
    This means going throuh each package
    call the stop
    call the deactivate
    delete the active link
    call the activate
    create the active link
    call start
    """

    THREAD_NAME = 'activate_manifest'

    STAGE_ACTIVATION = 1
    STAGE_STARTUP = 2

    def __init__(self, threadMgr, service, manifest):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, manifest)
        self.setName(ActivateManifest.THREAD_NAME)
        # stage of activation, used for cleanup
        self._activationStage = 0
        self.__LOG = manifestutil.getServiceLogger(self, logging.getLogger(__name__))

    def doRun(self):
        """ Main body of the thread """
        errorMsg = ""
        errorCode = None
        symlinkSwitched = False
        failed = False
        try:
            activePath = os.path.join(ServiceController.manifestPath(self._service), 'active')
            oldManifest = None
            
            appGlobal = pylons.config['pylons.app_globals']

            # make sure that if the active path exists, it's a link
            # if not log that and delete the link
            if (os.path.exists(activePath) and not os.name == 'nt' and not islink(activePath)):
                self.__LOG.error('%s is not a link.  Attempted to delete' % activePath)
                shutil.rmtree(activePath)

            if (os.path.exists(activePath)):
                oldManifest = os.path.basename(readlink(activePath))

            self.__installManifest(self._service, self._manifest)
            self.__deactivateManifest(self._service, oldManifest)
            symlinkSwitched = self.__switchSymlink(self._service, self._manifest)

            appGlobal = pylons.config['pylons.app_globals']

            if self._service == 'agent':
                # START Jeff  09 19 2012: save the timestamp and old manifestPath to .recover: only for agent service.
                recoveryInfo = {}
                beforeKillTimeHuman = strftime("%Y-%m-%d %H:%M:%S", localtime())
                beforeKillTimeStamp = int(time.time())
                recoveryInfo['beforeKillTimeHuman'] = str(beforeKillTimeHuman) 
                recoveryInfo['beforeKillTimeStamp'] = str(beforeKillTimeStamp) 
                # make sure there is always quote: even if null. easy for json parsing in startup
                if self._manifest:
                    recoveryInfo['newManifest'] = self._manifest
                else:
                    recoveryInfo['newManifest'] = 'null'
                if oldManifest:
                    recoveryInfo['oldManifest'] = oldManifest
                else:
                    recoveryInfo['oldManifest'] = 'null'
                manifestutil.writeJson('agent', '.recovery', recoveryInfo)
                # END Jeff  09 19 2012: save the timestamp and .recover files with

                # persist threads result before shutting down
                if (hasattr(appGlobal, 'threadMgr') and appGlobal.threadMgr != None):
                    killStatus = {}
                    killStatus['httpStatus'] = 500
                    killStatus['error'] = Errors.THREAD_KILLED_AGENT_RESTART
                    killStatus['errorMsg'] = 'thread killed, agent restart'
                    appGlobal.threadMgr.snapshot(killStatus, True)

            self.__activateManifest(self._service, self._manifest)

        except SystemExit as exc:
            failed = True
            if (len(exc.args) == 2):
                # ok we got {err code, err msg}
                errorCode = exc.args[0]
                errorMsg = exc.args[1]
            raise exc
        
        except AgentException as exc:
            failed = True
            errorMsg = 'Activate Manifest - Agent Exception - %s' % exc.getMsg()
            errorCode = exc.getCode()
        
        except Exception as exc:
            failed = True
            errorMsg = 'Activate Manifest - Unknown error - (%s/%s) - %s - %s' \
                        % (self._service, self._manifest, str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR
        
        finally:
            if failed: 
                if not self._skipCleanupOnFailure():
                    self.__cleanup(symlinkSwitched, errorMsg, errorCode)

                self.__LOG.warning(errorMsg)
                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)
            else:
                self._updateProgress(100)

    def __cleanup(self, symlinkSwitched, errorMsg, errorCode):
        """ cleanup if activate is not good """
        self.__LOG.info("Start cleanup")
        try:
            if symlinkSwitched:
                self.__LOG.debug("Remove active link")

                self.__LOG.info("Deactivate failed manifest (%s, %s)" % (self._service, self._manifest))
                self.__deactivateFailedManifest(self._service, self._manifest)

                #remove symlink at the end, this is prevent deactivation failed but symlink is removed so that later cleanup is blocked
                activePath = self.__getSymlinkPath(self._service)
                self.__removeSymlink(activePath)

        except Exception as exc:
            self.__LOG.warning(" Exception while recovery:%s" % exc)

    def __installManifest(self, service, manifest):
        """ install a manifest.  This means calling install on the manifest
        @param service - service of manifest to activate
        @param manifest - manifest to activate
        @param stack - stack for recovery
        """
        self.__LOG.debug("Install manifest %s-%s" % (service, manifest))
        if (manifest == None):
            return

        self._execPackages('install', service, manifest, 1, 10, activateFlow = True)

    def __deactivateManifest(self, service, manifest):
        """ deactive a manifest.  This means calling stop then deactive on the manifest
        @param service - service of manifest to deactivate
        @param manifest - manifest to deactivate
        @param stack - stack for recovery
        """
        self.__LOG.debug("Deactivate Manifest %s-%s" % (service, manifest))
        if (manifest == None):
            return

        self._execPackages('shutdown', service, manifest, 11, 25, activateFlow = False)
        self._execPackages('deactivate', service, manifest, 26, 50, activateFlow = False)
        manifestutil.processControllerInPackage(self._service, self._manifest, activateFlow = False)

    def __deactivateFailedManifest(self, service, manifest):
        """ best effort to deactive a failed manifest.  This means calling stop then deactive on the manifest, and ignore any errors
        @param service - service of manifest to deactivate
        @param manifest - manifest to deactivate
        @param stack - stack for recovery
        """
        self.__LOG.debug("Deactivate Manifest %s-%s" % (service, manifest))
        if (manifest == None):
            return
        needShutdown = (self._activationStage == ActivateManifest.STAGE_STARTUP)
        needDeactivate = (needShutdown | (self._activationStage == ActivateManifest.STAGE_ACTIVATION))
        if needShutdown:
            try:
                self._execPackages('shutdown', service, manifest, 81, 90, activateFlow = False)
            except Exception:
                pass
        if needDeactivate:
            try:
                self._execPackages('deactivate', service, manifest, 91, 99, activateFlow = False)
                manifestutil.processControllerInPackage(self._service, self._manifest, activateFlow = False)
            except Exception:
                pass

    def __switchSymlink(self, service, manifest):
        """ remove old symlink and create new one """
        self.__LOG.debug("Switch active link for %s-%s" % (service, manifest))
        if (manifest == None):
            return

        #remove symlink
        activePath = self.__getSymlinkPath(service)
        self.__removeSymlink(activePath)

        # create the active link
        symlink(manifest, activePath)
        return True

    def __activateManifest(self, service, manifest):
        """ deactive a manifest.  This means calling stop then deactive on the manifest
        @param service - service of manifest to activate
        @param manifest - manifest to activate
        @param stack - stack for recovery
        """
        self.__LOG.debug("Activate Manifest %s-%s" % (service, manifest))
        if (manifest == None):
            return

        self._activationStage = ActivateManifest.STAGE_ACTIVATION
        self._execPackages('activate', service, manifest, 51, 65, activateFlow = True)
        self._activationStage = ActivateManifest.STAGE_STARTUP
        self._execPackages('startup', service, manifest, 66, 80, activateFlow = True)
        manifestutil.processControllerInPackage(self._service, self._manifest, activateFlow = True)

    def __removeSymlink(self, activePath):
        """ remove symlink """
        if os.path.exists(activePath):
            if (os.path.islink(activePath)): # *nix
                os.remove(activePath)
            else:
                raise AgentException('Running platform seems to be neither win32 nor *nix with any (sym)link support. Can\'t proceed with link deletion')

    def __getSymlinkPath(self, service):
        """ return symlink path for a service """
        return os.path.join(ServiceController.manifestPath(service), 'active')

