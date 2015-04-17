# pylint: disable=R0914,R0912,R0904,C0103,W0105
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
Creatted on Nov 16, 2010

@author: ppa
'''
from agent.lib.base import BaseController
from pylons import config, response, tmpl_context as c
from pylons.templating import render_mako as render
import httplib
import json
import logging
import os
from agent.lib.filehelper import plaintext2html

LOG = logging.getLogger(__name__)


def getConfigFile():
    """ get config """
    return config['app_conf']

class ValidateInternalsController(BaseController):
    """ ValidateInternal Controller Class """
    def __init__(self):
        """ constructor  """
        super(ValidateInternalsController, self).__init__()
        
    @staticmethod
    def sendHttpRequest( httpRequest ):
        """ get http content """
        connection = None
        
        #host, port, protocol, url, httpMethod 
        if (httpRequest == None):
            print "NullPointer of httpRequest is null"
        status, error, errorMessage, httpResponse, httpResponseMessage = None, None, None, None, None
        
        try:
            #print "Now send HTTP request with URL: " + httpRequest.url
            if 'https' == httpRequest.protocol:
                connection = httplib.HTTPSConnection(httpRequest.host, httpRequest.port)
            else:
                connection = httplib.HTTPConnection(httpRequest.host, httpRequest.port)
            
            if httpRequest.headers is None:
                connection.request(httpRequest.httpMethod, httpRequest.urlPostfix)
            else:
                connection.request(httpRequest.httpMethod, httpRequest.urlPostfix, httpRequest.body, httpRequest.headers)
            httpResponse = connection.getresponse()
            status = httpResponse.status
            if status >= 200 and status < 300:
                httpResponseMessage = httpResponse.read()
            else:
                errorMessage = httpResponse.reason
        except IOError, exception:
            errorMessage = 'Error during sendHttpRequest - %s' % (str(exception))
        finally:
            if connection is not None:
                connection.close()
                
        return status, httpResponseMessage, error, errorMessage
    
    def getInfo(self, isHtml):
        """ generate info """
        appGlobal = config['pylons.app_globals']
        if 'True' == isHtml:
            c.status = appGlobal.metrixManager.getStatus()
            menuTab = "MENU_TAB_VI"
            c.menuTab = menuTab
            for vkey, vval in c.status:
                if not vval:
                    continue
                elif vkey == 'OSInfo':
                    c.fqdn = vval["fqdn"] 
                
            return render('/derived/validateInternals.html')
        else:
            response.content_type = 'application/json'
            return appGlobal.metrixManager.getJsonStatus()
    
    

    def getInfo2(self, isHtml):
        """ generate validate internal info for VI facelift """
        appGlobal = config['pylons.app_globals']
        response.content_type = 'application/json'
        viInfo = appGlobal.metrixManager.getStatus()
        viInfo2 = {}
        hostInfo = []
        healthInfo = []
        configInfo = []
        osInfo = []
        agentInfo = []
        configOR = []
        viInfo2['Host Information'] = hostInfo
        viInfo2['Health Information'] = healthInfo
        viInfo2['OS Information'] = osInfo
        viInfo2['Agent Information'] = agentInfo
        viInfo2['Configuration Information'] = configInfo
        viInfo2['Configuration Overrides'] = configOR
        for vkey, vval in viInfo:
            if not vval:
                continue
            if vkey == 'HealthFactor':
                hvals = json.loads(vval) 
                for ckey, cval in hvals.iteritems():
                    healthInfo.append({'display-name':'', 'name':ckey, 'value':cval})
            elif vkey == 'OSInfo':
                for ckey, cval in vval.iteritems():
                    osInfo.append({'display-name':'', 'name':ckey, 'value':cval})
            elif vkey == 'AgentInfo':
                for ckey, cval in vval.iteritems():
                    agentInfo.append({'display-name':'', 'name':ckey, 'value':cval})
            elif vkey == 'Configuration':
                for ckey, cval in vval.iteritems():
                    configInfo.append({'display-name':'', 'name':ckey, 'value':cval})
            elif vkey == 'Configuration Overrides':
                for ckey, cval in vval.iteritems():
                    configOR.append({'display-name':'', 'name':ckey, 'value':cval})
            else:
                hostInfo.append({'display-name':'', 'name':vkey, 'value': vval})
        return json.dumps(viInfo2)

    def getLogDirectory(self):
        """ show log directory """
        logList = os.listdir('logs')
        for fileName in logList:
            if not fileName.endswith('.log'):
                logList.remove(fileName)
        c.content = logList
        
        menuTab = "MENU_TAB_LOGS"
        c.menuTab = menuTab        
        return render('/derived/logDirectory.html')

    def getLogDirectory2(self):
        """ get log directories for VI facelift """
        logInfo = {}
        logs = []
        logList = os.listdir('logs')
        for fileName in logList:
            if fileName.endswith('.log'):
                logs.append({'file-name':fileName, 'file-url':'/agent/logs/%s' % fileName})
        logInfo['Log Files'] = logs
        response.content_type = 'application/json'
        return json.dumps(logInfo)

    def getLogFile(self, fileName):
        """ show log file """
        logFile = open('logs/' + fileName, 'r')
        logData = logFile.read()
        logFile.close()
        return plaintext2html(logData)

    def getAgentHealth(self):
        """ generate agent health REST response """
        appGlobal = config['pylons.app_globals']
        status = appGlobal.metrixManager.getStatus()
        result = []
        for key, value in status:
            if 'Health' == key:
                result.append({'key': 'health', 'value': value})
            elif 'HealthFactor' == key and type(value) is dict:
                subres = []
                for key1, value1 in value.items():
                    subres.append('%s=%s' % (key1, value1))
                result.append({'key': 'healthFactor', 'value': ','.join(subres)})                    

        response.content_type = 'application/json'
        return json.dumps(result)

    def getMonitors(self):
        """ show all monitor values available """
        appGlobal = config['pylons.app_globals']
        response.content_type = 'application/json'
        result = appGlobal.agentMonitor.dumpMonitorValues() if appGlobal is not None else {}
        return json.dumps(result)


    def getThreads(self):
        """ show all threads """
        appGlobal = config['pylons.app_globals']
        response.content_type = 'application/json'
        result = appGlobal.threadMgr.getInfo() if appGlobal is not None else {}
        return json.dumps(result)

    
