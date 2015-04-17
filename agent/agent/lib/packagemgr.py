#pylint: disable=W0511,C0103,W0621,E1101,W0212,W0703,R0912,W0611,W0105
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
Package Manager

This class is responsible for maintaining the packages in the <agent_root>/packages directory.
It will download packages
Give progress of downloading packages
Garbage collect packages

The state is stored on the filesystem
all in progress (denoted with a .inprogress files will be deleted at startup)
"""

import pylons
import glob
import threading
import time
import os
import traceback

from agent.lib.package import PackageUtil
from agent.lib.agent_thread.download_thread import DownloadThread
import logging
from agent.lib import agenthealth, manifestutil
from agent.lib.errors import Errors
from agent.lib.agent_thread.service_delete import ServiceDelete

LOG = logging.getLogger(__name__)
GCLOG = logging.getLogger('gc')

class PackageMgr(threading.Thread):
    """ Package Manager Class """

    def __init__(self, garbageFreq, maxPackageAge):
        """ Initialize the Package Mgr """
        threading.Thread.__init__(self)

        self.__stop = False

        self.__garbageFreq = float(garbageFreq)
        self.__maxPackageAge = float(maxPackageAge)

        self.__inProgressPackages = {}
        self.__inProgressLock = threading.RLock()
        
        PackageMgr.runOnceOnStartup()

    def resetDownloadThreadMap(self):
        """ clear map, cleanup all services invoked, this ensures that fresh threads are spawned after cleanup """
        self.__inProgressPackages = {}

    def getPackageDownloadThread(self, packageUri, skipProp = True):
        """
        getPackage(package)
        @params package - URI (e.g. http://repo/repo/package-0.1.4.cronus)
        in case of bittorrent - http://repo/repo/package-0.1.4.cronus.torrent
        get the DownloadThread object for a particular package URI
        If a DownloadThread does not exist, create one
        """

        # try to get create the package
        uriDict = PackageUtil.parseUri(packageUri)

        with self.__inProgressLock:
            # if the package is already in progress, just return that object
            if (uriDict['package'] in self.__inProgressPackages):
                thread = self.__inProgressPackages[uriDict['package']]
                if thread.isAlive():
                    return thread

            # start package download - either it is a new download, or a prev thread errored-out
            appGlobal = pylons.config['pylons.app_globals']
            downloadThread = DownloadThread(appGlobal.threadMgr, packageUri, packageloc=None, skipProp = skipProp)
            downloadThread.start()

            # add to the list
            self.__inProgressPackages[uriDict['package']] = downloadThread

        return downloadThread

    @staticmethod
    def packagePath():
        """ compute the path to the packages """
        return os.path.realpath(os.path.join(pylons.config['agent_root'], 'packages'))
    
    @staticmethod
    def runOnceOnStartup():
        """ one time check at startup """
        try:
            # if the packages directory isn't there create it
            if (not os.path.isdir(PackageMgr.packagePath())):
                try:
                    os.remove(PackageMgr.packagePath())
                except OSError:
                    pass
                os.makedirs(PackageMgr.packagePath())
        except Exception as exc:
            LOG.error('Unable to create packages directory %s' % str(exc))


    #####################################################
    # Garbage collection
    #####################################################

    def stop(self):
        """
        stop(self)

        stop the garbage collection thread
        """

        self.__stop = True

    def run(self):
        """
        the garbage collection thread body
        go through the list of packages and delete packages over a certain threshold
        two variables affect operation
        packageMgr_gc_freq = how log GC sleeps for between checks
        pacageMgr_package_age = how old a package can get to before it's deleted

        go through the list of inprogress threads and remove all threads that are done
        """
        #pylint:disable=R0914, R0912, R0915
        while (self.__stop == False):
            time.sleep(self.__garbageFreq)

            try: 
                # GC in progress hash
                self.__inProgressLock.acquire()
                try:
                    for key in self.__inProgressPackages.keys():
                        if (not self.__inProgressPackages[key].isAlive()):
                            del self.__inProgressPackages[key]
    
                finally:
                    self.__inProgressLock.release()
    
    
                if not self.__stop:
                    # go through all the packages and see if they are older than the threshold
                    for filename in glob.glob(os.path.join(PackageMgr.packagePath(), '*.cronus.inprogress')):
                        if (time.time() > os.path.getatime(filename) + float(pylons.config['packageMgr_package_age'])):
                            try:
                                GCLOG.info('Garbage collecting package(%s)' % filename)
                                LOG.info('Garbage collecting package(%s)' % filename)
                                os.remove(filename)
                            except OSError, osErr:
                                GCLOG.error('Unable to garbage collect %s - %s' % (filename, osErr))
                                LOG.error('Unable to garbage collect %s - %s' % (filename, osErr))
                        
                    for filename in glob.glob(os.path.join(PackageMgr.packagePath(), '*.cronus')):
                        LOG.debug('garbage collection check in progress for filename %s' % filename)
                        try:
                            if (time.time() > os.path.getatime(filename) + float(pylons.config['packageMgr_package_age'])):
                                LOG.info('Garbage collecting package(%s)' % filename)
                                os.remove(filename)
                                if os.path.exists(filename + '.prop'):
                                    os.remove(filename + '.prop')
                                if os.path.exists(filename + '.torrent'):
                                    os.remove(filename + '.torrent')
                                if os.path.exists(filename + '.inprogress'):
                                    os.remove(filename + '.inprogress')
                        except OSError, osErr:
                            GCLOG.error('Unable to garbage collect %s - %s' % (filename, osErr))
                            LOG.error('Unable to garbage collect %s - %s' % (filename, osErr))
                    #appGlobal = pylons.config['pylons.app_globals']
                #import pdb;pdb.set_trace();
                if not self.__stop:
                    PackageUtil.cleanupOrphanedPackages(False)
    
                packageMount = pylons.config['agent_root']
    
                if(not self.__stop and agenthealth.needAggressiveGC(packageMount)):
                    PackageUtil.forceCleanUpDownloadedPkgs()
                    
                # validate all services and remove rogue services
                PackageMgr.cleanRogueService()
                
            except Exception:
                code = Errors.UNKNOWN_ERROR
                msg = 'Failed to Garbage Collection ' + '(#' + str(code) + '). ' + traceback.format_exc(5)
                GCLOG.error(msg)
                LOG.error(msg)
                
    @staticmethod
    def cleanRogueService():
        """ delete rogue services """
        try:
            services = manifestutil.getServices()
            for service in services:
                path = manifestutil.servicePath(service)
                for idx in range(3):
                    if os.path.exists(os.path.join(path, 'manifests')):
                        break
                    time.sleep(2)
                    if idx == 2:
                        appGlobal = pylons.config['pylons.app_globals']
                        LOG.info('service %s does not have manifests folder, cleanup the rogue service' % service)
                        deleteThread = ServiceDelete(appGlobal.threadMgr, service, path)
                        deleteThread.run()
                        LOG.info('service %s cleaned up' % service)
                        break
        except Exception:
            LOG.error('failed to check and cleanup rogue service' + traceback.format_exc(5))            
