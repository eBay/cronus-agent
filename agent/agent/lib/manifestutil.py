#pylint: disable=W0703,W0702,C0103,E1101,W0703,W0212,W0232,R0914,R0915,W0141,R0912,W0105
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
"""
helpers functions for manifest, to get paths for different level in a __service 
such as services, manifests, packages
also load package cronus.ini file
"""

from agent.lib import dynautils, utils
from agent.lib.contextutils import getcontext
from agent.lib.errors import AgentException, Errors
from agent.lib.utils import synchronized, readlink, islink
from pylons import config
from threading import Lock
import ConfigParser
import json
import logging
import os
import sys
import time
import traceback

INI_FILENAME = 'cronus.ini'
ACTIVE_MANIFEST = 'active'
CRONUS_DIR = 'cronus'

LOGHDLRS = {}
LOGFMT = '%(asctime)s.%(msecs)03d %(levelname)-5.5s [%(name)s] [%(threadName)s] [%(__service)s] %(message)s'
DATEFMT = '%y/%m/%d %H:%M:%S'
LOCK = Lock()

LOG = logging.getLogger(__name__)

class ServiceFilter(logging.Filter):
    ''' filter log message by __service name, only if message has [servicename], 
        in addition to agent logs, it will also be logged to __service log
    ''' 
    def __init__(self, servicename, name=''):
        ''' @param servicename: matching __service name
            @param name: name of the filter 
        '''
        logging.Filter.__init__(self, name=name)
        self.__service = servicename
        
    def filter(self, record):
        ''' filter, accept message if it matches the regular expression'''
        return (record.__dict__.has_key('__service') and record.__dict__['__service'] ==  self.__service)


def getServiceLogger(source, logger, servicename=None):
    ''' add a log handler for a specific __service to an existing logger, handler is cached
        @param __service: __service name
        @param logger: an existing logger to add handler to 
    '''
    assert logger is not None
    # only deal with Logger, not LogAdaptor
    if not isinstance(logger, logging.Logger):
        return logger
    
    # __service name
    service = servicename if servicename is not None else getcontext(source, '__service', None)
    
    if 'agent' == service:
        return logger
    elif LOGHDLRS.has_key(service):
        hdlr = LOGHDLRS.get(service)
    elif service in getServices():
        hdlr = __initServiceLogHandler(service)
    else:
        return logger
        
    logger.addHandler(hdlr)
    return logging.LoggerAdapter(logger, {'__service' : service})
    
@synchronized(LOCK)
def __initServiceLogHandler(service):
    ''' initialize log handler for a __service 
        @param __service: __service name
        @return: log handler 
    ''' 
    try:
        logfile = 'logs/service_' + service + '.log'
        LOG.info('creating log file for __service %s at %s' % (service, logfile))
        hdlr = logging.handlers.RotatingFileHandler(logfile, maxBytes=(50*1024*1024), backupCount=3)
        formatter = logging.Formatter(LOGFMT, DATEFMT)
        hdlr.setFormatter(formatter)
        hdlr.setLevel(logging.INFO)
        hdlr.addFilter(ServiceFilter(service))
        LOGHDLRS[service] = hdlr
        return hdlr
    except:
        return __NULLLOG

def serviceRootPath():
    """ compute the path to this __service node root """
    return os.path.realpath(os.path.join(config['agent_root'], 'service_nodes'))

def dataPath(service):
    """ data directory path """
    return os.path.join(servicePath(service), '.data')

def appDataPath(service):
    """ application data directory path """
    return os.path.join(servicePath(service), '.appdata')

def expandServiceName(svcname_prefix):
    """ match and expand a __service name prefix to full __service name"""
    for service in getServices():
        if service.startswith(svcname_prefix):
            return service
    return svcname_prefix

def getServices(prefix = None):
    """ return the list of services under this agent
        if prefix is provide, return the services only match the prefix
    """
    try:
        path = serviceRootPath()
        dirs = []
        for fileName in os.listdir(path):
            if (not prefix or fileName.startswith(prefix)) and os.path.isdir(os.path.join(path, fileName)):
                dirs.append(fileName)
        dirs.sort()
        return dirs
    except:
        return []

