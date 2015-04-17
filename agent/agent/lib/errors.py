#pylint: disable=C0111,W0105
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
""" List of error constants used in the agent """

import traceback

class Errors(object):
    """ class hosts error code constants """

    # general errors
    UNKNOWN_ERROR = 1
    FILE_NOT_FOUND_ERROR = 2
    INVALID_FILE_NAME = 3
    HTTP_READ_ERROR = 4
    INVALID_REQUEST = 5
    WIN32_UNSUPPORTED_ERROR = 6
    INVALID_AUTH = 401

    # service related errors
    SERVICE_EXISTS = 100
    SERVICE_NOT_FOUND = 101
    SERVICE_DELETE_NOT_VALID = 102
    SERVICE_DELETE_FAILED = 102
    SERVICE_IN_USE = 103

    # manifest related errors
    MANIFEST_MISSING_SERVICE = 200
    MANIFEST_ALREADY_EXISTS = 201
    MANIFEST_NOT_FOUND = 202
    MANIFEST_ALREADY_IN_PROGRESS = 203
    MANIFEST_PACKAGE_PARSING_ERROR = 204
    MANIFEST_PACKAGE_DOWNLOAD_FAILED = 205
    MANIFEST_PATH_ERROR = 206
    MANIFEST_DELETING_ACTIVE_MANIFEST = 207
    MANIFEST_PACKAGE_DOES_NOT_EXIST = 208
    MANIFEST_REPORT_FAILED = 209

    # thread system
    THREAD_CAT_ALREADY_EXISTS = 300
    THREAD_ALREADY_ADDED = 301
    REJECT_REQUEST = 302
    THREAD_KILLED_AGENT_RESTART = 303
    AGENT_STOPPING = 304

    # agent thread
    AGENT_THREAD_STOPPED = 400
    AGENT_THREAD_TIMEDOUT = 10401 # this is a client error
    AGENT_THREAD_PROGRESS_TIMEDOUT = 10402 # this is a client error 
    AGENT_THREAD_NOT_CANCELABLE = 403

    # action
    ACTIVEMANIFEST_MANIFEST_MISSING = 500
    INVALID_LIFECYCLE_ACTION = 501

    # package
    PACKAGE_SCHEME_ERROR = 600
    PACKAGE_PATH_ERROR = 601
    PACKAGE_INPROGRESS_EXISTS = 602
    PACAKGE_SCRIPT_NOT_FOUND = 603
    PACKAGE_CLEANUP_FAILED = 604
    PACKAGE_EXPAND_NOT_SUPPORTED = 605
    PACKAGE_CHECKSUM_ERROR = 606
    PACKAGE_NOT_FOUND = 607
    INVALID_PACKAGE = 608
    PACKAGE_UNTAR_FAILURE = 609

    # status
    STATUS_UUID_NOT_FOUND = 700

    # distribution client related errors
    DC_MISSING_TORRENT = 800
    DC_MISSING_PACKAGE = 801
    DC_MISSING_PROP_FILE = 802
    DC_DUPLICATE_PACKAGE = 803
    DC_UNSUPPORTED_PROTOCOL = 804
    DC_FAILED_DOWNLOAD = 805
    DC_FAILED_VALIDATE = 806
    DC_IP_PROBLEM = 807
    
    # module related errors
    MODULE_PACKAGE_PARSING_ERROR = 900
    

    # util
    UTIL_RCHOWN_ERROR = 1001
    UTIL_RCHMOD_ERROR = 1002
    UTIL_SYSCMD_ERROR = 1003
    UTIL_CHMOD_ERROR = 1004

    # services cleaup
    SERVICES_CLEANUP_FAIL = 1101

    # Log errors
    LOG_DIR_NOT_FOUND_ERROR = 1201
    LOG_FILE_NOT_FOUND_ERROR = 1202
    LOG_MANIFEST_FILE_NOT_FOUND_ERROR = 1203
    NOT_ENOUGH_PARAMS = 1204
    LOG_PARAM_REQUIRED = 1205
    LOG_APP_DIR_CONFIG_MISSING = 1207
    LOG_APP_DIR_NOT_FOUND = 1208
    SERVICE_NOT_FOUND = 1209
    CRONUS_INI_EMPTY_NOT_FOUND = 1210

    # agent health
    HEALTH_DISKFULL = 1401
    
    # monitoring
    MONITOR_INVALID_RESOLUTION = 1501
    
    # client error
    CLIENT_SCRIPT_ERROR = 10000
    

class AgentException(Exception):
    """ Agent exception """
    def __init__(self, error, errorMsg):
        """ constructor  """
        Exception.__init__(self)
        self.__error = error
        self.__errorMsg = errorMsg
    def __str__(self):
        """ string """
        return repr(self.__errorMsg)
    def getCode(self):
        """ accessor """
        return self.__error
    def getMsg(self):
        """ accessor """
        return "%s" % (self.__errorMsg if self.__errorMsg else traceback.format_exc(2))
    
class ConcurrentActivityException(AgentException):
    
    def __init__(self, error_msg, uuid):
        """constructor"""
        AgentException.__init__(self, Errors.THREAD_CAT_ALREADY_EXISTS, error_msg)
        self.__conflictuuid = uuid
        
    def getConflictUuid(self):
        """ return conflict uuid """        
        return self.__conflictuuid

class FileNotFoundError(AgentException):

    def __init__(self, error_msg):
        """ constructor  """
        AgentException.__init__(self, Errors.FILE_NOT_FOUND_ERROR, error_msg)

class ServiceNotFoundError(AgentException):
    def __init__(self, error_msg):
        """ constructor """
        AgentException.__init__(self, Errors.SERVICE_NOT_FOUND, error_msg)

class ManifestNotFoundError(AgentException):
    def __init__(self, error_msg):
        """ constructor """
        AgentException.__init__(self, Errors.MANIFEST_NOT_FOUND, error_msg)

class PackagePathError(AgentException):
    def __init__(self, error_msg):
        """ constructor """
        AgentException.__init__(self, Errors.PACKAGE_PATH_ERROR, error_msg)

class PackageScriptNotFound(AgentException):
    def __init__(self, error_msg):
        """ constructor """
        AgentException.__init__(self, Errors.PACAKGE_SCRIPT_NOT_FOUND, error_msg)
