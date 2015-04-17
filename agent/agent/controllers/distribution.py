#pylint: disable=W0703,E1102,W0511,W0105
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
""" DistributionClient """

from agent.lib import utils, configutil
from agent.lib.agent_thread.download_thread import DownloadThread
from agent.lib.agent_thread.validate_package import ValidatePackage
from agent.lib.base import BaseController
from agent.lib.errors import Errors, AgentException
from agent.lib.package import PackageUtil
from agent.lib.packagemgr import PackageMgr
from agent.lib.result import doneResult, errorResult, statusResult
from agent.lib.security.agentauth import authorize
from agent.lib.utils import trackable
from paste.deploy.converters import asbool
from pylons import request, response, config
import json
import logging
import os
import pylons
import shutil
import traceback

LOG = logging.getLogger(__name__)

class DistributionController(BaseController):
    """ Distribution Client class. """

    @authorize()
    @trackable()
    def startdownload(self):
        """
        Download using http. The protocol is chosen based on package uri.
        Target folder is packageloc relative to repo_root.
        """
        try:
            utils.checkDiskFull()
            reqjson = json.loads(request.body)
            package = str(reqjson['package'])
            packageloc = str(reqjson['packageloc'])
            skipProp = asbool(reqjson['skipProp']) if 'skipProp' in reqjson else configutil.getConfigAsBool('download_skip_prop')
            
            LOG.info('Request received for StartDownload %s' % packageloc)
            appGlobal = config['pylons.app_globals']
            downloadThread = None

            cat = 'DIST_SD' + packageloc

            if not downloadThread:
                LOG.info('Starting a new StartDownload Thread %s' % packageloc)
                downloadThread = DownloadThread(appGlobal.threadMgr, package, packageloc, category = [cat], skipProp = skipProp)
                downloadThread.setMergeOnFound(True)
                self.injectJobCtx(downloadThread)
                downloadThread.start()
                downloadThread.threadMgrEvent.wait()

            return statusResult(request, response, downloadThread, controller = self)
        except AgentException as excep:
            return errorResult(request, response, error = excep.getCode(), errorMsg = excep.getMsg(), controller = self)
        except Exception as excp:
            errorMsg = 'Exception downloading %s - traceback %s' % (str(excp), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR, errorMsg = errorMsg, controller = self)


    @authorize()
    @trackable()
    def validatePackage(self):
        """
        Validate a given package, read prop file, do md5 checksum.
        Target folder is packageloc relative to repo_root.
        """
        try:
            body = json.loads(request.body)
            package = str(body['package'])
            async = False
            if 'async' in body:
                async = asbool(body['async'])
                
            LOG.info('Request received for Validate Package %s' % package)
            appGlobal = config['pylons.app_globals']
            vThread = ValidatePackage(appGlobal.threadMgr, package)
            if not async:
                vThread.join()
            return statusResult(request, response, vThread, controller = self)
            
        except Exception as excp:
            errorMsg = 'Error validating package %s' + excp.getMsg
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR, errorMsg = errorMsg, controller = self)

    @trackable()
    def listPackages(self):
        """ list content of packages folder
        """
        result = {}
        pkgs = [ os.path.basename(packageDir) for packageDir in os.listdir(PackageMgr.packagePath()) ]
        result['packages'] = pkgs
        return doneResult(request, response, result = result, controller = self)
    
    @authorize()
    @trackable()
    def uploadPackage(self):
        """ take an upload file """
        try:
            utils.checkDiskFull()

            agt_root = pylons.config['agent_root']
            pkg_root = pylons.config['repo_root']

            md5 = str(request.POST['md5']) if 'md5' in request.POST else None
            dest = str(request.POST['dest']) if 'dest' in request.POST else None

            myfile = request.POST['file']
            filename = myfile.filename.lstrip(os.sep)
            permanent_file = open(os.path.join(pkg_root, filename), 'w')

            shutil.copyfileobj(myfile.file, permanent_file)
            myfile.file.close()
            permanent_file.close()
            
            if md5:
                md5Sum = utils.md5sum(permanent_file)
                if (md5Sum != md5):
                    msg = 'package md5 = %s : %s' % (md5Sum, md5)
                    LOG.warning(msg)
                    raise AgentException(Errors.DC_FAILED_VALIDATE, msg)
            
            if filename and dest:
                utils.copyFile(pkg_root, os.path.join(agt_root, 'service_nodes', dest), filename) 

            return doneResult(request, response, controller=self)
        
        except AgentException as excp:
            return errorResult(request, response, excp.getCode(), excp.getMsg(), controller = self)
        
        except Exception as excp:
            errorMsg = 'Exception downloading %s - traceback %s' % (str(excp), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR, errorMsg = errorMsg, controller = self)
       
    @authorize()
    @trackable()
    def deletePackage(self, package):
        """ secret !!hack!! API to delete one cronus package in the packages folder. """
        try:
            LOG.info('secret delete called for package %s' % package)
            packagesPath = PackageMgr.packagePath()
            thisPkgPath = os.path.join(packagesPath, package + '.cronus')
            thisPropPath = os.path.join(packagesPath, package + '.cronus.prop')
            thisInprogressPath = PackageUtil.inProgressPath(thisPkgPath)

            PackageUtil.cleanUpPackage(thisInprogressPath, thisPkgPath, thisPropPath)
            return doneResult(request, response, controller=self)
        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when deleting package %s,  %s - %s' %
                               (package, str(excp), traceback.format_exc(2)),
                               controller = self)