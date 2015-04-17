#pylint: disable=E1121,W0105
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
Created on Apr 30, 2014

@author: biyu
'''
from pylons import request
from agent.lib.security import agentauth

import logging
from agent.lib.base import BaseController

LOG = logging.getLogger(__name__)

class ModuleBaseController(BaseController):
    """ base controller class for pluggable module controller
        force authn & authz for any non GET call
    """

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        if request.method != 'GET':
            return agentauth.authorize(BaseController.__call__, self, environ, start_response)
        else:
            return BaseController.__call__(self, environ, start_response)

    @property
    def logger(self):
        """ logger property """
        return LOG

