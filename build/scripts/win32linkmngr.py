'''
Created on Mar 22, 2011

Handles win32 link creation, read, removal according to the support available in the running platform

@author: hshankar
'''

from subprocess import Popen, PIPE
import logging
import os
import platform
import shutil
import sys

LOG = logging.getLogger(__name__)
SUCCESS = 0
SPACE = ' '

def createwin32link(src_link_path, target_dir):
    ''' Creates a link in win32 platform to a target dir. In order,
        a. Tries to create symlink, if supported
        b. If unsupported, falls back to creating junction pt, if it's supported
        c. If unsupported, falls back to creating a vanilla .link file with the target path hard-coded in it
    '''
    try:
        create_symlink(src_link_path, target_dir)
    except UnSupportedByWin32Error:
        try:
            create_junction_pt(src_link_path, target_dir)
        except UnSupportedByWin32Error:
            create_vanillalink(src_link_path, target_dir)

def removewin32link(link):
    try:
        remove_symlink(link)
    except InvalidWin32SymlinkError:
        try:
            remove_junction_pt(link)
        except InvalidWin32JuncPtError:
            remove_vanillalink(link)        
        
def readwin32link(link):
    try:
        return(read_symlink(link))
    except InvalidWin32SymlinkError:
        try:
            return(read_junction_pt(link))
        except InvalidWin32JuncPtError:
            return(read_vanillalink(link))

def read_vanillalink(link):
    linkPath = os.path.join(link, '.link')
    if (not os.path.exists(linkPath)):
        return None
    else:
        linkfile = open(linkPath, 'r')
        targetPath = linkfile.read()
        linkfile.close()
        return(targetPath) 
                
def remove_vanillalink(link):
    shutil.rmtree(link)
#    os.remove(link) 
                
def create_vanillalink(src_link_path, target_dir):
    ''' Simulates a link i.e. creates a vanilla .link file with given target dir path as content
    '''
    if(not os.path.exists(src_link_path)):
        os.mkdir(src_link_path)
    linkpath = os.path.join(src_link_path, '.link')
    linkfile = open(linkpath, 'w')
    linkfile.write(target_dir)
    linkfile.close()
    if (os.name == 'nt'):
        cmd = "attrib +h %s" % linkpath
        os.system(cmd)            

def create_junction_pt(src_junc_pt, target_dir):
    ''' Creates junction point if supported by the running win32 platform(typically available from Win 2K).    
        
     @param src_junc_pt: full path including name of junction point that's to be created 
         (for e.g. C:\test\sample_junc_pt); Parent directory (C:\test, in e.g.) must exist  
     @param target_dir: for which junction point has to be created; must exist; if relative, 
         assumed that its present in same directory where link is to be created
     @see: http://en.wikipedia.org/wiki/NTFS_junction_point    
     @see http://windowsdevcenter.com/pub/a/oreilly/windows/news/win2kcommands_0401.html#linkd
    '''
    ensure_win32_presence('junction point creation')
    
    if(not os.path.isabs(target_dir)):
        # target should be rel dir. Let's form the absolute path based on 
        # given link par path, so that 'linkd' cmd can succeed
        parent_dir = os.path.dirname(src_junc_pt)
        abs_target_dir = os.path.join(parent_dir, target_dir)
        if(not os.path.exists(abs_target_dir) or not os.path.isdir(abs_target_dir)):
            raise IllegalStateError(abs_target_dir + ' formed as abs path out of ' + target_dir + ' based on given junc pt\'s par dir either doesn\'t exist or not a dir; Or may be we detected it as rel dir wrongly?')
    else:
        abs_target_dir = target_dir 
    cmd = formcmd('linkd', src_junc_pt, abs_target_dir)
    statuscode, stdout, stderr = run_with_shell(cmd)
    
    errmsg = _errmsg_junc_cre(stdout, stderr)         
    ensure_cmdexec_passed(statuscode, errmsg)
    LOG.info('Successfully created junc pt ' + src_junc_pt + ' to target ' + target_dir + '(' + abs_target_dir + ')')
    
def _errmsg_junc_cre(stdout, stderr):
    errmsg = ('Junction point creation failed as it is not seemed to be supported by this win32 platform ' + ''.join(platform.uname()) +
                 '. Support is available only from Win2K systems.\n') + _std_opcumerr(stdout, stderr) 
    return (errmsg)                  

