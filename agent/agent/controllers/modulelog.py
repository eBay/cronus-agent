#pylint: disable=R0911,W0105
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
'''
Creatted on September 1, 2011

@author: gmangalick
'''
from agent.lib.utils import trackable
try:
    import json
except ImportError:
    import simplejson as json
from pylons import request, response
from pylons import tmpl_context as c
from agent.lib.base import BaseController
from agent.lib.filehelper import tailFile, downloadFile, viewFile
from agent.lib.manifestutil import PkgInitConfig, serviceRootPath, packagePath, packagesInManifest, getServices, manifestPath, getManifests, manifestRootPath
from agent.lib.errors import Errors
from pylons.templating import render_mako as render
import os, time
import logging

LOG = logging.getLogger(__name__)

class ModulelogController(BaseController):
    """ Module Log Controller Class """
    def __init__(self):
        """ constructor  """
        super(ModulelogController, self).__init__()

    @trackable()
    def listServices(self):
        """ listServices """
        packageList = getServices()
        return ModulelogController.prepareOutput(packageList, "/log/list/packages?service=", serviceRootPath(), "List Of Services")

    @trackable()
    def listPackages(self):
        """ listPackages """
        service = request.params.get('service', '')
        package = request.params.get('package', '')
        manifest = request.params.get('manifest', 'active')
        if (service == ''):
            c.errorMsg = 'missing service parameter from request'
            c.errorCode = Errors.LOG_PARAM_REQUIRED
            return render('/derived/error.html')
        if (package != ''):
            return ModulelogController.doAppLogFile('list')
        if (not os.path.isdir(manifestPath(service, manifest))):
            return ModulelogController.doListManifests(service)
        packageList = packagesInManifest(service, manifest)
        return ModulelogController.prepareOutput(packageList, "/log/list/applog?service=" + service + "&manifest=" + manifest + "&package=", manifestPath(service, manifest), "List Of Packages")

    @trackable()
    def listAppLog(self):
        """ listAppLog """
        action = request.params.get('ops', 'list')
        return ModulelogController.doAppLogFile(action)

    @trackable()
    def tailAppLog(self):
        """ tailAppLog """
        return ModulelogController.doAppLogFile('tail')

    @trackable()
    def downloadAppLog(self):
        """ downloadAppLog """
        return ModulelogController.doAppLogFile('download')

    @staticmethod
    def prepareOutput(fileList, urlPath, absolutePath, message):
        """ prepareOutput """
        fullLogList = []
        for fileName in fileList:
            logList = []
            logList.append(urlPath + fileName)
            logList.append(fileName)
            logList.append("/folder.png")
            logList.append(time.ctime(os.path.getmtime(os.path.join(absolutePath, fileName))))
            fileSize = os.path.getsize(os.path.join(absolutePath, fileName))
            logList.append("" + str(fileSize / 1024) + " KB")
            fullLogList.append(logList)
        LOG.info("fullLogLis %s" % fullLogList)
        c.status = fullLogList
        c.message = message
        c.absolutePath = absolutePath
        return render('/derived/appLogDirectory.html')

    @staticmethod
    def doAppLogFile(action):
        """ listAppLog """
        service = request.params.get('service', '')
        package = request.params.get('package', '')
        manifest = request.params.get('manifest', 'active')

        if (service == '' or package == ''):
            c.errorMsg = 'missing service or package parameter from request'
            c.errorCode = Errors.LOG_PARAM_REQUIRED
            return render('/derived/error.html')
        packagePathStr = packagePath(service, manifest, package)
        if (not os.path.isdir(packagePathStr)):
            return ModulelogController.listManifests(service)
        LOG.info('In ModuleLogController doAppLogFile ' + packagePathStr)
        pkgInit = PkgInitConfig(service, manifest, package)
        pkgConfig = pkgInit.getConfigs()
        if not pkgConfig:
            c.errorMsg = 'cronus.ini does not exist, view log needs cronus.ini to know log location, please check your cronus package to make sure cronus.ini exist and have property logAppDir'
            c.errorCode = Errors.CRONUS_INI_EMPTY_NOT_FOUND
            return render('/derived/error.html')
        logAppDirList = pkgConfig['logAppDir']

        dirName = request.params.get('dirName', '')
        fileName = request.params.get('fileName', '')

        if (action == 'list'):
            if (fileName != '' and dirName != ''):
                dirName = os.path.join(dirName, fileName)
            if (dirName != ''):
                return ModulelogController.listAppLogDir(service, manifest, package, dirName, os.path.join(packagePathStr, dirName))
            else:
                return ModulelogController.listAllAppLogDir(service, manifest, package, dirName, packagePathStr, logAppDirList)

        if (dirName == '' or fileName == ''):
            c.errorMsg = 'tail/download App log requires dirName & FileName params missing'
            c.errorCode = Errors.NOT_ENOUGH_PARAMS
            return render('/derived/error.html')

        if (action == 'tail'):
            lines = request.params.get('size', '100')
            return tailFile(os.path.join(packagePathStr, dirName, fileName), lines)
            
        if (action == 'download'):
            return downloadFile(os.path.join(packagePathStr, dirName, fileName))

    @staticmethod
    #===========================================================================
    # listAppLogWithDir
    #===========================================================================
    def listAppLogDir(service, manifest, package, shortDirName, dirName):
        """ listAppLogDir """
        LOG.info('In ModuleLogController dirName ' + dirName)
        print '****content type ', request.environ['CONTENT_TYPE']
        if (not os.path.exists(dirName)):
            c.errorMsg = 'App Log directory (%s) missing' % (dirName)
            c.errorCode = Errors.LOG_APP_DIR_NOT_FOUND
            return render('/derived/error.html')
        if (os.path.isfile(dirName)):
            return viewFile(dirName)
        if (os.path.isdir(dirName)):
            logList = os.listdir(dirName)
            if (request.environ['CONTENT_TYPE'] == 'application/json'):
                return ModulelogController.doJSonStr(logList)
            fullLogList = []
            for fileName in logList:
                fileStr = ''
                fileImg = ''
                logList = []
                if (os.path.isdir(os.path.join(dirName, fileName))):
                    fileStr = "?service=" + service + "&manifest=" + manifest + "&package=" + package + "&dirName=" + os.path.join(shortDirName, fileName)
                    fileImg = "/folder.png"
                else:
                    fileStr = "?service=" + service + "&manifest=" + manifest + "&package=" + package + "&dirName=" + shortDirName + "&fileName=" + fileName
                    fileImg = "/notepad.bmp"
                logList.append(fileStr)
                logList.append(fileName)
                logList.append(fileImg)
                logList.append(time.ctime(os.path.getmtime(os.path.join(dirName, fileName))))
                fileSize = os.path.getsize(os.path.join(dirName, fileName))
                logList.append("" + str(fileSize / 1024) + " KB")
                fullLogList.append(logList)
            print "fullLogLis ", fullLogList
            c.status = fullLogList
            c.message = "List Of Files/Directories" + ""
            c.absolutePath = dirName
            return render('/derived/appLogDirectory.html')

    @staticmethod
    def listAllAppLogDir(service, manifest, package, shortDirName, packagePathStr, appLogDirList):
        """ listAllAppLogDir """
        if (len(appLogDirList) < 1):
            c.errorMsg = 'Could not find logAppDir config values in config file %s' % (appLogDirList)
            c.errorCode = Errors.LOG_APP_DIR_CONFIG_MISSING
            return render('/derived/error.html')
        for fileName in appLogDirList:
            if (not os.path.exists(os.path.join(packagePathStr, fileName))):
                c.errorMsg = 'App Log directory (%s) missing' % (fileName)
                c.errorCode = Errors.LOG_APP_DIR_NOT_FOUND
                return render('/derived/error.html')
        if (request.environ['CONTENT_TYPE'] == 'application/json'):
            return ModulelogController.doJSonStr(appLogDirList)
        fullLogList = []
        for fileName in appLogDirList:
            fileStr = ''
            fileImg = ''
            logList = []
            if (os.path.isdir(os.path.join(packagePathStr, fileName))):
                fileStr = "?service=" + service + "&manifest=" + manifest + "&package=" + package + "&dirName=" + fileName
                fileImg = "/folder.png"
            else:
                fileStr = "?service=" + service + "&manifest=" + manifest + "&package=" + package + "&dirName=" + fileName
                fileImg = "/notepad.bmp"
            logList.append(fileStr)
            logList.append(fileName)
            logList.append(fileImg)
            logList.append(time.ctime(os.path.getmtime(os.path.join(packagePathStr, fileName))))
            fileSize = os.path.getsize(os.path.join(packagePathStr, fileName))
            logList.append("" + str(fileSize / 1024) + " KB")
            fullLogList.append(logList)
        print "fullLogLis ", fullLogList
        c.status = fullLogList
        c.message = "List Of Files/Directories" + ""
        c.absolutePath = packagePathStr
        return render('/derived/appLogDirectory.html')

    @staticmethod
    def doJSonStr(fileList):
        """ doJSonStr """
        response.content_type = 'application/json'
        fileHash = []
        dirHash = []
        appHash = {}
        mainHash = {}
        appHash['FileLogEntries'] = fileHash
        appHash['DirLogEntries'] = dirHash
        mainHash['ApplicationLog'] = appHash
        for fileName in fileList:
            if (os.path.isdir(fileName)):
                fileHash.append(fileName)
            else:
                dirHash.append(fileName)
        return json.dumps(mainHash)

    @trackable()
    def listManifestLog(self):
        """ listManifestLog """
        return ModulelogController.doManifestLogFile('list')

    @trackable()
    def listManifests(self):
        """ listManifests """
        service = request.params.get('service', '')

        if (service == ''):
            c.errorMsg = 'missing service or package parameter from request'
            c.errorCode = Errors.LOG_PARAM_REQUIRED
            return render('/derived/error.html')
        return ModulelogController.doListManifests(service)

    @staticmethod
    def doListManifests(service):
        """ do manifest log file """
        packageList = getManifests(service)
        return ModulelogController.prepareOutput(packageList, "/log/list/packages?service=" + service + "&manifest=", manifestRootPath(service), "List Of Manifests")

    @trackable()
    def tailManifestLog(self):
        """ tail manifest log file """
        return ModulelogController.doManifestLogFile('tail')

    @trackable()
    def downloadManifestLog(self):
        """ download manifest log file """
        return ModulelogController.doManifestLogFile('download')

    @staticmethod
    def doManifestLogFile(action):
        """ do manifest log file """
        service = request.params.get('service', '')
        package = request.params.get('package', '')
        manifest = request.params.get('manifest', 'active')

        if (service == '' or package == ''):
            c.errorMsg = 'missing service or package parameter from request'
            c.errorCode = Errors.LOG_PARAM_REQUIRED
            return render('/derived/error.html')
        print 'service/package/manifest ', service, package, manifest
        packagePathStr = packagePath(service, package, manifest)
        print 'package path ', packagePathStr
        pkgInit = PkgInitConfig(service, package, manifest)
        pkgConfig = pkgInit.getConfigs()
        if not pkgConfig:
            c.errorMsg = 'cronus.ini does not exist, view log needs cronus.ini to know log location, please check your cronus package to make sure cronus.ini exist and have property logAppDir'
            c.errorCode = Errors.CRONUS_INI_EMPTY_NOT_FOUND
            return render('/derived/error.html')
        print '*** packageConfig ', pkgConfig
        manifestFileName = pkgConfig['logManifestFile']
        if (action == 'download'):
            return downloadFile(os.path.join(packagePathStr, manifestFileName))
        if (action == 'tail'):
            lines = request.params.get('size', '100')
            return tailFile(os.path.join(packagePathStr, manifestFileName), lines)
        if (action == 'list'):
            return manifestFileName

    @trackable()
    def tailAgentLog(self):
        """ show log file """
        lines = '100'
        if len(request.params) > 0:
            lines = request.params.get('size', '100')
        return tailFile('logs/agent.log', lines)

    @trackable()
    def downloadAgentLog(self):
        """ show log file """
        print serviceRootPath()
        return downloadFile('logs/agent.log')
