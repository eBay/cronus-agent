#pylint: disable=W0511,C0103,W0621,E1101,W0212,W0703,R0912,R0914,R0915,R0911,W0105
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
""" Utility Functions """

from agent.lib import contextutils
from agent.lib.errors import Errors, FileNotFoundError, AgentException
from decorator import decorator
from hashlib import md5
from subprocess import Popen, PIPE
import binascii
import errno
import json
import logging
import os
import pylons
import re
import shutil
import socket
import stat
import sys
import tarfile
import time
import traceback

LOG = logging.getLogger(__name__)
APILOG = logging.getLogger('agentapi')

def getHostIP():
    """ utility function to get current host's IP addr """
    ipaddr = None
    ipRe = re.compile('([0-9]+).([0-9]+).([0-9]+).([0-9]+)')
    ipaddr_rec_list = socket.getaddrinfo(socket.gethostname(), None)
    for one_ipaddr_rec in ipaddr_rec_list:
        one_ipaddr = one_ipaddr_rec[4][0]
        match = ipRe.match(one_ipaddr)
        if match is not None and match.group(0) == one_ipaddr and one_ipaddr != '127.0.0.1':
            ipaddr = one_ipaddr
            break
    return ipaddr


def md5sum(filename, bufSize = 8192):
    """ utility function to calculate the md5 sum """
    md5Sum = md5()

    # the with statement makes sure the file will be closed
    with open(filename, 'rb') as fileObj:

        # We read the file in small chunk until EOF
        content = fileObj.read(bufSize)
        while content:
            # We had data to the md5 hash
            md5Sum.update(content)
            content = fileObj.read(bufSize)

    # We return the md5 hash in hexadecimal format
    return md5Sum.hexdigest()

def calcProgress(low, high, percent):
    """ utility function to calculate the progress between [low-high]

    @param - low - int begining of progress range
    @param - high - int end of progress range
    @param - percent - float progress percent of this range [0-100%]
    @return - int - new progress
    """
    if (percent > 1):
        percent = 1

    return int((high - low) * percent + low)

def _is_unix_link(link_path):
    """ basically a wrapper around path.islink """
    return os.path.islink(link_path)

def islink(link_path):
    """ os independent link detector """
    if(_is_unix_link(link_path)):
        return True
    else:
        return False

def symlink(target_dir, link_path): # TODO : rename to createlink
    """create sym linkPath"""

    # lets not use symlink support by python even if present in win32, as of now
    if (hasattr(os, 'symlink')):
        return os.symlink(target_dir, link_path)
    else:
        raise AgentException('Running platform seems to be neither win32 nor *nix with any (sym)link support. Can\'t proceed with link creation')

def readlink(link):
    """read sym link"""
    if (_is_unix_link(link)):
        return os.readlink(link) #@UndefinedVariable
    else:
        raise AgentException('Running platform seems to be neither win32 nor *nix with any (sym)link support (or) provided link is wrong. Can\'t proceed with link read')

def rmlink(link):
    """ remove symlink """
    LOG.info("removing link %s" % link)
    if (_is_unix_link(link)):
        return os.remove(link)
    else:
        raise AgentException('Running platform seems to be neither win32 nor *nix with any (sym)link support (or) provided link is wrong. Can\'t proceed with link read')

def validatelink(link):
    """ validate a symlink """
    try:
        return islink(link) and os.path.exists(readlink(link))
    except Exception:
        return False

def loadPropFile(proploc):
    """ load json object style properties specified in a file into prop object """
    try:
        with open(proploc, 'r') as propFile:
            prop = json.load(propFile)
            propFile.close()
            return prop
    except (ValueError, OSError) as excp:
        print excp
        raise FileNotFoundError('Cannot read ' + proploc)

def convertPropToParams(prop):
    """ convert properties structure to a list of params with -- prefixed before key """
    proplist = []
    for key, val in prop.iteritems():
        proplist.append(str('--' + key))
        proplist.append(val)
    return proplist

def sysuntar(tarfilepath, destdir):
    ''' use system untar to untar a package '''
    cmd = 'tar -C %s -xz -f %s' % (destdir, tarfilepath)
    ret = os.system(cmd)
    if (ret != 0):
        error = 'untar cmd (%s) returned error code (%d)' % (cmd, ret)
        LOG.error(error)
        raise AgentException(Errors.PACKAGE_UNTAR_FAILURE, error)