def remove_junction_pt(junc_pt):
    ''' Removes the junction point specified, if it exists. This neither deletes the pointing target directory 
    nor checks whether param is really a junction point, so if it's just an empty normal directory/file it's just removed.  
      
    @param junc_pt: that's to be removed 
    '''
    ensure_win32_presence('junction point deletion')
    
    try:
        if(_is_reparse_point(junc_pt)):
            cmd = formcmd('linkd', junc_pt, '/D')
            statuscode, stdout, stderr = run_with_shell(cmd)
            
            errmsg = _errmsg_junc_del(stdout, stderr)          
            ensure_cmdexec_passed(statuscode, errmsg)
            LOG.info('Successfully deleted junc pt ' + junc_pt)
        else:
            raise InvalidWin32JuncPtError(junc_pt + ' doesn\'t seem to be a valid reparse (junction) point')
    except UnSupportedByWin32Error, e:
        raise InvalidWin32JuncPtError(e.__str__())
    
def _errmsg_junc_del(stdout, stderr):
    errmsg = ('Junction point deletion failed; probably \'linkd\' junc pt cmd not supported by this win32 platform ' + ''.join(platform.uname()) +
                 '. Also check if it is really a junction point. Or could be some other genuine failure\n') + _std_opcumerr(stdout, stderr) 
    return (errmsg)

def create_symlink(src_symlink, target_dir):
    ''' Creates symbolic link if supported by the running win32 platform(typically available from Win Vista).       
     
     @param src_symlink: full path including name of symlink that's to be created 
         (for e.g. C:\test\sample_symlink); Parent directory (C:\test, here) must exist  
     @param target_dir: for which symlink has to be created; must exist; if relative,  
         assumed that its present in same directory where link is to be created
    '''
    ensure_win32_presence('symlink creation')
    
    errmsg = _errmsg_sym_cre('', '')
    ensure_symlink_support(errmsg)
    
    import jaraco.windows.filesystem as fs;
    fs.symlink(target_dir, src_symlink, True)
    LOG.info('Successfully created symlink ' + src_symlink + ' to target ' + target_dir)    
    
#def _create_symlink(src_symlink, target_dir_or_file):
#    ''' Creates symbolic link if supported by the running win32 platform(typically available from Win Vista).       
#     
#     @param src_symlink: full path including name of symlink that's to be created 
#     (for e.g. C:\test\sample_symlink); Parent directory (C:\test, here) must exist  
#     @param target_dir_or_file: for which symlink has to be created; must exist
#     @see: http://en.wikipedia.org/wiki/Symbolic_link    
#     @see: http://www.maxi-pedia.com/mklink
#    '''
#    ensure_win32_presence('symlink creation')
#    
#    cmd = formcmd('mklink', src_symlink, target_dir_or_file)
#    statuscode, stdout, stderr = run(cmd)
#    
#    errmsg = _errmsg_sym_cre(stdout, stderr)
#    ensure_cmdexec_passed(statuscode, errmsg)
#    LOG.info('Successfully created symlink ' + src_symlink + ' to target ' + target_dir_or_file)

def _errmsg_sym_cre(stdout, stderr):
    errmsg = ('Symlink not seemed to be supported by this win32 platform ' + ''.join(platform.uname()) + 
                 '. Support is available only from Win Vista.\n') + _std_opcumerr(stdout, stderr) 
    return (errmsg)

def remove_symlink(link_to_dir):
    ''' Removes the link_to_dir (to a dir) specified, if it exists.    
     
    @param link_to_dir: that's to be removed 
    '''
    ensure_win32_presence('symlink to dir deletion')
    
    try:
        errmsg = _errmsg_sym_del('', '')
        ensure_symlink_support(errmsg)
        
        import jaraco.windows.filesystem as fs;
        if fs.is_symlink(link_to_dir):            
            do_win32_rmdir(link_to_dir)
        else:
            raise InvalidWin32SymlinkError(link_to_dir + ' doesn\'t seem to be a valid symlink (though running platform seems to support symlink')
        LOG.info('Successfully deleted link_to_dir ' + link_to_dir)
    except UnSupportedByWin32Error, e:
        raise InvalidWin32SymlinkError(e.__str__())
    
def do_win32_del_file(file):
    cmd = formcmd('del', file)
    statuscode, stdout, stderr = run_with_shell(cmd)
    if(statuscode != SUCCESS):
        raise UnexpectedWin32LinkError('Failed to delete ' + file + ' using \'del\' cmd. ' + _std_opcumerr(stdout, stderr))

