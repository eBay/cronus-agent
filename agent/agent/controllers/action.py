#pylint: disable=W0703,E1101,R0904,R0914,W0105
""" 
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

Action Controller """

from pylons import request, response, config
import logging
import json
import traceback
import os

from agent.lib.base import BaseController
from agent.controllers.manifest import ManifestController
from agent.lib.agent_thread.activate_manifest import ActivateManifest
from agent.lib.agent_thread.restart_service import RestartService
from agent.lib.agent_thread.reset_service import ResetService
from agent.lib.errors import Errors
from agent.lib.result import errorResult, doneResult
from agent.lib.result import statusResult
from paste.deploy.converters import asbool
from agent.lib.utils import trackable
from agent.lib import manifestutil, configutil
from agent.lib.agent_thread.startstop_service import StartStopService
from agent.lib.agent_thread.deactivate_manifest import DeactivateManifest
from agent.lib.security.agentauth import authorize
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.agent_thread.deploy_service import DeployService

LOG = logging.getLogger(__name__)

class ActionController(BaseController):
    """ Action Controller class.  Responsible for all actions of a service/agent """

    @authorize()
    @trackable()
    def deployservice(self, service):
        """ activate manifest, if already active then skip """
        LOG.info('deploy service for service(%s) with body: %s', service, request.body)
        try:
            appGlobal = config['pylons.app_globals']

            # parse the body
            if (request.body == ""):
                return errorResult(request, response, Errors.INVALID_REQUEST,
                                   'No body found in post command',
                                   controller = self)

            requestjson = json.loads(request.body)
            manifest = requestjson['manifest']
            packages = requestjson['package']
            skipProp = asbool(requestjson['skipProp']) if 'skipProp' in requestjson else configutil.getConfigAsBool('download_skip_prop')
            skipActivation = asbool(requestjson['skipActivation']) if 'skipActivation' in requestjson else False
            
            # activate manifest if not already activated
            if manifestutil.getActiveManifest(service) == manifest:
                return doneResult(request, response, controller=self)
            
            deployServiceThread = DeployService(appGlobal.threadMgr, service, manifest, packages, skipProp = skipProp, skipActivation = skipActivation)
            self.injectJobCtx(deployServiceThread)
            deployServiceThread.start()
            deployServiceThread.threadMgrEvent.wait()

            return statusResult(request, response, deployServiceThread, controller = self)

        except Exception as excep:
            msg = 'Unknown error for activateManifest(%s/%s) - %s - %s' % (service, manifest, str(excep), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = msg, controller = self)


    @authorize()
    @trackable()
    def activatemanifest(self, service):
        """ activate manifest, if already active then skip """
        LOG.info('activateManifest for service(%s) with body: %s', service, request.body)
        try:
            appGlobal = config['pylons.app_globals']
            manifest = ''
            requestjson = json.loads(request.body)
            manifest = requestjson['manifest']
            force = asbool(requestjson['force']) if 'force' in requestjson else False
            
            if not force and manifestutil.getActiveManifest(service) == manifest:
                return doneResult(request, response, controller=self)
            
            else:
                mf_path = os.path.join(ManifestController.manifestPath(service, manifest))
                if (not os.path.exists(mf_path)):
                    return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Manifest(%s, %s) path missing' % (service, manifest),
                                   controller = self)
                LOG.debug('Manifest path exists: %s' % (mf_path))
                activateThread = ActivateManifest(appGlobal.threadMgr, service, manifest)
                self.injectJobCtx(activateThread)
                activateThread.start()
                activateThread.threadMgrEvent.wait()

            return statusResult(request, response, activateThread, controller = self)

        except Exception as excep:
            msg = 'Unknown error for activateManifest(%s/%s) - %s - %s' % (service, manifest, str(excep), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = msg, controller = self)

    @authorize()
    @trackable()
    def restart(self, service):
        ''' Controller to restart service '''
        LOG.info('restart for service(%s)', service)

        try:
            appGlobal = config['pylons.app_globals']

            if not os.path.exists(ManifestController.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Active Manifest(%s) path missing' % (service),
                                   controller = self)
            restartThread = RestartService(appGlobal.threadMgr, service)
            self.injectJobCtx(restartThread)
            restartThread.start()
            restartThread.threadMgrEvent.wait()

            return statusResult(request, response, restartThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for restart service(%s) - %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def reset(self, service):
        ''' Controller to reset service '''
        LOG.info('reset for service(%s)', service)

        try:
            appGlobal = config['pylons.app_globals']

            if not os.path.exists(ManifestController.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Active Manifest(%s) path missing' % (service),
                                   controller = self)
            resetThread = ResetService(appGlobal.threadMgr, service)
            self.injectJobCtx(resetThread)
            resetThread.start()
            resetThread.threadMgrEvent.wait()

            return statusResult(request, response, resetThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for restart service(%s) - %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def startup(self, service):
        ''' Controller to startup service '''
        LOG.info('startup for service(%s)', service)

        try:
            appGlobal = config['pylons.app_globals']

            if not os.path.exists(manifestutil.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Active Manifest(%s) path missing' % (service),
                                   controller = self)
            startupThread = StartStopService(appGlobal.threadMgr, service, StartStopService.ACTION_STARTUP)
            self.injectJobCtx(startupThread)
            startupThread.start()
            startupThread.threadMgrEvent.wait()

            return statusResult(request, response, startupThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for start service(%s) - %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)


    @authorize()
    @trackable()
    def shutdown(self, service):
        ''' Controller to shutdown service '''
        LOG.info('shutdown for service(%s)', service)

        try:
            appGlobal = config['pylons.app_globals']

            if not os.path.exists(manifestutil.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Active Manifest(%s) path missing' % (service),
                                   controller = self)
            shutdownThread = StartStopService(appGlobal.threadMgr, service, StartStopService.ACTION_SHUTDOWN)
            self.injectJobCtx(shutdownThread)
            shutdownThread.start()
            shutdownThread.threadMgrEvent.wait()

            return statusResult(request, response, shutdownThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for shutdown service(%s) - %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def deactivatemanifest(self, service):
        """ deactivate a manifest """
        LOG.info('activateManifest for service(%s) with body: %s', service, request.body)
        try:
            appGlobal = config['pylons.app_globals']
            if not os.path.exists(manifestutil.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Deactivate Manifest(%s) path missing' % (service),
                                   controller = self)

            deactivateThread = DeactivateManifest(appGlobal.threadMgr, service)
            self.injectJobCtx(deactivateThread)
            deactivateThread.start()
            deactivateThread.threadMgrEvent.wait()

            return statusResult(request, response, deactivateThread, controller = self)

        except Exception as excep:
            msg = 'Unknown error for deactivateManifest(%s) - %s - %s' % (service, str(excep), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = msg, controller = self)


    @authorize()
    @trackable()
    def executeScript(self, service, scriptname):
        """ execute a script from remote location"""
        scriptpath = None

        try:
            # parse the body
            if (not request.body or request.body == ""):
                LOG.error('invalid body found in post command')
                return errorResult(request, response, Errors.INVALID_REQUEST, 'No body found in post command', controller = self)

            body = json.loads(request.body)
            paramobj = body['params'] if 'params' in body else []
            params = paramobj if type(paramobj) == list else paramobj.split()

            LOG.info('%s' % (params))

            scriptpath = None
            for package in manifestutil.packagesInManifest(service):
                scriptpathtmp = os.path.join(manifestutil.packagePath(service, 'active', package), 'cronus', 'scripts', scriptname)
                if os.path.exists(scriptpathtmp):
                    scriptpath = scriptpathtmp
                    break
            if not scriptpath:
                return errorResult(request, response, Errors.INVALID_REQUEST, 'script %s not found' % scriptname, controller = self)

            cmd = ['sudo', '-u', 'cronusapp', scriptpath]

            for param in params:
                param = param.encode('ascii', 'ignore')
                cmd.append(param)

            LOG.info('cmd = %s' % cmd)

            appGlobal = config['pylons.app_globals']
            execThread = ExecThread(appGlobal.threadMgr, cmd)
            execThread.setLogLevel('info')
            execThread.start()
            execThread.threadMgrEvent.wait()

            return statusResult(request, response, execThread, controller = self)

        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when executing cmd %s,  %s - %s' %
                               (scriptpath, str(excp), traceback.format_exc(2)),
                               controller = self)


    @trackable()
    def sendMetrics(self, service="agent", resSec="60", monitorgroup="default"):
        ''' send data to external monitoring system EVPS '''
        appGlobal = config['pylons.app_globals']
    
        if request.body:
            collectdTextResult = request.body
            outputMapArray = json.loads(collectdTextResult)
            appGlobal.agentMonitor.runExtMonitor(service, 'http', resSec, outputMapArray, monitorgroup)
        
        return
