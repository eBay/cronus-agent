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

from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.errors import Errors
from agent.lib.package import PackageUtil
import logging
import os
import pylons
import traceback

LOG = logging.getLogger(__name__)

class ValidatePackage(AgentThread):
    """ Cancel distribution """

    def __init__(self, threadMgr, package):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, name = 'validate_package')
        self.__package = package

    def doRun(self):
        """ Main body of the thread """
        try:
            path = pylons.config['repo_root']
            packagePath = os.path.join(path, self.__package)
            propPath = os.path.join(path, (self.__package + '.prop'))
            if os.path.exists(packagePath):
                if (os.path.exists(propPath) and
                    PackageUtil.validateProp(propPath) and
                    PackageUtil.validatePackage(packagePath)):
                    os.utime(packagePath, None)
                    os.utime(propPath, None)
                    self._updateStatus(progress = 100, result = {'msg': 'Package %s is valid' % packagePath})
                    
                else:    
                    msg = 'Package %s failed validation ' % packagePath
                    LOG.warning(msg)
                    self._updateStatus(httpStatus = 500, progress = 100, error = Errors.PACKAGE_CHECKSUM_ERROR, errorMsg = msg)
            else:
                self._updateStatus(httpStatus = 500, progress = 100, error = Errors.PACKAGE_NOT_FOUND, errorMsg = ('Package not found %s' % packagePath))
                
        except Exception as excp:
            errorMsg = 'Exception downloading %s - traceback %s' % (str(excp), traceback.format_exc(2))
            self._updateStatus(httpStatus = 500, progress = 100, error = Errors.UNKNOWN_ERROR, errorMsg = errorMsg)
