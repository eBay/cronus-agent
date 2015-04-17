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
auth module'''

from pylons import request, response
from agent.lib.result import errorResult
from agent.lib.errors import Errors

def invalidAuthHandler(message, result):
    ''' call back when unauthenticated user comes '''
    return errorResult(request, response, Errors.INVALID_AUTH, message, 401, result = result)

class UnauthorizedException(Exception):
    ''' exception thrown if it's a authenticated user'''
    def __init__(self, message):
        ''' constructor '''
        super(UnauthorizedException, self).__init__(message)
        self.message = message
