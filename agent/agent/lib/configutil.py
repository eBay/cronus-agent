#pylint: disable=W0703,W0621,C0103,W0105
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
Created on Mar 21, 2014

@author: biyu
'''

from agent.lib import manifestutil
import logging
from beaker.converters import asbool
import pylons
import copy
import json

CONFIG = {}
CONFIGOR = {}

LOG = logging.getLogger(__name__)

def loadPylonConfig(pylonconfigs):
    """ load pylon config with overrides """
    CONFIG.update(pylonconfigs)
    
def loadConfigOverrides():
    """ load config override from .metadata """
    try:
        configsMeta = manifestutil.readJsonServiceMeta('agent', ['configs'])
        CONFIGOR.clear()
        if 'configs' in configsMeta:
            CONFIGOR.update(configsMeta['configs'])

        # apply to pylon configs
        pylons_config = pylons.config.current_conf()
        if pylons_config and CONFIGOR:
            pylons_config.update(copy.deepcopy(CONFIGOR))
            pylons.config.pop_process_config()
            pylons.config.push_process_config(pylons_config)

    except BaseException as exc:
        LOG.error(str(exc))
    
def getConfig(key):
    """ getting pylon config with overrides """
    return CONFIGOR[key] if key in CONFIGOR else (CONFIG[key] if key in CONFIG else None)
    
def getConfigAsBool(key):
    """ get config as bool """
    value = getConfig(key)
    return asbool(value) if value else False

def getConfigAsInt(key):
    """ get config as int """
    value = getConfig(key)
    return int(value) if value else 0

def getConfigAsJson(key):
    """ get config as json """
    value = getConfig(key)
    return json.loads(value) if value else None
    
def getConfigOverrides():
    """
    load configuration overrides from agent .metadata.json
    """
    configsOR = {}
    try:
        configsMeta = manifestutil.readJsonServiceMeta('agent', ['configs'])
        configsOR = configsMeta['configs'] if 'configs' in configsMeta else {}
    except Exception as exc:
        LOG.error(str(exc))
        
    return configsOR 
