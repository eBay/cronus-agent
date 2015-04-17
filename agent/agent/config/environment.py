#pylint: disable=W0212,W0105
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
"""Pylons environment configuration"""

import os

from mako.lookup import TemplateLookup
from pylons.configuration import PylonsConfig
from pylons.error import handle_mako_error

import agent.lib.app_globals as app_globals
from agent.config.routing import make_map
from agent.lib.agent_globals import startAgentGlobals

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object
    """
    config = PylonsConfig()

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='agent', paths=paths)

    config['routes.map'] = make_map(config)
    config['pylons.app_globals'] = app_globals.Globals(config)

    # Setup cache object as early as possible
    import pylons
    pylons.cache._push_object(config['pylons.app_globals'].cache)

    # Create the Mako TemplateLookup, with the default auto-escaping
    config['pylons.app_globals'].mako_lookup = TemplateLookup(
        directories=paths['templates'],
        error_handler=handle_mako_error,
        module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
        input_encoding='utf-8', default_filters=['escape'],
        imports=['from webhelpers.html import escape'])

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)
    pylons.config.update(config)

    # create the base directory for the agent
    path = os.path.join(config['agent_root'], 'service_nodes')
    if not os.path.exists(path):
        os.makedirs(path)

    path = os.path.join(config['agent_root'], 'packages')
    if not os.path.exists(path):
        os.makedirs(path)

    # create directories for distribution client
    # If repo_root is not specified, assume it is same as agent_root
    if config['repo_root'] is None or config['repo_root'] == '':
        config['repo_root'] = config['agent_root']
    path = config['repo_root']
    if not os.path.exists(path):
        os.makedirs(path)

    # start the agent globals
    startAgentGlobals()

    return config