def untar(tarfilepath, destdir):
    '''
    Untars a tar ball to desired dir
    '''
    tar = tarfile.open(tarfilepath, errorlevel = 1)
    tar.extractall(destdir)
    tar.close()

def isHigherPrivilegeService(service):
    '''
    Determines if the service is higher priviledge one (used to determine whether to run it as cronus user)
    '''
    return (service == "agent")

def rmrf(aDir):
    ''' deletes a dirctory and its contents '''
    if os.path.exists(aDir):
        try:
            shutil.rmtree(aDir, False, handleRemoveReadonly)
        except OSError:
            cmd = 'rm -rf %s' % aDir
            os.system(cmd)
    return (not os.path.exists(aDir))

def handleRemoveReadonly(func, path, exc):
    """ handle read only file delete """
    excvalue = exc[1]
    if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) # 0777
        func(path)
    else:
        raise    

def removedir(aDir):
    ''' deletes a directory  '''
    os.rmdir(aDir)
    return (not os.path.exists(aDir))

def rchown(path, uid, gid):
    ''' recursive chown.  Given a path, change the uid and gid recrusively.  Will not follow links.
    @param path - string of path to chmod
    @param uid - int uid
    @param gid - int gid
    @return - none
    '''
    if os.path.exists(path):
        cmd = 'sudo chown -R %s:%s %s' % (str(uid), str(gid), path)
        ret = os.system(cmd)
        if (ret != 0):
            error = 'chown cmd (%s) returned error code (%d)' % (cmd, ret)
            LOG.error(error)
            raise AgentException(Errors.UTIL_RCHOWN_ERROR, error)

def chmod(path, mode, sudoUser = 'no'):
    ''' chmod.  Given a path, change the uid and gid.  Will not follow links.
    @param path - string of path to chmod
    @param mode - permission mode
    @return - none
    '''
    cmd = 'chmod %s %s' % (mode, path)
    if sudoUser != 'no':
        cmd = sudoCmd(cmd, sudoUser)
    __execChmod(cmd, Errors.UTIL_CHMOD_ERROR)

def rchmod(path, mode, sudoUser = 'no'):
    ''' recursive chmod.  Given a path, change the uid and gid recrusively.  Will not follow links.
    @param path - string of path to chmod
    @param mode - permission mode
    @return - none
    '''
    cmd = 'chmod -R %s %s' % (mode, path)
    if sudoUser != 'no':
        cmd = sudoCmd(cmd, sudoUser)
    __execChmod(cmd, Errors.UTIL_RCHMOD_ERROR)

def __execChmod(cmd, errcode):
    '''
    Executes given chmod command and throws AgentException with give errCode in case if exec fails.
    '''
    ret = os.system(cmd)
    if (ret != 0):
        error = 'chmod cmd (%s) returned error code (%d)' % (cmd, ret)
        LOG.error(error)
        raise AgentException(errcode, error)

def listdirperlastmodtime(directory, result_absolute = False):
    '''
    Lists the contents of given directory sorted based on last modified time
    @param directory: to list
    @param result_absolute: if true, returns absolute paths; else returns just base names
    '''
    if(not directory or not os.path.isdir(directory)):
        raise AgentException(Errors.FILE_NOT_FOUND_ERROR,
                             'Given directory %s is invalid or doesn\'t exist or not a real directory' % directory)

    contents = os.listdir(directory)
    contents = [os.path.join(directory, f) for f in contents] # add path to each
    newContents = []
    for content in contents:
        try:
            if os.path.getmtime(content):
                newContents.append(content)
        except OSError, osErr:
            LOG.error('Unable to get mod time %s - %s' % (content, osErr))
            
    newContents.sort(key = os.path.getmtime)
    return newContents if result_absolute else [os.path.basename(f) for f in newContents]