def do_win32_rmdir(dir):
    cmd = formcmd('rmdir', dir)
    statuscode, stdout, stderr = run_with_shell(cmd)
    if(statuscode != SUCCESS):
        raise UnexpectedWin32LinkError('Failed to delete ' + dir + ' using \'rmdir\' cmd. ' + _std_opcumerr(stdout, stderr))
    
def _remove_symlink(symlink):
    ''' Removes the symlink specified, if it exists.    
     
    @param symlink: that's to be removed 
    '''
    ensure_win32_presence('symlink deletion')
    
    cmd = formcmd('del', '/F', '/S', '/Q', symlink)
    statuscode, stdout, stderr = run(cmd)
    
    errmsg = _errmsg_sym_del(stdout, stderr)        
    ensure_cmdexec_passed(statuscode, errmsg)
    LOG.info('Successfully deleted symlink ' + symlink)

def _errmsg_sym_del(stdout, stderr):
    errmsg = ('Symlink not seemed to be supported by this win32 platform ' + ''.join(platform.uname()) + 
                 '. Check if it is really a symlink.\n') + _std_opcumerr(stdout, stderr) 
    return (errmsg)

def _std_opcumerr(stdout, stderr):
    msg = ''
    if(len(stdout) != 0):
        msg += 'Standard o/p:\n' + stdout + '\n'
    if(len(stderr) != 0):
        msg += 'Err msg gotten:\n' + stderr
    return(str(msg))

def read_symlink(link):
    ensure_win32_presence('read symlink')
    
    errmsg = _errmsg_sym_read('', '')
    try:
        ensure_symlink_support(errmsg)    
        import jaraco.windows.filesystem as fs;
        if fs.is_symlink(link):
            return(get_symlink_target(link))
        else:
            raise InvalidWin32SymlinkError(link + ' doesn\'t seem to be a valid symlink (though running platform seems to support symlink')
    except UnSupportedByWin32Error, e:
        raise InvalidWin32SymlinkError(e.__str__())

def get_symlink_target(link):
    """
    get_symlink_target(link) -> target
    Return a string representing the path to which the symbolic link points.
    Similar to jaraco.windows.filesystem.readlink(link) except that 
    opened file handle is closed properly, to prevent leak
    """
    import jaraco.windows.api.filesystem as api
    import jaraco.windows.error as e
    from ctypes import (POINTER, cast, create_string_buffer)
    handle = api.CreateFile(
        link,
        0,
        0,
        None,
        api.OPEN_EXISTING,
        api.FILE_FLAG_OPEN_REPARSE_POINT|api.FILE_FLAG_BACKUP_SEMANTICS,
        None,
        )
    
    if handle == api.INVALID_HANDLE_VALUE:
        raise WindowsError()

    res = api.DeviceIoControl(handle, api.FSCTL_GET_REPARSE_POINT, None, 10240)

    bytes = create_string_buffer(res)
    p_rdb = cast(bytes, POINTER(api.REPARSE_DATA_BUFFER))
    rdb = p_rdb.contents
    e.handle_nonzero_success(api.CloseHandle(handle))
    if not rdb.tag == api.IO_REPARSE_TAG_SYMLINK:
        raise RuntimeError("Expected IO_REPARSE_TAG_SYMLINK, but got %d" % rdb.tag)
    return rdb.get_print_name()

def _errmsg_sym_read(stdout, stderr):
    errmsg = ('Symlink not seemed to be supported by this win32 platform ' + ''.join(platform.uname()) + 
                 '. Check if it is really a symlink.\n') + _std_opcumerr(stdout, stderr) 
    return (errmsg)

def read_junction_pt(link):
    ensure_win32_presence('read junction pt')
    try:        
        if(_is_reparse_point(link)):    
            import win32con, winioctlcon, winnt, win32file
            import struct
            h = win32file.CreateFile(link, 0,
                        win32con.FILE_SHARE_READ|win32con.FILE_SHARE_WRITE|win32con.FILE_SHARE_DELETE, None,
                        win32con.OPEN_EXISTING,
                        win32file.FILE_FLAG_OVERLAPPED|win32file.FILE_FLAG_OPEN_REPARSE_POINT|win32file.FILE_FLAG_BACKUP_SEMANTICS, 0)
            output_buf=win32file.AllocateReadBuffer(winnt.MAXIMUM_REPARSE_DATA_BUFFER_SIZE)
            buf=win32file.DeviceIoControl(h, winioctlcon.FSCTL_GET_REPARSE_POINT,None,
                        OutBuffer=output_buf, Overlapped=None)
            fixed_fmt='LHHHHHH'
            fixed_len=struct.calcsize(fixed_fmt)
            tag, datalen, reserved, target_offset, target_len, printname_offset, printname_len = \
                        struct.unpack(fixed_fmt, buf[:fixed_len])
            ## variable size target data follows the fixed portion of the buffer
            name_buf=buf[fixed_len:]
        
    #        target_buf=name_buf[target_offset:target_offset+target_len]
    #        target=target_buf.decode('utf-16-le')
            _target_buf=name_buf[printname_offset:printname_offset+printname_len]
            _target=_target_buf.decode('utf-16-le')
    #        print _target        
            return _target 
        else:
            raise InvalidWin32JuncPtError(link + ' doesn\'t seem to be a valid reparse (junction) point')
    except UnSupportedByWin32Error, e:
        raise InvalidWin32JuncPtError(e.__str__()) 
    
