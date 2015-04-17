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
import traceback

from agent.lib.utils import islink
from agent.lib.utils import readlink
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
import logging
from agent.lib.agent_thread.manifest_control import ManifestControl
from agent.lib import manifestutil

LOG = logging.getLogger(__name__)

class StartStopService(ManifestControl):
    """ This thread will attempt to restart a service
    This means going through each package in ACTIVE manifest
    call the shutdown
    call start
    """
    ACTION_STARTUP = 'Startup'
    ACTION_SHUTDOWN = 'Shutdown'
    ACTION_RESTART = 'Restart'
    ACTION_REBOOT = 'Reboot'

    THREAD_NAME = 'service_lifecycle'

    def __init__(self, threadMgr, service, action):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, manifest = None)
        self.setName(StartStopService.THREAD_NAME)
        self.__action = action
        self.__LOG = manifestutil.getServiceLogger(self, logging.getLogger(__name__))

    def doRun(self):
        """ Main body of the thread """
        errorMsg = ""
        errorCode = None
        failed = False
        activeManifest = None

        try:
            activePath = manifestutil.manifestPath(self._service, 'active')
            # make sure that the active path exists and it is a link
            # Should we check this again since we already have a check in action controller
            if not os.path.exists(activePath) or not islink(activePath):
                raise AgentException(error = Errors.ACTIVEMANIFEST_MANIFEST_MISSING, errorMsg = 'No active manifest - cannot restart service')

            activeManifest = os.path.basename(readlink(activePath))

            if self.__action == StartStopService.ACTION_SHUTDOWN:
                self.__shutdownManifest(self._service, activeManifest)
            elif self.__action == StartStopService.ACTION_STARTUP:
                self.__startupManifest(self._service, activeManifest)
            elif self.__action == StartStopService.ACTION_RESTART:
                self.__restartManifest(self._service, activeManifest)
            elif self.__action == StartStopService.ACTION_REBOOT:
                self.__rebootManifest(self._service, activeManifest)
            else:
                raise AgentException(error = Errors.INVALID_LIFECYCLE_ACTION, errorMsg = 'Invalid life cycle action - %s' % self.__action)

            self.__LOG.info('Done: %s service for (%s/%s)' % (self.__action, self._service, activeManifest))
            self._updateStatus(progress = 100)

        except AgentException as exc:
            failed = True
            errorMsg = '%s Service - Agent Exception - %s' % (self.__action, exc.getMsg())
            errorCode = exc.getCode()
        except Exception as exc:
            failed = True
            errorMsg = '%s Service - Unknown error - (%s/%s) - %s - %s' \
                        % (self.__action, self._service, self._manifest, str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR
        finally:
            if failed:
                self.__LOG.error(errorMsg)

                if not self._skipCleanupOnFailure() and self.__action != StartStopService.ACTION_SHUTDOWN and self._service and activeManifest:
                    try:
                        self.__LOG.info('%s Service %s failed, shutdown to cleanup' % (self.__action, self._service))
                        self.__shutdownManifest(self._service, activeManifest)
                    except BaseException as excep:
                        self.__LOG.error('Cleanup failed - %s' % str(excep))

                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)

    def __shutdownManifest(self, service, manifest):
        """ shutdown a manifest.  This means calling shutdown script on manifest packages
        @param service - service of manifest to deactivate
        """
        self.__LOG.info("Shutdown active Manifest %s" % (service))
        self._execPackages('shutdown', service, manifest, 50, 90, activateFlow = False)

    def __startupManifest(self, service, manifest):
        """ startup a manifest.  This means calling startup script on manifest packages
        @param service - service of manifest to activate
        """
        self.__LOG.info("Startup active Manifest %s" % (service))
        self._execPackages('startup', service, manifest, 50, 90, activateFlow = False)

    def __restartManifest(self, service, manifest):
        """ restart a manifest.  This means calling startup/lcm script on manifest packages
        @param service - service of manifest to activate
        """
        self.__LOG.info("restart active Manifest %s" % (service))
        self._execPackages('restart', service, manifest, 10, 90, activateFlow = False)

    def __rebootManifest(self, service, manifest):
        """ reboot a manifest.  This means calling startup/lcm script on manifest packages
        @param service - service of manifest to activate
        """
        self.__LOG.info("reboot active Manifest %s" % (service))
        self._execPackages('reboot', service, manifest, 10, 90, activateFlow = False)


