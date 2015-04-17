#pylint: disable=W0703,W0511,W0402,R0911,R0915,R0912,W0331,W0612,R0904,W0105
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
""" Thread to download a package """

from agent.lib import utils, contextutils
from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.errors import Errors, FileNotFoundError, AgentException
from agent.lib.package import PackageUtil
from agent.lib.utils import loadPropFile
from random import randint
import json
import logging
import os
import pylons
import time
import traceback
import urlgrabber


LOG = logging.getLogger(__name__)

class DownloadThread(AgentThread):
    """ Separate thread to start download """
    def __init__(self, threadMgr, packageUri, packageloc, path = None, category = None, skipProp = True):
#        cat = 'DC_DowloadThread' + str(datetime.now())
        AgentThread.__init__(self, threadMgr, cat = category, name = 'download_thread')
        self.__path = pylons.config['repo_root']
        if path is not None:
            self.__path = path
        # check to see if the package path exists
        if (not os.path.isdir(self.__path)):
            msg = 'Package path(%s) does not exist' % self.__path
            LOG.error(msg)
            raise AgentException(Errors.PACKAGE_PATH_ERROR, msg)
        
        self.__uriDict = PackageUtil.parseUri(packageUri, self.__path, packageloc)
        self.__prop = {}
        self.__error = None
        self.__progress = 0.0
        self.__timeouts = None
        self.__skipProp = skipProp

    def getUriDict(self):
        ''' Get the package info dictionary '''
        return self.__uriDict

    def beforeRun(self):
        """ set external timeout values if any """
        # set timeout
        if contextutils.existcontext(self, 'thread_timeout'):
            self._timeout = contextutils.getcontext(self, 'thread_timeout', self._timeout)
        
        if contextutils.existcontext(self, 'thread_progress_timeout'):
            self._progressTimeout = contextutils.getcontext(self, 'thread_progress_timeout', self._progressTimeout)

    def doRun(self):
        """ Progress Info:
        0 : start
        1 - 2 : prop file download
        3 - 5 : checking existing data (hash verification)
        6 - 8 : allocating disk space (in case of pre_allocate
        9 - 99 : downloading data
        100 : download complete.
        """
        try:
            self.__startDownload()
        except AgentException as exc:
            msg = 'Error for package (%s) - %s' % (self.__uriDict['package'], str(exc))
            LOG.error(msg)
            self._updateStatus(httpStatus = 500, error = exc.getCode(), errorMsg = msg)
        except Exception as exc:
            msg = 'Unknown error for package (%s) - %s' % (self.__uriDict['package'], str(exc))
            LOG.error(msg)
            self._updateStatus(httpStatus = 500, error = Errors.UNKNOWN_ERROR, errorMsg = msg)

    def __startDownload(self):
        """ actual download logic """
        try:
            LOG.info("Starting package download for package %s" % self.__uriDict['package'])

            # check to see if there's an in progress file,
            # since PackageMgr guarantees that duplicate threads will not be spawned
            # for same pkg, assume an existing thread was killed.
            # attempt to clean up package n move
            if (os.path.exists(self.__uriDict['inProgressPackagePath'])):
                LOG.debug('In progress file (%s) already exists. Will validate and reattempt download if necessary' % self.__uriDict['inProgressPackagePath'])


            if os.path.exists(self.__uriDict['packagePath']):
                if (os.path.exists(self.__uriDict['propPath']) and
                    PackageUtil.validateProp(self.__uriDict['propPath']) and
                    PackageUtil.validatePackage(self.__uriDict['packagePath'], self.__uriDict['propPath'])):
                    msg = 'The package already exists. Will NOT download duplicate package' + self.__uriDict['packagePath']
                    LOG.info(msg)
                    os.utime(self.__uriDict['packagePath'], None)
                    os.utime(self.__uriDict['propPath'], None)
                    self._updateStatus(progress = 100)
                    # NOTE: this is a normal exit not an error!
                    return
                LOG.warning('The package already exists. However package prop (%s) failed validation. Downloading package.' % self.__uriDict['propPath'])

            # Delete all traces of package before beginning download
            LOG.info('Cleaning up all packages for %s ' % self.__uriDict['packagePath'])
            PackageUtil.cleanUpPackage(self.__uriDict['inProgressPackagePath'],
                                   self.__uriDict['packagePath'],
                                   self.__uriDict['propPath'])

            AgentThread._updateProgress(self, 0)
            
            if not self.__skipProp:
                # First, download .prop file
                LOG.info('Starting download of prop file %s - %s' % (self.__uriDict['propUri'], self.__uriDict['propPath']))
                self.__download_prop_file()
                try:
                    self.__prop = loadPropFile(self.__uriDict['propPath'])
                except FileNotFoundError:
                    raise AgentException(Errors.DC_MISSING_PROP_FILE,
                                         'Prop file (%s) unable to read or did not parse' % (self.__uriDict['propPath']))
            AgentThread._updateProgress(self, 2)

            self.__setProgressTimeouts()

            if self.__uriDict['scheme'] == 'http':
                # try download 3 times, with random sleep
                for _ in range(3):
                    try:
                        sotimeout = float(pylons.config['download_thread_sotimeout'])
                        proxies = json.loads(pylons.config['urlgrabber_proxies'])
                        urlgrabber.urlgrab(self.__uriDict['uri'], 
                                           self.__uriDict['inProgressPackagePath'],
                                           checkfunc = None if self.__skipProp else (PackageUtil.validateDownload, (), {}),
                                           progress_obj = DownloadProgress(self),
                                           throttle = float(pylons.config['package_throttle']),
                                           bandwidth = int(pylons.config['package_bandwidth']),
                                           keepalive = 0,
                                           timeout = sotimeout,
                                           proxies = proxies) 
                        break
                    except Exception as exc:
                        msg = 'Download error %s - %s' % (str(exc), traceback.format_exc(3))
                        LOG.warning(msg)
                        randsleep = randint(30, 60)                
                        time.sleep(randsleep)
                    
            else:
                # oops! only http and bittorrent supported now
                raise AgentException(Errors.DC_UNSUPPORTED_PROTOCOL, 'Only http protocols is supported at the moment')

            self._checkStop()

            if not self.__skipProp:
                if (not PackageUtil.validatePackage(self.__uriDict['inProgressPackagePath'], self.__uriDict['propPath'])):
                    raise AgentException(Errors.DC_FAILED_VALIDATE, 'Package ' + self.__uriDict['packagePath'] + ' failed validation')
                os.utime(self.__uriDict['propPath'], None)
                utils.rchmod(self.__uriDict['propPath'], "777", 'no')
            
            LOG.info('Download complete, will now rename and do validation on this file %s' % self.__uriDict['packagePath'])
            os.rename(self.__uriDict['inProgressPackagePath'], self.__uriDict['packagePath'])
            os.utime(self.__uriDict['packagePath'], None)
            utils.rchmod(self.__uriDict['packagePath'], "777", 'no')
            LOG.info("Download complete, Validation completed, updating progress to 100")
            self._updateStatus(progress = 100)

        except AgentException, exc:
            self._updateStatus(httpStatus = 500, progress = 0, error = exc.getCode(), errorMsg = exc.getMsg())
            msg = 'Download error %s - %s' % (str(exc), traceback.format_exc(3))
            LOG.error(msg)
            raise exc
        except Exception, exc:
            self._updateStatus(httpStatus = 500, progress = 0, error = Errors.UNKNOWN_ERROR, errorMsg = str(exc))
            msg = 'Unknown download error %s - %s' % (str(exc), traceback.format_exc(3))
            LOG.error(msg)
            raise exc
        finally:
            LOG.info("Completed package download for package %s" % self.__uriDict['package'])

    def __setProgressTimeouts(self):
        """ Setting timeout for download thread.  The timeouts uses the size of the package."""
        if not self.__skipProp:
            timeout = float(self.__prop['size']) / float(pylons.config['download_thread_rate_per_sec'])
            timeout = max(timeout, float(pylons.config['download_thread_min_time']))
            timeout = min(timeout, float(pylons.config['download_thread_max_time']))

            progressTimeout = timeout * float(pylons.config['download_thread_progress_ratio'])
            progressTimeout = max(progressTimeout, float(pylons.config['download_thread_min_progress_time']))
        
            self.extendTimeout(timeout)
            self.setProgressTimeout(progressTimeout)
            self.__timeouts = (timeout, progressTimeout)
            
        else:
            self.__timeouts = (self._timeout, self._progressTimeout)
        
        LOG.debug('Using timeout=%s and progress timeout=%s' % self.__timeouts)

    def getProgressTimeouts(self):
        """
        Getting timeout from the download thread.  The timeout is either None or consists
        provides (total timeout, progress timeout)
        """
        return self.__timeouts

    def stop(self):
        """ stopping client before calling the super method """
        LOG.info('STOP download thread is called stopping')
        AgentThread.stop(self)

    def _updateHttpProgress(self, amount_read):
        """ custom progress computation """
        if not self.__skipProp:
            progress = 2 + ((float(amount_read) / float(self.__prop['size'])) * (97))
            AgentThread._updateProgress(self, progress)
        else:
            progress = min(self.getProgress(), 97) + 1
            AgentThread._updateProgress(self, progress)
            
        self._checkStop()

    def __download_prop_file(self):
        """ download prop file and validate """
        # retry 3 times download prop file
        for _ in range(3):
            try:
                sotimeout = float(pylons.config['download_thread_sotimeout'])
                proxies = json.loads(pylons.config['urlgrabber_proxies'])
                urlgrabber.urlgrab(
                            self.__uriDict['propUri'], 
                            self.__uriDict['propPath'], 
                            keepalive = 0, 
                            timeout = sotimeout,
                            proxies = proxies)
                break
            except Exception:
                randsleep = randint(30, 60)                
                time.sleep(randsleep)
        
        if (not os.path.exists(self.__uriDict['propPath'])):
            raise AgentException(Errors.DC_MISSING_PROP_FILE,
                            'Prop file (%s) does not exist' % (self.__uriDict['propPath']))
        
        if not PackageUtil.validateProp(self.__uriDict['propPath']):
            raise AgentException(Errors.DC_MISSING_PROP_FILE,
                            'Prop file (%s) failed validation' % (self.__uriDict['propPath']))

#pylint: disable=W0212
class DownloadProgress(object):
    """ object to track the progress of a package """

    def __init__(self, thread):
        """ constructor """
        object.__init__(self)
        self.__thread = thread

    def start(self, filename = None, url = None, basename = None,
              size = None, now = None, text = None):
        """ called during the start of the progress """
        pass

    def update(self, amount_read, now = None):
        """ update the progress """
        self.__thread._updateHttpProgress(amount_read)

    def end(self, amount_read, now = None):
        """ end the progress """
        pass