def getManifests(service):
    """ return the list of services under this agent """
    manifests = []

    rootPath = manifestRootPath(service)
    dirContent = os.listdir(rootPath)

    for item in dirContent:
        path = os.path.join(rootPath, item)
        if (os.path.isdir(path) and not path.endswith('.inprogress')):
            if (not utils.islink(path)):
                manifests.append(item)

    return sorted(manifests)

def getAllServiceActiveManifests():
    ''' get all [(__service, activemanifest)] tuples '''
    result = set()
    for service in getServices():
        if hasActiveManifest(service):
            activeManifest = getActiveManifest(service)
            result.add((service, activeManifest))
    return result

def servicePath(service):
    """ compute the path to this __service node """
    return os.path.join(serviceRootPath(), service)

def serviceFromPath(servicepath):
    """ derive __service name from a path
        @param servicepath: __service path
        @return: __service name
    """
    servicerootpath = serviceRootPath()
    if isinstance(servicepath, str):
        if servicepath and servicepath.find(servicerootpath) >= 0:
            serviceHead = servicepath[servicepath.find(servicerootpath)+len(servicerootpath)+1:]
            service = serviceHead.split(os.path.sep)[0]
            return service
    elif isinstance(servicepath, list):
        for spath in servicepath:
            service = serviceFromPath(spath)
            if service is not None:
                return service
    return None

def serviceMetadataPath(service):
    """ __service metadata file
        @param __service: __service name
        @return: path to .metadata file
    """
    return os.path.join(servicePath(service), ".metadata.json")

def updateServiceMetaFile(service, pushedData=None, retries=1):
    """ create .metadata file for a __service in __service root with properties from state server
        @param __service: __service name
        @param stateclient: state server client
        @pushedData: more data to be pushed to .metadata file
        @return dict written to the file 
    """ 
    result_cleaned = {}
    for _ in range(retries):
        try:
            # load existing metadata
            result = readJsonServiceMeta(service)
            dataFound = False

            if pushedData is not None and type(pushedData)==dict:
                dataFound = True
                for key, value in pushedData.iteritems():
                    if type(value)==dict:
                        if key in result and type(result[key])==dict:
                            existing = result[key]
                            existing.update(value)
                            existing_cleaned = dict((k, v) for k, v in existing.iteritems() if v is not None)
                            result[key] = existing_cleaned
                        else:
                            cleaned = dict((k, v) for k, v in value.iteritems() if v is not None)
                            result[key] = cleaned
                    else:
                        result[key] = value

            # now remove none
            result_cleaned = dict((k, v) for k, v in result.iteritems() if v is not None)

            # update if there is data
            if dataFound:
                metaContentPath = serviceMetadataPath(service)
                cp = ConfigParser.SafeConfigParser()
                cp.optionxform = str
                for key, value in result_cleaned.items():
                    if isinstance(value, basestring):
                        # property file only support string as value
                        cp.set(ConfigParser.DEFAULTSECT, key, value)
                
                if os.path.exists(servicePath(service)):
                    LOG.info('create .metadata.json for __service %s' % service)
                    _writeJsonServiceMeta(result_cleaned, metaContentPath)
            else:
                LOG.info('no data found, skip .metadata file creation')
                
            #if we successfully reach here, there's no need to retry
            break
                
        except BaseException as excep:
            LOG.error('Error updating __service metadata file %s - %s' % (str(excep), traceback.format_exc(2)))
            time.sleep(1)            
            
    return result_cleaned

def _writeJsonServiceMeta(mainHash, metaContentPath):
    """Write an .metadata.json-format representation of the configuration state."""
    with open(metaContentPath, 'wb+') as fp:
        jsonStr = json.dumps(mainHash)
        fp.write(jsonStr)
        fp.write("\n")
        
