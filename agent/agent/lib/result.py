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
"""This object helps create the result output"""

import logging
import json
from pylons import url
from agent.lib import contextutils

LOG = logging.getLogger(__name__)

NORMAL = '0'
WARNING = '1'
CRITICAL = '2'
DEBUG = '99'

def doneResult(request, response, httpStatus=200, result = None, controller = None):
    """ return a done result """

    response.status_int = httpStatus
    response.content_type = 'application/json'
    res = {}
    res['progress'] = 100
    res['status'] = url(controller='status', action='done')
    if (result != None):
        res['result'] = result

    __injectcontext(controller, __getreqstr(request), NORMAL, result)

    return json.dumps(res)

def statusResult(request, response, thread, controller = None, maxProgress = 100):
    """ set and return the status result """

    threadStatus = thread.getStatus()
    response.status_int = threadStatus['httpStatus']
    response.content_type = 'application/json'

    res = getThreadStatus(thread, maxProgress)
    
    # check if the result is an error not not
    if (threadStatus['error'] == None):
        status = NORMAL
        msg = 'progress %s' % str(threadStatus['progress'])
    else:
        status = CRITICAL
        msg = threadStatus['errorMsg']

    __injectcontext(controller, __getreqstr(request), status, msg)

    return json.dumps(res)

def errorResult(request, response, error, errorMsg, httpStatus = 500, result = None, controller = None):
    """ set and return the error result
        @param controller: pylon controller handling the request, where cal context is injected and later retrieved by trackable
    """

    response.status_int = httpStatus
    response.content_type = 'application/json'

    res = {'error':error, 'errorMsg':errorMsg}
    if (result != None):
        res['result'] = result

    title = __getreqstr(request)
    msg = 'Error Result - (%s, %s)' % (str(error), errorMsg)
    __injectcontext(controller, title, CRITICAL, msg)
    LOG.warning(msg)

    return json.dumps(res)

def __getreqstr(request):
    ''' get request string '''
    reqstr = []
    try:
        if request is not None:
            reqstr.append(request.url)
            reqstr.append(request.method)
            if request.body:
                reqstr.append(request.body)
    except BaseException:
        pass
    return ' '.join(reqstr) if reqstr else None

def __injectcontext(target, reqstr, status, msg = None):
    ''' inject additional status and message
        @param target: target to inject context
        @param status: status
        @param msg: message
    '''
    if target is not None:
        if reqstr is not None:
            contextutils.injectcontext(target, {'caltitle':reqstr})
        if status is not None:
            contextutils.injectcontext(target, {'calstatus':status})
        if msg is not None:
            contextutils.injectcontext(target, {'calbody':msg})

def getThreadStatus(thread, maxProgress = 100):
    ''' construct thread status json '''
    
    threadStatus = thread.getStatus()
    res = {}

    res['status'] = '/status/%s' % thread.getUuid()
    if (threadStatus['executionMsec'] != None):
        res['executionMsec'] = threadStatus['executionMsec']
        
    if (threadStatus['result'] != None):
        res['result'] = threadStatus['result']

    # check if the result is an error not not
    if (threadStatus['error'] == None):
        res['progress'] = threadStatus['progress']
        if int(res['progress']) > maxProgress:
            res['progress'] = maxProgress
    else:
        res['errorMsg'] = threadStatus['errorMsg']
        res['error'] = threadStatus['error']
        
    return res