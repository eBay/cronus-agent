#pylint: disable=W0703, R0912,W0105
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
"""The base Controller API

Provides the BaseController class for subclassing.
"""

from pylons.controllers import WSGIController

import logging
from pylons import request
from agent.lib import contextutils, manifestutil

LOG = logging.getLogger(__name__)
CTXNAMES = ['guid', 'service', 'thread_timeout', 'thread_progress_timeout']

class BaseController(WSGIController):
    """ base controller class """

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']

        # before setting anything new, first reset the old values from previous request if any
        contextutils.resetcontext(self)

        #LOG.debug(environ)
        if 'service' in environ['pylons.routes_dict']:
            servicename = environ['pylons.routes_dict']['service']
            #if not registered, agent will not try to replace

            if servicename is not None and servicename.count('.') == 2:
                servicename = manifestutil.expandServiceName(servicename)
                LOG.info('service name expanded %s ' % servicename)
                environ['pylons.routes_dict']['service'] = servicename
            
            contextutils.injectcontext(self, {'service': servicename})

            
        # get correlationid into context
        if 'X-CORRELATIONID' in request.headers and request.headers['X-CORRELATIONID'] is not None:
            contextutils.injectcontext(self, {'guid': request.headers['X-CORRELATIONID']})
        else:
            contextutils.injectcontext(self, {'guid': ''})

        # get timeouts and inject into context
        if 'X-THREAD_TIMEOUT' in request.headers and request.headers['X-THREAD_TIMEOUT'] is not None:
            contextutils.injectcontext(self, {'thread_timeout': request.headers['X-AGENT_THREAD_TIMEOUT']})

        # get progress timeouts and inject into context
        if 'X-THREAD_PROGRESS_TIMEOUT' in request.headers and request.headers['X-THREAD_PROGRESS_TIMEOUT'] is not None:
            contextutils.injectcontext(self, {'thread_progress_timeout': request.headers['X-THREAD_PROGRESS_TIMEOUT']})

        # get remote address from request
        remoteAddr = request.environ.get("X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR"))
        contextutils.injectcontext(self, {'remote_addr': remoteAddr})

        reqChecksum = '%s,%s,%s' % (request.method, request.url, request.body)
        contextutils.injectcontext(self, {'reqChecksum': reqChecksum})

        return WSGIController.__call__(self, environ, start_response)


    def injectJobCtx(self, target):
        ''' inject both guid and callback into an object
            @param target: target
        '''
        contextutils.copycontexts(self, target, CTXNAMES)

