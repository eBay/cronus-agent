#pylint: disable=W0703, W0141, R0912, R0914, R0915, E1121, E1101, W0212, W0612,W0105
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
Agent health monitoring
Created on Dec 21, 2011

@author: biyu
'''

import logging
import os
import traceback
import pylons
import threading
import re
import platform
import socket


LOG = logging.getLogger(__name__)

AGENT_HEALTHY = 'True'
AGENT_UNHEALTHY = 'False'
AGENT_HEALTH_UNKNOWN = 'Unknown'

DISK_THRESHOLD_DEFAULT = 90
DISK_GC_THRESHOLD_DEFAULT = 70
FD_THRESHOLD_DEFAULT = 500
MEM_THRESHOLD_DEFAULT = 900000

KEY_STICKY_VERSION = 'sticky_version'

def loadVersion():
    """
    searches ./version.properties and  cronus/version.properties for version file
    @return version string in version.properties file
    """
    path = './'
    if os.path.isfile('%s/version.properties' % path):
        version_file = open('%s/version.properties' % path, 'r')
    elif os.path.isfile('%s/cronus/version.properties' % path):
        version_file = open('%s/cronus/version.properties' % path, 'r')
    else:
        return "unknown"

    versionDict = {}
    for line in version_file:
        # skip comments
        if re.search(r"^\s*#", line) or re.search(r"^\s*$", line):
            continue
        key, value = line.split('=')
        versionDict[key.strip()] = value.strip()

    for key in ['version.major', 'version.minor', 'version.build', 'version.buildnum.hudson']:
        if key not in versionDict:
            versionDict[key] = '-'

    return "%s.%s.%s" % (versionDict['version.major'], versionDict['version.minor'], versionDict['version.buildnum.hudson']
            if versionDict['version.buildnum.hudson'] != '-' else versionDict['version.build'])

def checkAgentVersion(isStartup = False):
    '''
    Check agent version against source of truth
    '''

    wiriVersion = loadVersion()

    appGlobal = pylons.config['pylons.app_globals']
    if wiriVersion:
        appGlobal.agentInfo['version_wiri'] = wiriVersion

def getOsInfo():
    '''
    Check os info
    '''
    distr = __get_distribution()
    ostype = __get_os_type()
    nodename = __get_node_name()
    fqdn = socket.getfqdn()
    osinfo = {'node_name': nodename,
              'fqdn': fqdn,
              'os_type': ostype,
              'os_distr': distr}
    return osinfo

def checkAgentHealth():
    '''
    Reports the agent health (as of now, based on disk utilization and file descriptors usage)
    as an attribute to be shown in ValidateInternals page.
    '''
    health = AGENT_HEALTH_UNKNOWN
    healthfactor = {}

    if(os.name == 'nt'):
        LOG.error('Agent monitoring not yet supported in win32 platforms')
    else:
        try:
            appGlobal = pylons.config['pylons.app_globals']
            monit_list = appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')]
            disk_usage_percent, fd_usage, mem_usage = __get_disk_fd_mem_usage(monit_list)
            disk_threshold, fd_threshold, mem_threshold = get_disk_and_fd_thresholds()

            healthfactor['disk-usage'] = '%s / %s' % (str(disk_usage_percent), str(disk_threshold))
            healthfactor['FD-usage'] = '%s / %s' % (str(fd_usage), str(fd_threshold))
            healthfactor['mem-usage(KB)'] = '%s / %s' % (str(mem_usage), str(mem_threshold))

            disk_ok = __is_usage_normal('Disk', disk_usage_percent, disk_threshold)
            fd_ok = __is_usage_normal('FD', fd_usage, fd_threshold)
            mem_ok = __is_usage_normal('Memory', mem_usage, mem_threshold)

            if disk_usage_percent < 0 or fd_usage < 0 or mem_usage < 0:
                health = AGENT_HEALTH_UNKNOWN
            else:
                health = AGENT_HEALTHY if (fd_ok and mem_ok) else AGENT_UNHEALTHY
                if ((not fd_ok or not mem_ok) and not appGlobal.threadMgr.hasActive() and appGlobal.autoRestartEnabled):
                    # restart when there is no active job
                    sdthread = threading.Thread(target = appGlobal.sdutil)
                    sdthread.start()

                if appGlobal.diskOk != disk_ok:
                    appGlobal.diskOk = disk_ok

        except KeyError:
            # we don't have monitor script run yet, skip
            pass
        except Exception as excep:
            health = AGENT_HEALTH_UNKNOWN
            LOG.error('Cannot report agent health (%s) - %s' % (excep, traceback.format_exc(3)))

    return (health, healthfactor)

def get_disk_and_fd_thresholds():
    '''
    @return: disk and fd and mem usage thresholds as obtained from *.ini; if invalid resets to a good known default
    '''
    disk_threshold = int(pylons.config['health_disk_usage_percent_threshold'])
    if(disk_threshold < 0 or disk_threshold > 100):
        LOG.warning('Disk usage threshold (%s) set at config seemed to be invalid. Resetting it to %s' % (disk_threshold, DISK_THRESHOLD_DEFAULT))
        disk_threshold = DISK_THRESHOLD_DEFAULT
    fd_threshold = int(pylons.config['health_agent_file_descriptor_usage_threshold'])
    if(fd_threshold < 0):
        LOG.warning('FD usage threshold (%s) set at config seemed to be invalid. Resetting it to %s' % (fd_threshold, FD_THRESHOLD_DEFAULT))
        fd_threshold = FD_THRESHOLD_DEFAULT
    mem_threshold = int(pylons.config['health_agent_mem_usage_threshold'])
    if(mem_threshold < 0):
        LOG.warning('Memory usage threshold (%s) set at config seemed to be invalid. Resetting it to %s' % (mem_threshold, MEM_THRESHOLD_DEFAULT))
        mem_threshold = MEM_THRESHOLD_DEFAULT
    return disk_threshold, fd_threshold, mem_threshold

def __get_disk_fd_mem_usage(monit_list):
    '''
    @return: metrics (disk_usage_percentage, fd_usage, mem_usage(KB)) as numeric;
    If not available/err, throws exception with meaningful message
    '''
    fd_usage = None
    mem_usage = None
    packageMount = pylons.config['agent_root']
    total_disk, used_disk = getDiskUsage(packageMount)

    for (key, value) in monit_list.items():
        if(len(value) == 3): # of expected format [value, timestamp, preTimestamp]
            if (key == 'agentUsedFD'):
                fd_usage = value[0]
            if (key == 'agentUsedMem'):
                mem_usage = value[0]
            if fd_usage is not None and mem_usage is not None:
                break # ok, we collected all we needed

    disk_usage_percent = getDiskUsagePercent(total_disk, used_disk)
    fd_usage = __convert_usage(fd_usage)
    mem_usage = __convert_usage(mem_usage)

    return disk_usage_percent, fd_usage, mem_usage

def getDiskUsage(path):
    ''' returns the used disk and available disk values'''
    fstat = os.statvfs(path)
    total = (fstat.f_blocks * fstat.f_frsize)
    used = (fstat.f_blocks - fstat.f_bfree) * fstat.f_frsize
    return total, used

def __convert_usage(usage):
    '''
    @return: FD usage parsed as integer; if unable to, return -1
    '''
    try:
        return int(usage)
    except (TypeError, ValueError):
        return -1

def needAggressiveGC(path):
    ''' when to start aggressive GC '''
    isDiskUsageNormal = False
    gc_threshold = int(pylons.config['health_disk_usage_gc_threshold'])
    if(gc_threshold < 0 or gc_threshold > 100):
        LOG.warning('Disk usage gc threshold (%s) set at config seemed to be invalid. Resetting it to %s' % (gc_threshold, DISK_GC_THRESHOLD_DEFAULT))
        gc_threshold = DISK_GC_THRESHOLD_DEFAULT
    if os.name == 'posix':
        total_disk, used_disk = getDiskUsage(path)
        usage_percent = getDiskUsagePercent(total_disk, used_disk)
        isDiskUsageNormal = __is_usage_normal('Disk', usage_percent, gc_threshold)
    else:
        isDiskUsageNormal = True    #advanced GC is disabled for windows
    return not isDiskUsageNormal

def canStopAggressiveGC(path):
    ''' when to stop aggressive GC '''
    isDiskUsageNormal = False
    gc_threshold = int(pylons.config['health_disk_usage_gc_threshold'])
    gc_buffer = int(pylons.config['health_disk_usage_gc_buffer'])
    gc_lowerbound = gc_threshold - gc_buffer
    if(gc_lowerbound < 0 or gc_lowerbound > 100 or gc_lowerbound > gc_threshold):
        LOG.warning('Disk usage gc lower threshold (%s) set at config seemed to be invalid. Resetting it to %s' % (gc_lowerbound, gc_threshold))
        gc_lowerbound = gc_threshold
    if os.name == 'posix':
        total_disk, used_disk = getDiskUsage(path)
        usage_percent = getDiskUsagePercent(total_disk, used_disk)
        isDiskUsageNormal = __is_usage_normal('Disk', usage_percent, gc_lowerbound)
    else:
        isDiskUsageNormal = True    #advanced GC is disabled for windows
    return isDiskUsageNormal


def __is_usage_normal(usage_name, usage, threshold):
    '''
    @return: True if usage falls below threshold; else False;
    '''
    is_normal = True
    if usage > threshold:
        LOG.warning('Agent unhealthy; %s used by agent (%s) exceeded threshold(%s)' % (usage_name, usage, threshold))
        is_normal = False
    LOG.debug('Agent healthiness - FD: agent %s usage %s, threshold %s, normal %s' % (usage_name, usage, threshold, is_normal))
    return is_normal

def getDiskUsagePercent(total_disk, used_disk):
    '''
    @return: disk usage as percentage;
    Throws exception if given disk usage metric is None/invalid
    '''
    try:
        actual = (float(used_disk) / float(total_disk)) * 100
        rounded = round(actual, 2)
        return rounded
    except (TypeError, ValueError):
        raise Exception('Disk utilization couldn\'t be calculated as some required metrics are not properly captured'
                        '(i.e. either unavailable or not seem to be arithmetic) (Total disk %s, Used disk %s)' % (total_disk, used_disk))

def __get_up_time():
    ''' system up time, idletime in second'''
    uptime = idletime = -1
    if os.name != 'nt' and os.path.exists("/proc/uptime"):
        uptime, idletime = [float(f) for f in open("/proc/uptime").read().split()]
    return (uptime, idletime)

def __get_distribution():
    ''' get os distribution '''
    distr = None
    if os.name == 'nt':
        distr = 'win'
    elif platform.uname()[0] == 'Linux':
        from agent.lib import utils
        ldistr = utils.get_linux_distro()
        distr = ldistr[0] + ldistr[1]
    elif platform.uname()[0] == 'Solaris':
        distr = 'Solaris'
    else:
        distr = 'Ubuntu10.10'
    return distr

def __get_os_type():
    ''' get value os info '''
    return platform.uname()[0] + " " + platform.uname()[2] + " " + platform.uname()[3] + " " + platform.uname()[4]


def __get_node_name():
    ''' get node name '''
    return platform.uname()[1]
