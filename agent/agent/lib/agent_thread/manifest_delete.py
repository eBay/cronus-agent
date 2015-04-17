#pylint: disable=W0703,R0904,W0105
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
""" Thread to perform service deletes """

import shutil
from agent.lib.errors import Errors
from agent.lib.agent_thread.agent_thread import AgentThread
import logging
from agent.lib import manifestutil

LOG = logging.getLogger(__name__)

class ManifestDelete(AgentThread):
    """ All threads used by the agent should be of type agent thread.
    This thread will be used to generate ids, provide categories for the thread mgr. """

    def __init__(self, threadMgr, service, manifest):
        """ Constructor """
        from agent.controllers.service import ServiceController

        AgentThread.__init__(self, threadMgr, cat = [ServiceController.serviceCat(service)], name = 'delete_manifest')
        self.service = service
        self.manifest = manifest

    def doRun(self):
        """ Main body of the thread """
        try:
            # now try to delete the manifest directory
            shutil.rmtree(manifestutil.manifestPath(self.service, self.manifest))
            self._updateStatus(progress = 100)
        except OSError as excp:
            msg = 'Manifest(%s, %s) path error: %s' % (self.service, self.manifest, str(excp))
            self._updateStatus(httpStatus = 500, error = Errors.MANIFEST_PATH_ERROR, errorMsg = msg)
        except Exception as exc:
            msg = 'Unknown error when deleting service %s - %s' % (self.service, str(exc))
            errCode = Errors.UNKNOWN_ERROR
            self._updateStatus(httpStatus = 500, error = errCode, errorMsg = msg)

