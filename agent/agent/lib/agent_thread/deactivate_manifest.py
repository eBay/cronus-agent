#pylint: disable=W0703,R0912,R0915,R0904,W0105
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

import os
import shutil
import traceback

from agent.lib.utils import islink
from agent.lib.utils import readlink
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.controllers.service import ServiceController
import logging
from agent.lib.agent_thread.manifest_control import ManifestControl

from agent.lib import manifestutil


class DeactivateManifest(ManifestControl):
    """ This thread will attempt to activate a manifest
    This means going throuh each package
    call the stop
    call the deactivate
    delete the active link
    call the activate
    create the active link
    call start
    """

    THREAD_NAME = 'deactivate_manifest'

    def __init__(self, threadMgr, service):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, manifest = None, name = 'deactivate_manifest')
        self.setName(DeactivateManifest.THREAD_NAME)
        self.__LOG = manifestutil.getServiceLogger(self, logging.getLogger(__name__))

    def doRun(self):
        """ Main body of the thread """
        errorMsg = ""
        errorCode = None
        failed = False
        try:

            activePath = os.path.join(ServiceController.manifestPath(self._service), 'active')
            oldManifest = None

            # make sure that if the active path exists, it's a link
            # if not log that and delete the link
            if (os.path.exists(activePath) and not os.name == 'nt' and not islink(activePath)):
                self.__LOG.error('%s is not a link.  Attempted to delete' % activePath)
                shutil.rmtree(activePath)

            if (os.path.exists(activePath)):
                oldManifest = os.path.basename(readlink(activePath))
            else:
                raise AgentException(error = Errors.ACTIVEMANIFEST_MANIFEST_MISSING, errorMsg = 'No active manifest - cannot deactivate service')

            self.__deactivateManifest(self._service, oldManifest)
            self.__removeSymlink(self._service)

        except SystemExit as exc:
            failed = True
            if (len(exc.args) == 2):
                # ok we got {err code, err msg}
                errorCode = exc.args[0]
                errorMsg = exc.args[1]
            raise exc
        except AgentException as exc:
            failed = True
            errorMsg = 'Deactivate Manifest - Agent Exception - %s' % exc.getMsg()
            errorCode = exc.getCode()
        except Exception as exc:
            failed = True
            errorMsg = 'Deactivate Manifest - Unknown error - (%s) - %s - %s' \
                        % (self._service, str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR
        finally:
            if failed:
                self.__LOG.warning(errorMsg)
                self._updateStatus(httpStatus = 500, error = errorCode,
                                   errorMsg = errorMsg)
            self.__LOG.debug('Done: activate manifest for (%s)' % (self._service))
            self._updateProgress(100)

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
        manifestutil.processControllerInPackage(service, manifest, activateFlow = False)

    def __removeSymlink(self, service):
        """ remove symlink """
        #remove symlink
        activePath = self.__getSymlinkPath(service)
        if os.path.exists(activePath):
            if (os.path.islink(activePath)): # *nix
                os.remove(activePath)
            else:
                raise AgentException('Running platform seems to be neither win32 nor *nix with any (sym)link support. Can\'t proceed with link deletion')

    def __getSymlinkPath(self, service):
        """ return symlink path for a service """
        return os.path.join(ServiceController.manifestPath(service), 'active')


