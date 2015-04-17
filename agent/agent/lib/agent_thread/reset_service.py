#pylint: disable=W0703,R0912,R0904,W0105
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
""" Thread to perform reset of a service """

import os
import traceback

from agent.lib.utils import islink
from agent.lib.utils import readlink
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.controllers.service import ServiceController
import logging
from agent.lib.agent_thread.manifest_control import ManifestControl
from agent.lib import manifestutil


class ResetService(ManifestControl):
    """ This thread will attempt to reset a service
    This means going through each package in ACTIVE manifest
    call the shutdown
    call deactivate
    call activate
    call start
    """
    THREAD_NAME = 'service_lifecycle'

    def __init__(self, threadMgr, service):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, manifest = None, name = 'reset_service')
        self.setName(ResetService.THREAD_NAME)
        self.__LOG = manifestutil.getServiceLogger(self, logging.getLogger(__name__))

    def doRun(self):
        """ Main body of the thread """
        errorMsg = ""
        errorCode = None
        failed = False
        activeManifest = None
        try:
            activePath = os.path.join(ServiceController.manifestPath(self._service), 'active')
            # make sure that the active path exists and it is a link
            # Should we check this again since we already have a check in action controller
            if not os.path.exists(activePath) or not islink(activePath):
                raise AgentException(error = Errors.ACTIVEMANIFEST_MANIFEST_MISSING, errorMsg = 'No active manifest - cannot reset service')

            activeManifest = os.path.basename(readlink(activePath))

            self.__shutdownManifest(self._service, activeManifest)
            self.__deactivateManifest(self._service, activeManifest)
            self.__activateManifest(self._service, activeManifest)
            self.__startupManifest(self._service, activeManifest)

            self.__LOG.info('Done: reset service for (%s/%s)' % (self._service, activeManifest))
            self._updateStatus(progress = 100)

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
                self.__LOG.error(errorMsg)

                if self._service and activeManifest:
                    try:
                        self.__LOG.info('Reset service %s failed, shutdown to cleanup' % self._service)
                        self.__shutdownManifest(self._service, activeManifest)
                    except BaseException as excep:
                        self.__LOG.error('Cleanup failed - %s' % str(excep))

                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)

    def __shutdownManifest(self, service, manifest):
        """ shutdown a manifest.  This means calling shutdown script on manifest packages
        @param service - service of manifest to deactivate
        """
        self.__LOG.info("Shutdown active Manifest %s" % (service))
        self._execPackages('shutdown', service, manifest, 11, 25, activateFlow = False)

    def __deactivateManifest(self, service, manifest):
        """ deactivate a manifest.  This means calling deactivate script on manifest packages
        @param service - service of manifest to deactivate
        """
        self.__LOG.info("Deactivate active Manifest %s" % (service))
        self._execPackages('deactivate', service, manifest, 26, 50, activateFlow = False)

    def __activateManifest(self, service, manifest):
        """ activate a manifest.  This means calling activate script on manifest packages
        @param service - service of manifest to activate
        """
        self.__LOG.info("Activate active Manifest %s" % (service))
        self._execPackages('activate', service, manifest, 51, 75, activateFlow = False)

    def __startupManifest(self, service, manifest):
        """ startup a manifest.  This means calling startup script on manifest packages
        @param service - service of manifest to activate
        """
        self.__LOG.info("Startup active Manifest %s" % (service))
        self._execPackages('startup', service, manifest, 75, 90, activateFlow = False)
