#pylint: disable=W0105
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
"""Setup the agent application"""
import logging

import pylons.test

from agent.config.environment import load_environment

LOG = logging.getLogger(__name__)

def setup_app(command, conf, my_vars):
    """Place any commands to setup agent here"""
    # Don't reload the app if it was loaded under the testing environment
    if not pylons.test.pylonsapp:
        load_environment(conf.global_conf, conf.local_conf)

    LOG.debug('setup app with command:' + str(command))
    LOG.debug('setup app with vars:' + str(my_vars))