def readNestJsonServiceMeta(service, topKey, keychain):
    """ convenient method to get value from a nested key chain """
    svcMeta = readJsonServiceMeta(service, [topKey]).get(topKey, None)
    if svcMeta:
        for key in keychain:
            if svcMeta and isinstance(svcMeta, dict):
                svcMeta = svcMeta.get(key, None)
            else:
                break
    return svcMeta    
        
def readJsonServiceMeta(service, keys=None):
    """ get all metadata
        @param __service: __service name
        @param keys: list of keys to get metadata for, if none, get all metadata
        @return: metadata  
    """
    result = {}
    metaContentPath = serviceMetadataPath(service)
    try:
        with open(metaContentPath, 'rb') as fp:
            result = json.load(fp)
    except Exception:
        # fine, file not exist
        pass
    if keys is not None:
        for key in result.keys():
            if key not in keys:
                del result[key]
    return result   

def writeJson(service, filename, data):
    """ write data in json format to .file under __service root folder """
    if not filename.startswith('.'):
        raise AgentException(Errors.INVALID_FILE_NAME, 'file name has to start with .')
    
    filepath = os.path.join(servicePath(service), filename + '.json')
    try:
        with open(filepath, 'wb+') as fp:
            jsonStr = json.dumps(data)
            fp.write(jsonStr)
            fp.write("\n")
    except Exception:
        pass # fine, directory does not exist

def readJson(service, filename):
    """ read data in json format from under __service root folder """
    if not filename.startswith('.'):
        raise AgentException(Errors.INVALID_FILE_NAME, 'file name has to start with .')
    filepath = os.path.join(servicePath(service), filename + '.json')
    result = {}
    try:
        with open(filepath, 'rb') as fp:
            result = json.load(fp)
    except Exception:
        # fine, file not exist
        pass
    return result   
        
def pkgRepoRootPath():
    """ package root for all downloaded packages """
    return os.path.realpath(os.path.join(config['repo_root']))

def serviceCat(service):
    """ compute the path to this __service manifest path """
    return 'Service/%s' % service

def installedPkgRootPath(service):
    """ compute the path to this __service installed packages path """
    return os.path.join(servicePath(service), 'installed-packages')

def manifestRootPath(service):
    """ compute the path to this __service manifest path """
    return os.path.join(servicePath(service), 'manifests')

def hasActiveManifest(service):
    """
    return the name of the active manifest under a specific __service
    @param __service: name of __service
    @return: existence of active manifest
    """
    activePath = activeManifestPath(service)
    return activePath is not None and activePath != ''

def activeManifestPath(service):
    """ compute the path to this __service active manifest """
    activePath = manifestPath(service, ACTIVE_MANIFEST)
    if (not os.path.exists(activePath)):
        return ''

    realManifest = readlink(activePath)
    return realManifest

def getActiveManifest(service):
    """ return the name of the active manifest under a specific __service """
    return os.path.basename(activeManifestPath(service))

def manifestPath(service, manifest=ACTIVE_MANIFEST):
    """ compute the path to a __service manifest """
    return os.path.join(manifestRootPath(service), manifest)

def manifestContentPath(service, manifest):
    """ compute the path to this manifest content with package details """
    return os.path.join(manifestPath(service, manifest), ".manifest")

def packagesInManifest(service, manifest=ACTIVE_MANIFEST):
    """ return the list of packages in the manifest.  The list is just the names not paths in the order specified during manifest creation.
    @param __service:    name of the __service
    @param manifest:   name of the manifest
    @return: list with names of packages in it.  If none, returns an empty list []
    """
    #Defaulting to list directory when manifest contents are not found.
    path = manifestPath(service, manifest)
    dirs = []
    for fileName in os.listdir(path):
        if os.path.isdir(os.path.join(path, fileName)):
            dirs.append(fileName)
    dirs.sort()
    return dirs

def packagePath(service, manifest, package):
    """ compute the path to a __service manifest package """
    return os.path.join(manifestPath(service, manifest), package)