def _is_reparse_point(path):
    """
    Determine if the given path is a reparse point.
    """
    from ctypes import (windll) 
    from ctypes.wintypes import (LPWSTR, DWORD)
    INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
    FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    GetFileAttributes = windll.kernel32.GetFileAttributesW #@UndefinedVariable
    GetFileAttributes.argtypes = (LPWSTR,)
    GetFileAttributes.restype = DWORD
    res = GetFileAttributes(path)
    if res == INVALID_FILE_ATTRIBUTES: raise UnSupportedByWin32Error('Unable to obtain file attributes from running platform. Is it really win32 2K?')
    return bool(res & FILE_ATTRIBUTE_REPARSE_POINT)
    
def _errmsg_junc_read(stdout, stderr):
    errmsg = ('Junction pt not seemed to be supported by this win32 platform ' + ''.join(platform.uname()) + \
                 '. Check if it is really a symlink.\n') + _std_opcumerr(stdout, stderr) 
    return (errmsg)

def run(cmd):
    ''' Runs the given cmd and waits until it finishes.
    @return:  status code along with stdout,stderr
    '''
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()    
    return(p.returncode, stdout, stderr)

def run_with_shell(cmd):
    ''' Runs the given cmd with shell and waits until it finishes.
    @return:  status code along with stdout,stderr
    '''
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()    
    return(p.returncode, stdout, stderr)

def formcmd(cmd, *args):
    fullcmd = cmd
    for arg in args:
        fullcmd = fullcmd + SPACE + arg
    return(fullcmd)
 
def ensure_symlink_support(errmsg):
    try:
        # This creates attribute out of win32 function CreateSymbolicLinkW 
        # that's present only in symlink supported win32  
        from ctypes import (windll)
        CreateSymbolicLink = windll.kernel32.CreateSymbolicLinkW #@UndefinedVariable @UnusedVariable  
    except AttributeError as ae:
        # attr not resolved as symlink support not seem to be available in this win32
        errmsg += 'Err msg:\n' + ae.__str__()
        raise UnSupportedByWin32Error(errmsg)

def ensure_cmdexec_passed(statuscode, errmsg):
    if(statuscode != SUCCESS):
        raise UnSupportedByWin32Error(errmsg)
    
def ensure_win32_presence(operation):
    if(os.name != 'nt'):
        raise IllegalRequestError('This is NOT a win32 platform' + platform.uname() + ' but requested operation \'' + operation +  '\' requires one')

def iswin32():
    return(os.name == 'nt')

def usage():
    print 'Usage:'
    module_name = os.path.basename(sys.argv[0])
    print(module_name + ' -create(or -c) <src link path> <target dir path> \n (or) \n' + module_name + ' -remove(or -r) <link path>')

class IllegalArgError(Exception):
    pass

class FileNotFoundError(Exception):
    pass

class UnSupportedByWin32Error(Exception):
    pass

class IllegalRequestError(Exception):
    pass

class InvalidWin32SymlinkError(Exception):
    pass

class InvalidWin32JuncPtError(Exception):
    pass

class UnexpectedWin32LinkError(RuntimeError):
    pass 

class IllegalStateError(Exception):
    pass

if __name__ == '__main__':
    if(len(sys.argv) > 1):
        type = sys.argv[1]
        if(type == '-create' or type == '-c'):
            if(len(sys.argv) == 4):
                src_link_path = sys.argv[2]
                target_dir = sys.argv[3]
                createwin32link(src_link_path, target_dir)
            else:
                usage() 
        elif(type == '-remove' or type == '-r'):
            if(len(sys.argv) == 3):
                link = sys.argv[2]          
                removewin32link(link)      
            else:
                usage() 
        else:
            usage()
    else:
        usage()    
    
