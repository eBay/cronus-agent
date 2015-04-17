#pylint: disable=W0702,W0105
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
Created on Sep 1, 2011

@author: araveendrann
'''
import sys

def setuppath(path, modulename, classlist):
    ''' path '''
    if path not in sys.path:
        sys.path.append(path)

    moduleexist = (modulename in sys.modules)
    mod = __import__(modulename, fromlist=classlist)
    
    if moduleexist:
        # reload the same module
        mod = reload(mod)
        
    def getattrsafe(conf, key):
        ''' get attribute '''
        try:
            return getattr(conf, key)
        except:
            return None   
        
    return dict((k, getattrsafe(mod, k)) for k in classlist)        

def removepath(path, modulename, classlist):
    ''' remove path '''
    if path in sys.path:
        moduleexist = (modulename in sys.modules)
        mod = __import__(modulename, fromlist=classlist)
    
        if moduleexist:
            del sys.modules[modulename]

        if mod is not None:
            del mod

        sys.path.remove(path)
