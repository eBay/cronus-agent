#pylint: disable=E1101,W0105
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
import os
import platform
import subprocess

import logging
LOG = logging.getLogger(__name__)

class SystemMonitor():
    ''' monitor that gets system status '''
    def __init__(self):
        ''' constructor '''
        LOG.debug("creating %s" %(__name__))

    def getOSinfo(self):
        ''' get value os info '''
        return platform.uname()[0] + " " + platform.uname()[2] + " " + platform.uname()[3] + " " + platform.uname()[4]

    def getNodeName(self):
        ''' get node name '''
        return platform.uname()[1]

    def getPid(self):
        ''' get process pid'''
        return os.getpid()

    def getFreeMemory(self):
        ''' get free real memory in KB '''
        try:
            vmstat = subprocess.Popen("vmstat 1 2", shell = True, stdout=subprocess.PIPE)
            output = vmstat.communicate()[0].split('\n')
            fields = output[1].split()
            values = output[3].split()
            return int(values[fields.index('free')])
        except BaseException:
            return 0

    def getCpuUsage(self):
        ''' get cpu usage '''
        try:
            vmstat = subprocess.Popen("vmstat 1 2", shell = True, stdout=subprocess.PIPE)
            output = vmstat.communicate()[0].split('\n')
            fields = output[1].split()
            values = output[3].split()
            userTime = int(values[fields.index('us')])
            systemTime = int(values[fields.index('sy')])
            idleTime = int(values[fields.index('id')])
            return float(int(userTime) + int(systemTime)) / (int(userTime) + int(systemTime) + int(idleTime)) * 100
        except BaseException:
            return 0