def moduleRootPath(service = 'agent'):
    """ plugable modules folder root path """
    return os.path.join(servicePath(service), "modules")

def modulePath(service, module):
    """ plugbale module path """
    return os.path.join(moduleRootPath(service), module)

def getModules(service = 'agent'):
    """ return the list of services under this agent """
    path = moduleRootPath(service)
    dirs = os.listdir(path)
    dirs.sort()
    return dirs

def getModuleSymLinks(service = 'agent'):
    """ return all the symlinks from manifests to packages for a given service"""

    LOG.debug('calling getAllSymLinks %s' % service)
    linkedPaths = []
    mRootPath = moduleRootPath(service)
    LOG.debug('moduleRootPath is %s' % mRootPath)
    for pkgPath in os.listdir(mRootPath):
        try:
            LOG.debug('pkgPath is %s' % pkgPath)
            if not os.path.isfile(os.path.join(mRootPath, pkgPath)) and islink(os.path.join(mRootPath, pkgPath)):
                targetPath = os.path.abspath(readlink(os.path.join(mRootPath, pkgPath)))
                linkedPaths.append(targetPath)
                LOG.debug('targetPath is %s ' % targetPath)
        except BaseException as exc:
            LOG.error('failed to read link for the pkg path %s' % str(exc))
    return linkedPaths


def getPackageInitConfig(service, manifest, package):
    """ return init config for a package (cronus.ini)
        @return: PkgInitConfig
    """
    pkgPath = packagePath(service, manifest, package)
    return PkgInitConfig(pkgPath).getConfigs() if hasPackageInitConfig(service, manifest, package) else {}

def hasPackageInitConfig(service, manifest, package):
    """ whether cronus.ini exist """
    pkgPath = packagePath(service, manifest, package)
    return PkgInitConfig.exist(pkgPath)

def processModule(service, module, isAdd=True):
    """ process config file in package, load/unload dynamic controllers and routes """
    
    pkgPath = modulePath(service, module)
    if PkgInitConfig.exist(pkgPath):
        
        pkgInit = PkgInitConfig(pkgPath)
        pkgCfg = pkgInit.getConfigs()
        
        if pkgCfg is not None and 'controller' in pkgCfg:
            # import controller package from cronus.ini
            sys.path.append(pkgPath)
            ctrlr = __import__(pkgCfg['controller'], fromlist=['ControllerMeta'])
            routes = ctrlr.ControllerRoutes
            controllers = ctrlr.ControllerClass

            # now extends existing routes to include new routes from module
            # all routes start with /module/{module}/user defined routes
            mapper = config['routes.map']                
#             for i, route in enumerate(routes):
#                 route.name = '%s.%s' % (module, str(i))
            mapper.extend(routes, ('/modules/%s' % module))
            mapper.create_regs()

            # now load user defined controller class so that pylon can lookup controller by its name            
            appGlobal = config['pylons.app_globals']
            for controllerName, (pymodule, controller) in controllers.items():
                 
                # add new controllers
                if isAdd:
                    routemap = dynautils.setuppath(pkgPath, pymodule, [controller])
                    if routemap[controller] is not None:
                        appGlobal.dynacontrollers[controllerName] = routemap[controller]
                         
                # remove controllers
                elif controllerName in appGlobal.dynacontrollers.keys():
                    del appGlobal.dynacontrollers[controllerName]
                    dynautils.removepath(pkgPath, pymodule, [controller])