def sudoCmd(cmd, user = None):
    ''' decorate a command with sudo
        @param cmd: cmd to be decorated, can be list or string
        @param user: sudo as user, default None
        @return: decorated cmd as list or string
    '''
    agentuser = pylons.config['agent_user_account']
    sudoCmd = []
    isList = isinstance(cmd, list)
    sudoCmd = None
    if user is None: # no user, sudo
        sudoCmd = ['sudo']
    elif agentuser == user: # agent user, no need to sudo
        sudoCmd = []
    else: # other user, sudo -u
        sudoCmd = ['sudo', '-u', user]
    if isList:
        for i in cmd:
            sudoCmd.append(i)
    else:
        sudoCmd.append(cmd)
    return sudoCmd if isList else ' '.join(sudoCmd)


def synchronized(lock):
    """ Synchronization decorator. """

    def wrap(f):
        ''' wrapper '''
        def newFunction(*args, **kw):
            ''' wrapped '''
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()
        return newFunction
    return wrap

def synchronizedInst(f):
    """ Synchronization decorator for class instance. """

    def newFunction(self, *args, **kw):
        ''' wrapper '''
        try:
            rlock = self._sync_lock
        except AttributeError:
            from threading import RLock
            rlock = self.__dict__.setdefault('_sync_lock', RLock())
        rlock.acquire()
        try:
            return f(self, *args, **kw)
        finally:
            rlock.release()

    return newFunction


def checkDiskFull():
    ''' check disk usage and reject request require disk when disk is full '''
    appGlobal = pylons.config['pylons.app_globals']
    if not appGlobal.diskOk:
        msg = 'Cannot complete operation safely, disk is full'
        raise AgentException(Errors.HEALTH_DISKFULL, msg)

ipaddr = getHostIP()
hostname = socket.gethostname()
fqdn = socket.getfqdn()

def trackable():
    ''' logging '''

    def newf(f, self, *args, **kw):
        ''' wrapper '''
        errMsg = None
        startTs = time.time() * 1000

        try:
            result = f(self, *args, **kw)
            return result

        except BaseException as excep:
            errMsg = 'Error status (%s) - %s' % (excep, traceback.format_exc(2))
            raise excep

        finally:
            #log
            msg = []
            corId = contextutils.getcontext(self, 'guid')
            calTitle = contextutils.getcontext(self, 'caltitle')
            calBody = contextutils.popcontext(self, 'calbody')
            remoteAddr = contextutils.popcontext(self, 'remote_addr')

            #construct message
            msg.append('%s - %s' % ('correlationid', xstr(corId)))
            msg.append('%s - %s' % ('request', xstr(calTitle)))
            msg.append('%s - %s' % ('response', xstr(calBody)))
            msg.append('%s - %s' % ('remoteAddr', xstr(remoteAddr)))
            if errMsg:
                msg.append('%s - %s' % ('errMsg', xstr(errMsg)))

            apiTime = time.time() * 1000 - startTs
            msg.append('API time: %.2fms' % apiTime)
            if apiTime > 3000:
                msg.append('Tags: LongAPI')
            APILOG.info('\n' + ','.join(msg))

    return decorator(newf)

def runsyscmd(cmd):
    ''' run system command
        @param cmd: system command to run
    '''
    ret = os.system(cmd)
    if (ret != 0):
        error = 'system cmd (%s) returned error code (%d)' % (cmd, ret)
        LOG.error(error)
        raise AgentException(Errors.UTIL_SYSCMD_ERROR, error)
        
def runsyscmdwstdout(cmd):
    ''' run system command with capture of stdout '''
    LOG.info('run system command %s ' % cmd)
    process = Popen(cmd, stdout=PIPE, close_fds=True)
    preprocessed = process.communicate()[0]
    ret = process.wait()
    if ret != 0:
        error = 'system cmd (%s) returned error code (%d)' % (cmd, ret)
        LOG.error(error)
        raise AgentException(Errors.UTIL_SYSCMD_ERROR, error)
        
    return preprocessed
        
def getuserofpath(path):
    ''' find user of a path '''
    import pwd
    uid = os.stat(os.path.dirname(path)).st_uid
    return pwd.getpwuid(uid)[0]

def xstr(s):
    ''' extends str() '''
    return 'None' if s is None else str(s)

