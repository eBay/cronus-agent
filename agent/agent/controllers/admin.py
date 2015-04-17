#pylint: disable=W0703,W0105
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
""" Admin Controller """
from agent.lib import manifestutil
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.base import BaseController
from agent.lib.errors import Errors
from agent.lib.result import errorResult, statusResult, doneResult
from agent.lib.security.agentauth import authorize
from agent.lib.utils import rchmod, trackable
from paste.deploy.converters import asbool
from pylons import request, response, config
import json
import logging
import os
import pylons
import traceback

LOG = logging.getLogger(__name__)

class AdminController(BaseController):
    """ admin controller """

    def __init__(self):
        """ constructor """
        BaseController.__init__(self)
        self.__timeout = float(pylons.config['exec_thread_timeout'])
        self.__progressTimeout = float(pylons.config['exec_thread_progress_timeout'])

    @authorize()
    @trackable()
    def validateToken(self):
        """ validate token """
        return doneResult(request, response, result = "success", controller = self)

    @authorize()
    @trackable()
    def executeCmd(self):
        """ execute a command synchronously """
        try:
            # parse the body
            if (not request.body or request.body == ""):
                LOG.error('invalid body found in post command')
                return errorResult(request, response, 10001, 'No body found', controller = self)

            body = json.loads(request.body)
            cmd0 = body['cmd'] if 'cmd' in body else None
            needsudo = asbool(body['need-sudo']) if 'need-sudo' in body else False
            sudotgt = body['sudo-target'] if 'sudo-target' in body else None
            paramobj = body['params'] if 'params' in body else []
            params = paramobj if type(paramobj) == list else paramobj.split()
            LOG.info('%s %s %s %s' % (cmd0, needsudo, sudotgt, params))

            if cmd0 is None or cmd0 == '':
                return errorResult(request, response, 10002, 'No command found', controller = self)

            cmd = [cmd0.encode('ascii', 'ignore')]
            if needsudo:
                cmd.insert(0, 'sudo')
                if sudotgt is not None:
                    sudotgt = sudotgt.encode('ascii', 'ignore')
                    cmd.insert(1, sudotgt)
                    cmd.insert(1, '-u')

            for param in params:
                param = param.encode('ascii', 'ignore')
                cmd.append(param)

            appGlobal = config['pylons.app_globals']
            execThread = ExecThread(appGlobal.threadMgr, cmd)
            execThread.setLogLevel('info')
            execThread.start()

            return statusResult(request, response, execThread, controller = self)

        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when executing cmd %s,  %s - %s' %
                               (cmd, str(excp), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def executeScript(self):
        """ execute a script from remote location"""
        scriptpath = None

        try:
            # parse the body
            if (not request.body or request.body == ""):
                LOG.error('invalid body found in post command')
                return errorResult(request, response, 10001, 'No body found in post command', controller = self)

            body = json.loads(request.body)
            scriptloc = body['script-location'].encode('ascii', 'ignore') if 'script-location' in body else None
            scriptname = body['script-name'].encode('ascii', 'ignore') if 'script-name' in body else None
            needsudo = asbool(body['need-sudo']) if 'need-sudo' in body else False
            sudotgt = body['sudo-target'].encode('ascii', 'ignore') if 'sudo-target' in body else None
            paramobj = body['params'] if 'params' in body else []
            params = paramobj if type(paramobj) == list else paramobj.split()

            LOG.info('%s %s %s %s %s' % (scriptloc, scriptname, needsudo, sudotgt, params))

            if scriptloc is None or scriptloc == '':
                return errorResult(request, response, 10003, 'Script location not found', controller = self)
            if scriptname is None or scriptname == '':
                return errorResult(request, response, 10003, 'Script name not found', controller = self)

            scriptpath = os.path.join(self.dataPath(), scriptname)
            LOG.info('scriptpath = %s' % scriptpath)

            os.system('wget %s -O %s' % (scriptloc, scriptpath))

            if scriptpath is None or not os.path.exists(scriptpath):
                return errorResult(request, response, 10003, 'Failed to get script %s' % scriptpath, controller = self)

            rchmod(scriptpath, '+rx')

            cmd = [scriptpath]
            if needsudo:
                cmd.insert(0, 'sudo')
                if sudotgt is not None:
                    cmd.insert(1, sudotgt)
                    cmd.insert(1, '-u')

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

    def dataPath(self):
        """ compute the path to the packages """
        datapath = os.path.realpath(os.path.join(manifestutil.servicePath('agent'), '.data'))
        if not os.path.exists(datapath):
            os.system('mkdir %s' % datapath)
        return datapath
