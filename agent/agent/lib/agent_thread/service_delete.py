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
import os
import errno
import stat
import logging
import pylons
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib import utils, manifestutil

LOG = logging.getLogger(__name__)

class ServiceDelete(AgentThread):
    """ All threads used by the agent should be of type agent thread.
    This thread will be used to generate ids, provide categories for the thread mgr. """

    def __init__(self, threadMgr, service, path):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = [manifestutil.serviceCat(service)], name = 'delete_service')
        self.__path = path
        self.service = service

    def doRun(self):
        """ Main body of the thread """
        try:
            deleted = True

            try:
                ServiceDelete.deleteFolderContents(self.__path)

            except AgentException as excep:
                LOG.warning('Delete Service Exception - %s', excep.getMsg())
                self._updateStatus(httpStatus = 500, error = excep.getCode(),
                                   errorMsg = excep.getMsg())
            except OSError as excep:
                LOG.warning('Delete Service Exception - %s', excep.getMsg())
                self._updateStatus(httpStatus = 500, error = Errors.SERVICE_DELETE_FAILED,
                                   errorMsg = 'Path (%s) failed to be deleted' % self.__path)
                deleted = False

            self._checkStop()

            # kill & deactivate the service process
            threads = self._threadMgr.getThreadByCat(manifestutil.serviceCat(self.service), onlylive = True, fastbreak = False)
            for thread in threads:
                thread.stop()

            # TPY
            # go to the active manifest
            # stop the manifest
            # deactivate manifest

            # verify that the path does not exist
            if (os.path.exists(self.__path) and deleted):
                self._updateStatus(httpStatus = 500, error = 1,
                                    errorMsg = 'Path (%s) still exists even after delete attempt' % self.__path)

            self._updateStatus(progress = 100)
        except Exception as exc:
            msg = 'Unknown error when deleting service %s - %s' % (self.service, str(exc))
            errCode = Errors.UNKNOWN_ERROR
            self._updateStatus(httpStatus = 500, error = errCode, errorMsg = msg)

    @staticmethod
    def deleteFolderContents(path, onlyChildren = False):
        """ delete service """
        if not os.path.exists(path):
            return

        checkValidatePath(path)
        checkOwner(path)
        removeDirectory(path, onlyChildren)

def handleRemoveReadonly(func, path, exc):
    """ handle read only file delete """
    excvalue = exc[1]
    if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) # 0777
        func(path)
    else:
        raise

def checkValidatePath(path):
    """ check that the directory we are trying to delete is valid (at least try to) """
    if (path == None or path == '' or path == '/'):
        raise AgentException(Errors.SERVICE_DELETE_NOT_VALID,
                             'Invalid path(%s) to delete' % path)

def checkOwner(path):
    """ check that file owner is either agent account (check config but most likely cronus) or the app account """
    if (not os.name == 'nt'):
        import pwd
        agentUname = pylons.config['agent_user_account']
        agentUid = pwd.getpwnam(agentUname).pw_uid
        appUname = pylons.config['app_user_account']
        appUid = pwd.getpwnam(appUname).pw_uid
        file_stat = os.stat(path)

        if (not file_stat.st_uid in [agentUid, appUid]):
            raise AgentException(Errors.SERVICE_DELETE_NOT_VALID,
                                 'Path(%s) not owned by agent %s or application %s' % (path, agentUname, appUname))

def removeDirectory(path, onlyChildren):
    """ remove directory """
    if onlyChildren:
        path = os.path.join(path, '*')
        
    if (not os.name == 'nt'):

        cmd = utils.sudoCmd('rm -rf %s' % path)
        LOG.debug("running command %s" % cmd)

        ret = os.system(cmd)
        if (ret != 0):
            raise AgentException(error = Errors.SERVICE_DELETE_FAILED, errorMsg = 'Path (%s) delete failed' % path)
    else:
        try:
            shutil.rmtree(path, False, handleRemoveReadonly)
        except OSError:
            cmd = 'rm -rf %s' % path
            LOG.debug("running command %s" % cmd)
            os.system(cmd)