def get_linux_distro():
    """ portable getting linux distro, name and version """
    import platform, subprocess
    _distributor_id_cmdline_re = re.compile("(?:Distributor ID:)\s*(.*)", re.I)
    _release_cmdline_re = re.compile("(?:Release:)\s*(.*)", re.I)

    _distributor_id_file_re = re.compile("(?:DISTRIB_ID\s*=)\s*(.*)", re.I)
    _release_file_re = re.compile("(?:DISTRIB_RELEASE\s*=)\s*(.*)", re.I)

    _distname = None
    _version = None

    try:
        with open("/etc/lsb-release", "rU") as etclsbrel:
            for line in etclsbrel:
                m = _distributor_id_file_re.search(line)
                if m:
                    _distname = m.group(1).strip()
                    if _distname and _version:
                        return (_distname, _version)
                m = _release_file_re.search(line)
                if m:
                    _version = m.group(1).strip()
                    if _distname and _version:
                        return (_distname, _version)
    except EnvironmentError:
        pass

    (_distname, _version) = platform.linux_distribution()[:2]
    if _distname and _version:
        #Bug fix 09 24 2012 Jeff: spaces in distname can lead to bad URLs in  finding the python packages
        #fix: check if there is a space: if yes: replace space by %20  
        _distname = _distname.replace (" ", "_")
        _version = _version.replace (" ", "_")
        return (_distname, _version)

    try:
        p = subprocess.Popen(["lsb_release", "--all"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        rc = p.wait()
        if rc == 0:
            for line in p.stdout.readlines():
                m = _distributor_id_cmdline_re.search(line)
                if m:
                    _distname = m.group(1).strip()
                    if _distname and _version:
                        return (_distname, _version)

                m = _release_cmdline_re.search(p.stdout.read())
                if m:
                    _version = m.group(1).strip()
                    if _distname and _version:
                        return (_distname, _version)
    except EnvironmentError:
        pass

    if os.path.exists("/etc/arch-release"):
        return ("Arch_Linux", "")

    return (_distname, _version)

def copyFile(sourceDir, destinationDir, filename):
    """ copy a file from source dir to dest dir """
    # get owner of parent directory
    sourceFn = os.path.join(sourceDir, filename)
    if os.path.exists(destinationDir) and os.path.exists(sourceFn):
        destUname = getuserofpath(os.path.join(destinationDir, filename))
        cmd = sudoCmd('cp %s %s' % (sourceFn, destinationDir), destUname)
        runsyscmd(cmd)
    else:
        raise AgentException(Errors.INVALID_FILE_NAME, 'source %s %s or destination %s not exist' % (sourceDir, filename, destinationDir))
    
def stringChecksum(val):
    """ string checksum """
    return binascii.crc32(val)    

def usage():
    '''
    Prints the usage of this py module from command line, to console
    '''
    print 'Usage:'
    module_name = os.path.basename(sys.argv[0])
    print(module_name + ' -createlink(or -cl) <src link path> <target dir path> \n (or) \n' + module_name +
          ' -removelink(or -rl) <link path> \n (or) \n' + module_name + ' -untar(or -ut) <tar file path> <destination dir>')

class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, current_dict, past_dict):
        ''' constructor '''
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)
    def added(self):
        ''' added element '''
        return self.set_current - self.intersect
    def removed(self):
        ''' removed element '''
        return self.set_past - self.intersect
    def changed(self):
        ''' changed element '''
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])
    def unchanged(self):
        ''' unchanged element '''
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])
    def isChanged(self):
        ''' is anything changed '''
        return (self.added() or self.removed() or self.changed())

if __name__ == '__main__':
    if(len(sys.argv) > 1):
        type_ = sys.argv[1]
        if(type_ == '-createlink' or type_ == '-cl'):
            if(len(sys.argv) == 4):
                src_link_path = sys.argv[2]
                target_dir = sys.argv[3]
            else:
                usage()
        elif(type_ == '-removelink' or type_ == '-rl'):
            if(len(sys.argv) == 3):
                link = sys.argv[2]
            else:
                usage()
        elif(type_ == '-untar' or type_ == '-ut'):
            if(len(sys.argv) == 4):
                tarfilepath = sys.argv[2]
                destdir = sys.argv[3]
                untar(tarfilepath, destdir)
            else:
                usage()
        else:
            usage()
    else:
        usage()
