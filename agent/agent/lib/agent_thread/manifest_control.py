#pylint: disable=W0703,E0102,E1101,R0912,R0904,W0223,W0105
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
import time
import copy

from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.controllers.manifest import ManifestController
from agent.lib.utils import isHigherPrivilegeService, calcProgress
import logging
from agent.lib.contextutils import injectcontext, copycontexts
from agent.lib import manifestutil, utils, contextutils, configutil
from agent.lib.manifestutil import PkgInitConfig

LOG = logging.getLogger(__name__)

class ManifestControl(AgentThread):
    """ This thread will attempt to activate a manifest
    This means going throuh each package
    call the stop
    call the deactivate
    delete the active link
    call the activate
    create the active link
    call start
    """

    REC_MAP = {"install": "uninstall", "activate": "deactivate", "startup": "shutdown"}

    def __init__(self, threadMgr, service, manifest, name = 'agent_thread'):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = [manifestutil.serviceCat(service)], name = name)
        self.__manifest = manifest
        self.__service = service
        injectcontext(self, {'service':service})
        # maintain a stack that has all the recovery script paths
        # this stack is protected
        self._stack = []

    @property
    def _manifest(self):
        """ manifest property """
        return self.__manifest

    @_manifest.setter
    def _manifest(self, value):
        """ manifest property """
        self.__manifest = value

    @property
    def _service(self):
        """ service property """
        return self.__service

    @_service.setter
    def _service(self, value):
        """ service property """
        self.__service = value

    def _skipCleanupOnFailure(self):
        """ skip cleanup on app lifecycle failure
        """
        return configutil.getConfigAsBool('skip_cleanup_on_failure')

    def _obtainCmdExecThreads(self, exeName, service, manifest, activateFlow):
        """start the threads to execute cmd in each package in the service/manifest"""

        execThreads = []
        packages = ManifestController.getPackages(service, os.path.basename(manifest))
        # Executing the deactivate in reversed order where the last package is first deactivated.
        if (not activateFlow):
            packages.reverse()

        # make sure there's something to do, otherwise just return here
        if (len(packages) == 0):
            return execThreads
        
        for package in packages:

            pkgPath = manifestutil.packagePath(service, manifest, package)
            pkgInit = PkgInitConfig(pkgPath)
            pkgConfig = pkgInit.getConfigs()
                
                
            # check command type and package startup process
            if (exeName == 'reboot' or exeName == 'restart'):
                
                # default action for reboot is to startup, noop for restart agent
                action = 'startup' if 'reboot' == exeName else 'noop'
                
                if exeName == 'reboot' and pkgConfig and pkgConfig.has_key('lcm_on_system_reboot'):
                    action = pkgConfig['lcm_on_system_reboot']
                            
                if (exeName == 'restart' and pkgConfig and pkgConfig.has_key('lcm_on_agent_restart')):
                    action = pkgConfig['lcm_on_agent_restart']
                        
                if action == 'reset':
                    execThread, dummy = self._getBuiltThread(service, manifest, package, "shutdown")
                    execThreads.append([execThread, dummy])
                    execThread, dummy = self._getBuiltThread(service, manifest, package, "deactivate")
                    execThreads.append([execThread, dummy])
                    execThread, dummy = self._getBuiltThread(service, manifest, package, "activate")
                    execThreads.append([execThread, dummy])
                    
                if (action == 'reset' or action == 'startup'):
                    execThread, dummy = self._getBuiltThread(service, manifest, package, 'startup')
                    execThreads.append([execThread, dummy])
            
            else:
                execThread, dummy = self._getBuiltThread(service, manifest, package, exeName)
                execThreads.append([execThread, dummy])
                
        return execThreads
    

    def _getBuiltThread(self, service, manifest, package, exeName):
        """ here """
        # figure out the path to the cronus scripts
        uname = pylons.config['app_user_account']
        execPath = os.path.join(ManifestController.manifestPath(service, manifest), package, 'cronus', 'scripts', exeName)
        if (isHigherPrivilegeService(service)):
            cmd = execPath
        else:
            cmd = utils.sudoCmd([execPath], uname)

        dummy = not os.path.exists(execPath)
        execThread = ExecThread(self._threadMgr, cmd)
        copycontexts(self, execThread, contextutils.CTX_NAMES)
        return execThread, dummy

    def _execPackages(self, exeName, service, manifest, minProgress, maxProgress, activateFlow = True):
        """ execPackages.  Execute the executible for all packages under the service/manifest.
        calculate and update progress.  This will not return until all executibles have finished with status 0.
        If one executible fails, this function will thow an exception.

        @param exeName - name of the executible
        @param service - service of manifest
        @param manifest - manifest
        @param minProgress - minimum progress for executing these packages
        @param maxProgress - maximum progress for executing these packages
        @param stack - recovery stack
        @param activateFlow (default true) - whether part of activation flow (False means it is de-active).  This affects the order of execution
        @param runSequential (default true) - whether to run the activation in sequential manner (False means to run them in parallel).
        @throws AgentException - will throw an exception if an error occurred
        """
        execThreads = self._obtainCmdExecThreads(exeName, service, manifest, activateFlow)
        self._runExecThreads(execThreads, minProgress, maxProgress)

    def _runExecThreads(self, execThreads, minProgress, maxProgress):
        """ run exec threads """
        if (len(execThreads) == 0):
            self._updateProgress(maxProgress)
            return

        # start with min progress
        self._updateProgress(minProgress)

        # now wait for the threads to complete and update progress
        firstTime = True
        while (True):
            self._checkStop()

            progress = 0
            running = False

            for (execThread, dummy) in execThreads:
                #first time, push recovery stack
                if firstTime:
                    self._pushRecStack(execThread.getCmd())
                
                if dummy:
                    continue
                
                self.extendTimeout(execThread.getTimeout())
                status = AgentThread._runExeThread(self, (execThread, dummy))

                progress += status['progress']

            firstTime = False

            if (not running):
                break

            # update the progress
            percent = progress / len(execThreads)

            self._updateProgress(calcProgress(minProgress, maxProgress, float(percent) / 100))

            time.sleep(float(pylons.config['exec_thread_sleep_time']))

        self._updateProgress(maxProgress)

    def _pushRecStack(self, cmd):
        """ push recovery command of cmd into stack """
        newCmd = copy.deepcopy(cmd)
        if type(newCmd) is list:
            recPath = self._getRecPath(newCmd[-1])
            if recPath:
                newCmd[-1] = recPath
                self._stack.append(newCmd)
        else:
            recPath = self._getRecPath(newCmd)
            if recPath:
                self._stack.append(recPath)

    def _getRecPath(self, execPath):
        """ get the path for recovery script """
        head, fileName = os.path.split(execPath)
        scriptName, ext = os.path.splitext(fileName)
        if not scriptName in ManifestControl.REC_MAP:
            return None

        recPath = os.path.join(head, ManifestControl.REC_MAP[scriptName] + ext)
        if os.path.exists(recPath):
            return recPath

        return None

    def _popRecStack(self):
        """ pop command out of stack, make sure check whether empty stack before calling """
        return self._stack.pop()

    def _getStack(self):
        """ return stack """
        return self._stack





