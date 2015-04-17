#pylint: disable=W0703, W0141,R0914,R0911,W0105
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
""" Agent Manifest File """


from agent.lib.base import BaseController
from agent.lib.result import doneResult
from agent.lib.result import errorResult
from agent.lib.result import statusResult
from agent.lib.utils import readlink, islink, trackable
from agent.controllers.service import ServiceController
from agent.lib.errors import Errors, ManifestNotFoundError
from agent.lib.errors import AgentException
from agent.lib.package import PackageUtil
from agent.lib import manifestutil, configutil
from agent.controllers.modulelog import ModulelogController
from agent.lib.agent_thread.manifest_delete import ManifestDelete
from agent.lib.security.agentauth import authorize

from pylons import request, response, config
import glob
import os
import json
import logging
import traceback
from beaker.converters import asbool

LOG = logging.getLogger(__name__)

class ManifestController(BaseController):
    """ Manifest Controller Class """

    @authorize()
    @trackable()
    def post(self, service, manifest):
        """ Create a new service object """
        from agent.lib.agent_thread.manifest_create import ManifestCreate

        try:

            LOG.info('Post for service (%s) and manifest (%s) with body: %s',
                      service, manifest, request.body)

            # check to see if the manifest already exists
            path = ManifestController.manifestPath(service, manifest)
            if (os.path.isdir(path)):
                return doneResult(request, response, httpStatus = 201, controller = self)

            # parse the body
            if (request.body == ""):
                return errorResult(request, response, Errors.MANIFEST_PACKAGE_PARSING_ERROR,
                                   'No body found in post command',
                                   controller = self)

            body = json.loads(request.body)

            packages = body['package']
            forcedPackages = body['forcePackageName'] if 'forcePackageName' in body else None
            skipProp = asbool(body['skipProp']) if 'skipProp' in body else configutil.getConfigAsBool('download_skip_prop') 

            LOG.debug('pkgs = %s, %s', packages, forcedPackages)

            # parse the package list
            for idx, package in enumerate(packages):
                # to support reuse of an package from an existing manifest (active if possible)
                # without sending the complete package location in request body
                if package.startswith('/'):
                    packageRef = package
                    tokens = package.split('/')
                    pkgnamePrefix = tokens[-1].rstrip()
                    fullPkgLoc = manifestutil.getPackageByName(service, manifest = None, pkgnamePrefix = pkgnamePrefix)
                    if fullPkgLoc is None:
                        return errorResult(request, response, Errors.MANIFEST_PACKAGE_DOES_NOT_EXIST,
                                           'manifest (%s/%s) package (%s) does not exist' %
                                           (service, manifest, packages), controller = self)
                    else:
                        LOG.info('expanding package reuse ref %s with full package location %s' % (packageRef, fullPkgLoc))
                        packages[idx] = fullPkgLoc

            appGlobal = config['pylons.app_globals']
            # start a thread to create the package
            manThread = ManifestCreate(appGlobal.threadMgr, service, manifest, packages, forcePackages = forcedPackages, skipProp = skipProp)
            self.injectJobCtx(manThread)
            manThread.start()
            manThread.threadMgrEvent.wait()

            return statusResult(request, response, manThread, controller = self)
        except AgentException as excep:
            return errorResult(request, response, error = excep.getCode(), errorMsg = excep.getMsg(), controller = self)
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for activateManifest(%s/%s) - %s - %s' %
                               (service, manifest, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def delete(self, service, manifest):
        """ Delete a new service object """
        try:
            path = ManifestController.manifestPath(service, manifest)
            if (not os.path.isdir(path)):
                return errorResult(request, response, Errors.MANIFEST_NOT_FOUND,
                                   'manifest (%s/%s) missing service' % (service, manifest),
                                   controller = self)

            # first check that this isn't the active manifest
            path = os.path.join(ServiceController.manifestPath(service), 'active')
            if (os.path.exists(path)):
                activePath = os.path.basename(readlink(path))
                deletePath = os.path.basename(ManifestController.manifestPath(service, manifest))

                if (activePath == deletePath):
                    return errorResult(request, response, Errors.MANIFEST_DELETING_ACTIVE_MANIFEST,
                                       'Manifest(%s, %s) attempting to delete active manifest'
                                       % (service, manifest),
                                       controller = self)

            # now try to delete the manifest directory
            appGlobal = config['pylons.app_globals']
            manThread = ManifestDelete(appGlobal.threadMgr, service, manifest)
            self.injectJobCtx(manThread)
            manThread.start()
            manThread.threadMgrEvent.wait()

            return statusResult(request, response, manThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for delete manifest(%s/%s) - %s - %s' %
                               (service, manifest, str(excep), traceback.format_exc(2)),
                               controller = self)

    @trackable()
    def get(self, service, manifest):
        """ Get a new service object """
        LOG.info('Get for service (%s) and manifest (%s)', service, manifest)

        try:
            # first check that the manifest directory exists
            path = ManifestController.manifestPath(service, manifest)
            if (not os.path.isdir(path)):
                return errorResult(request, response, Errors.MANIFEST_NOT_FOUND,
                                   'manifest (%s/%s) missing service' % (service, manifest),
                                   controller = self)

            # now go through the list of packages in the manifest
            packages = []
            packageLinkNames = glob.glob(os.path.join(self.manifestPath(service, manifest), '*'))
            for packageLink in packageLinkNames:

                package = readlink(packageLink)

                LOG.debug('Get package (%s) in manifest (%s)', package, manifest)

                # deal with the case where the package has a / or \ (for windoz) at the end
                package = package.rstrip('/')
                package = package.rstrip('\\')

                # the name of the package can be constructed from the last two path components
                (head, version) = os.path.split(package)
                (head, name) = os.path.split(head)

                LOG.debug('Add package %s-%s.cronus' % (name, version))
                packages.append('%s-%s.cronus' % (name, version))

        except OSError as excp:
            return errorResult(request, response, Errors.MANIFEST_PATH_ERROR,
                               'Manifest(%s, %s) path error: %s' % (service, manifest, str(excp)),
                               controller = self)

        return doneResult(request, response, result = packages, controller = self)


    @trackable()
    def log(self, service, manifest):
        """ Get manifest logs """
        LOG.info('Get for service (%s) and manifest (%s)', service, manifest)

        try:
            # first check that the manifest directory exists
            path = manifestutil.manifestPath(service, manifest)
            if (not os.path.isdir(path)):
                return errorResult(request, response, Errors.MANIFEST_NOT_FOUND,
                                   'manifest (%s/%s) missing service' % (service, manifest),
                                   controller = self)
            packageList = manifestutil.packagesInManifest(service, manifest)
            return ModulelogController.prepareOutput(packageList, ("/log/list/applog?service=%s&manifest=%s&package=" % (service, manifest)), manifestutil.manifestPath(service), "List Of Packages")
        except OSError as excp:
            return errorResult(request, response, Errors.MANIFEST_PATH_ERROR,
                               'Manifest(%s, %s) path error: %s' % (service, manifest, str(excp)),
                               controller = self)
            

    #####################################################
    # utility members
    #####################################################

    @staticmethod
    def manifestContentPath(service, manifest):
        """ compute the path to this manifest content with package details """
        return os.path.join(ManifestController.manifestPath(service, manifest), ".manifest")

    @staticmethod
    def manifestPath(service, manifest):
        """
        compute the path to this manifest
        @param service:    name of the service
        @param manifest:   name of the manifest
        """
        return os.path.join(ServiceController.manifestPath(service), manifest)

    @staticmethod
    def getActiveManifest(service):
        """ return the name of the active manifest under a specific service """
        return os.path.basename(ManifestController.getActiveManifestPath(service))

    @staticmethod
    def getActiveManifestPath(service):
        """
        return the name of the active manifest under a specific service
        @param service: name of service
        @return: path of active manifest, or empty string if no active manifest
        """
        activePath = os.path.join(ServiceController.manifestPath(service), 'active')
        if (not os.path.exists(activePath)):
            return ''

        return readlink(activePath)

    @staticmethod
    def getManifests(service):
        """ return the list of manifests under a specific service """
        from agent.lib.agent_thread.manifest_create import ManifestCreate

        manifests = []

        dirContent = os.listdir(ServiceController.manifestPath(service))

        for item in dirContent:
            path = os.path.join(ServiceController.manifestPath(service), item)
            if (os.path.isdir(path) and not ManifestCreate.isInProgress(path)):
                if (not islink(path)):
                    manifests.append(item)

        return sorted(manifests)

    @staticmethod
    def getPackages(service, manifest):
        """ return the list of packages in the manifest.  The list is just the names not paths in the order specified during manifest creation.
        @param service:    name of the service
        @param manifest:   name of the manifest
        @return: list with names of packages in it.  If none, returns an empty list []
        """
        mfContentPath = ManifestController.manifestContentPath(service, manifest)
        if (os.path.exists(mfContentPath)):
            packages = []
            mfContentFile = file(mfContentPath, 'r')
            for packageUri in mfContentFile:
                pkgObj = PackageUtil.parseUri(packageUri.rstrip())
                packages.append(pkgObj['packageName'])
            return packages
        else:
            #Defaulting to list directory when manifest contents are not found.
            path = ManifestController.manifestPath(service, manifest)
            packages = os.listdir(path)

            return sorted(packages)

    @staticmethod
    def getPackagePaths(service, manifest):
        """
        return the list of package paths for a give service and manifest name
        @param service:     name of service
        @param manifest:    name of manifest
        @return: list of package paths within manifest
        @throws: ManifestNotFoundError    if manifest doesn't exist
        """
        path = ManifestController.manifestPath(service, manifest)
        if not os.path.isdir(path):
            raise ManifestNotFoundError("manifest path does not exist: " + path)

        packageDirs = [ packageDir for packageDir in os.listdir(path) if os.path.isdir(os.path.join(path, packageDir)) ]
        return map(lambda x: os.path.join(path, x), packageDirs)


    @staticmethod
    def getMonitorPaths(service, manifest, package):
        """ return the list of monitor paths in the (manifest, package) pair.
        @param service:   name of the service
        @param manifest:  name of the manifest
        @param package:   name of the package
        @return: list with paths of monitors in it.  If none, returns an empty list []
        """

        manPath = ManifestController.manifestPath(service, manifest)
        path = os.path.join(manPath, package, 'cronus', 'scripts', 'monitors')
        monitorPaths = []
        if os.path.exists(path):
            monitorPaths = filter(os.path.isfile, [os.path.join(path, child) for child in os.listdir(path)])

        return sorted(monitorPaths)

    @staticmethod
    def getAllSymLinks(service):
        """ return all the symlinks from manifests to packages for a given service"""

        LOG.debug('calling getAllSymLinks %s' % service)
        linkedPaths = []
        manPath = ServiceController.manifestPath(service)
        LOG.debug('manifestPath is %s' % manPath)
        for path in os.listdir(manPath):
            LOG.debug('path is %s' % path)
            if not islink(os.path.join(manPath, path)):
                LOG.debug('path is dir not a link')
                pkgPaths = [ packageDir for packageDir in os.listdir(os.path.join(manPath, path)) ]
                LOG.debug('pkgPaths is %s' % pkgPaths)
                for pkgPath in pkgPaths:
                    try:
                        LOG.debug('pkgPath is %s' % pkgPath)
                        if not os.path.isfile(os.path.join(manPath, path, pkgPath)) and islink(os.path.join(manPath, path, pkgPath)):
                            LOG.debug('pkgPaths is %s' % pkgPath)
                            targetPath = os.path.abspath(readlink(os.path.join(manPath, path, pkgPath)))
                            linkedPaths.append(targetPath)
                            LOG.debug('targetPath is %s ' % targetPath)
                    except BaseException as exc:
                        LOG.error('failed to read link for the pkg path %s' % str(exc))
        return linkedPaths

