#pylint: disable=R0915, W0603, R0914, E1101, W0703, R0912,W0105
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

This package starts and stop the global objects in the agent
It is assumed that the pylons configuration object is fully created
"""

import pylons
from agent.lib.agent_thread.threadmgr import ThreadMgr
from agent.lib.packagemgr import PackageMgr

import logging
import os
from agent.lib import manifestutil, agenthealth, configutil
import threading
import signal
from paste.deploy.converters import asbool
import uuid
from agent.lib.security import agentauth
from agent.controllers import validate_internals
from agent.controllers.module import ModuleController


LOG = logging.getLogger(__name__)

AGENT_HEALTH_VI_KEY = 'Health'
AGENT_HEALTH_FACTOR_VI_KEY = 'HealthFactor'
AGENT_INFO_KEY = 'AgentInfo'
OS_INFO_KEY = 'OSInfo'

def startAgentGlobals(startThreadMgr = True, startPackageMgr = True, startAgentMonitor = True):
    """
    Create and start the global objects
    """
    # cleanup incomplete manifests
    from agent.controllers.service import ServiceController
    ServiceController.cleanupServices()

    # stop the existing agents
    stopAgentGlobals()
    
    appGlobal = pylons.config['pylons.app_globals']

    # load config override from agent .metadata.json
    configutil.loadPylonConfig(pylons.config)
    configutil.loadConfigOverrides()
    LOG.info("Complete loading config overrides")

    # build in memory security token cache
    appGlobal.authztoken = str(uuid.uuid4())
    appGlobal.encryptedtokens = {}
    agentauth.buildTokenCache(appGlobal.authztoken)
    LOG.info("Complete building security token cache")

    # agent health
    appGlobal.agentHealth = 'True'
    appGlobal.agentHealthFactor = None
    from datetime import datetime
    appGlobal.agentInfo = {'version_wiri': agenthealth.loadVersion(),
                           'startup_time': str(datetime.now())}

    appGlobal.osInfo = agenthealth.getOsInfo()
    appGlobal.diskOk = True
    appGlobal.autoRestartEnabled = asbool(pylons.config['auto_restart_enabled'])
    LOG.info("Agent health initialized")

    # start thread mgr
    appGlobal.threadMgr = ThreadMgr(garbageFreq = pylons.config['threadMgr_garbage_freq'],
                                    maxThreadAge = pylons.config['threadMgr_thread_age'])
    if startThreadMgr:
        appGlobal.threadMgr.start()
    LOG.info("Agent thread manager started")

    # start package mgr
    appGlobal.packageMgr = PackageMgr(garbageFreq = pylons.config['packageMgr_garbage_freq'],
                                      maxPackageAge = pylons.config['packageMgr_package_age'])
    if startPackageMgr:
        appGlobal.packageMgr.start()
    LOG.info("Agent package manager started")

    # now load saved .metadata for previously saved hwPath, serverAddress, and serverAuth
    enrollMeta = manifestutil.readJsonServiceMeta('agent', ['hwPath'])
    hwPath = enrollMeta.get('hwPath')
    if hwPath is not None:
        appGlobal.hwPath = hwPath
    LOG.info("Agent hwPath loaded")

    #start monitor manager
    from agent.lib.monitors.monitor import AgentMonitor
    appGlobal.agentMonitor = AgentMonitor()
    if startAgentMonitor:
        appGlobal.agentMonitor.start()
    LOG.info("Agent monitor started")
    
    # start graphite udp server
#     from agent.lib.monitors.graphited import GraphiteDServer
#     from multiprocessing import Pipe
#     graphiteEnabled = configutil.getConfigAsBool('graphite_enabled')
#     if startAgentMonitor and graphiteEnabled:
#         output_p, input_p = Pipe()
#         appGlobal.graphited = GraphiteDServer(input_p)
#         appGlobal.graphited.start()
#         udpMsgProcessThread = threading.Thread(target=GraphiteDServer.read_queue, args=(output_p,))
#         udpMsgProcessThread.daemon = True
#         udpMsgProcessThread.start()
#         LOG.info("Agent graphited started")


    # Declare dictionary for storing dynamic controllers
    appGlobal.dynacontrollers = dict()

    # metrix manager initialization
    from agent.lib.monitors.metrix_manager import MetrixManager
    from agent.lib.monitors.system_monitor import SystemMonitor
    appGlobal.metrixManager = MetrixManager()
    appGlobal.systemMonitor = SystemMonitor()
    appGlobal.metrixManager.register('OS', appGlobal.systemMonitor.getOSinfo, 1)
    appGlobal.metrixManager.register('Node Name', appGlobal.systemMonitor.getNodeName, 1)
    appGlobal.metrixManager.register('Free Memory(KB)', appGlobal.systemMonitor.getFreeMemory, 2)
    appGlobal.metrixManager.register('CPU Usage(%)', appGlobal.systemMonitor.getCpuUsage, 2)

    appGlobal.metrixManager.register('Version', agenthealth.loadVersion, 5)
    appGlobal.metrixManager.register('Configuration', validate_internals.getConfigFile, 6)
    appGlobal.metrixManager.register('Configuration Overrides', configutil.getConfigOverrides, 7)
    appGlobal.metrixManager.register('hwPath', lambda : appGlobal.hwPath if hasattr(appGlobal, 'hwPath') else None, 5)
    appGlobal.metrixManager.register(AGENT_HEALTH_VI_KEY, lambda : appGlobal.agentHealth, 1)
    appGlobal.metrixManager.register(AGENT_HEALTH_FACTOR_VI_KEY, lambda : appGlobal.agentHealthFactor, 1)
    appGlobal.metrixManager.register(OS_INFO_KEY, lambda : appGlobal.osInfo, 2)
    appGlobal.metrixManager.register(AGENT_INFO_KEY, lambda : appGlobal.agentInfo, 2)
    LOG.info("Agent health metrics registered")
    
    # start all agent modules
    modulestartthread = threading.Thread(target = ModuleController.loadModuleOnAgentStartup)
    modulestartthread.start()
    LOG.info("Local modules started")

    # start all services with active manifest, and load dynamic controllers
    servicestartthread = threading.Thread(target = ServiceController.startServicesOnAgentStartup)
    servicestartthread.start()
    LOG.info("Local services started")

    appGlobal.sdutil = shutdownAgent

def stopAgentGlobals():
    """
    stop the global objects
    """
    appGlobal = pylons.config['pylons.app_globals']

    if (hasattr(appGlobal, 'threadMgr') and appGlobal.threadMgr != None):
        appGlobal.threadMgr.stop()
    if (hasattr(appGlobal, 'packageMgr') and appGlobal.packageMgr != None):
        appGlobal.packageMgr.stop()
    if (hasattr(appGlobal, 'agentMonitor') and appGlobal.agentMonitor != None):
        appGlobal.agentMonitor.stop()
    if (hasattr(appGlobal, 'seederMgr') and appGlobal.seederMgr != None):
        appGlobal.seederMgr.stop()
    if (hasattr(appGlobal, 'graphited') and appGlobal.graphited != None):
        appGlobal.graphited.stop()

def shutdownAgent():
    ''' shutdown agent '''
    stopAgentGlobals()
    pid = os.getpid()
    if (hasattr(signal, 'SIGKILL')):
        os.kill(pid, signal.SIGKILL)
    else:
        os.kill(pid, signal.SIGTERM)

def dummy():
    """ return a dummy value for unsupported function """
    return 0