def processControllerInPackage(service, manifest=ACTIVE_MANIFEST, activateFlow=True):
    """ process config file in package, load/unload dynamic controllers and routes """
    for package in packagesInManifest(service, manifest):
        pkgPath = packagePath(service, manifest, package)
        pkgInit = PkgInitConfig(pkgPath)
        pkgCfg = pkgInit.getConfigs()
        if pkgCfg is not None and 'controller' in pkgCfg:
            sys.path.append(pkgPath)
            ctrlr = __import__(pkgCfg['controller'], fromlist=['ControllerMeta'])
            (routes, controllers) = ctrlr.ControllerMeta

            mapper = config['routes.map']                
            #override names of all routes to that of __service we are operating now in 
            for i, route in enumerate(routes):
                route.name = service + "." + str(i)
                                
            mapper.extend(routes, "/modules")
            mapper.extend(routes, ('/services/%s' % service))
            mapper.create_regs()
            for key, (module, controller) in controllers.items():
                if activateFlow:
                    routemap = dynautils.setuppath(pkgPath, module, [controller])
                    if routemap[controller] is not None:
                        setattr(routemap[controller], '__service', service)
                        config['pylons.app_globals'].dynacontrollers[key] = routemap[controller]
                        
                elif key in config['pylons.app_globals'].dynacontrollers.keys():
                    del config['pylons.app_globals'].dynacontrollers[key]
                    dynautils.removepath(pkgPath, module, [controller])
                    
def getMonitorPaths(service, manifest, package):
    """ return the list of monitor paths in the (manifest, package) pair.
    @param __service:   name of the __service
    @param manifest:  name of the manifest
    @param package:   name of the package
    @return: list with paths of monitors in it.  If none, returns an empty list []
    """

    manPath = manifestPath(service, manifest)
    path = os.path.join(manPath, package, 'cronus', 'scripts', 'monitors')
    monitorPaths = []
    if os.path.exists(path):
        monitorPaths = filter(os.path.isfile, [os.path.join(path, child) for child in os.listdir(path)])

    return sorted(monitorPaths)

def getMonitorScriptPath(service, manifest, package, script):
    """ return the path to a monitor script
    @param __service:   name of the __service
    @param manifest:  name of the manifest
    @param package:   name of the package
    @param script:    script name
    @return: complete path to the script
    """
    manPath = manifestPath(service, manifest)
    path = os.path.join(manPath, package, 'cronus', 'scripts', 'monitors', script)
    if os.path.exists(path):
        return path
    else:
        return None
    
def getPackageByName(service, manifest, pkgnamePrefix):
    """ finding an existing package that matches a package name prefix
        @param __service: __service
        @param manifest: if None, try active manifest first, then non active manifests
        @param pkgnamePrefix: package name pattern to match against   
    """
    if not service:
        raise AgentException(Errors.MANIFEST_MISSING_SERVICE, 'missing __service')
    if not pkgnamePrefix:
        raise AgentException(Errors.PACKAGE_PATH_ERROR, 'package name prefix is missing for reuse of package')
    
    if manifest is None:
        manifest = ACTIVE_MANIFEST if hasActiveManifest(service) else getManifests(service)[0]
        
    if manifest is None or not os.path.exists(manifestContentPath(service, manifest)):
        raise AgentException(Errors.MANIFEST_NOT_FOUND, 'cannot find .manifest for manifest %s ' % manifest)
    
    fullPkgLoc = None
    with open(manifestContentPath(service, manifest)) as mfile:
        lines = mfile.readlines()
        for line in lines:
            tokens = line.split('/')
            if tokens[-1].startswith(pkgnamePrefix):
                # found
                fullPkgLoc = line.rstrip()
                break
    return fullPkgLoc                


class PkgInitConfig:
    """ cornus.ini """
    
    def __init__(self, pkgPath):
        """ constructor """
        self.path = os.path.join(pkgPath, CRONUS_DIR, INI_FILENAME)
        self.cfg = {}
        try:
            with open(self.path, 'rb') as fp:
                self.cfg = json.load(fp)
        except Exception:
            # fine, file not exist
            pass
        
    def getConfigs(self):
        """ get all configs """
        return self.cfg
    
    @staticmethod
    def exist(pkgPath):
        """ whether cronus.ini exist """
        return os.path.exists(os.path.join(pkgPath, CRONUS_DIR, INI_FILENAME))

class NullHandler(logging.Handler):
    ''' a null log handler '''
    def emit(self, record):
        pass
        
__NULLLOG = NullHandler() 
                
