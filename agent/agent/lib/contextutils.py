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
'''
managing context in an object
Created on Sep 22, 2011

@author: biyu
'''

CTX_DICT = 'jobcontext'
CTX_NAMES = ['guid', 'service', 'thread_timeout', 'thread_progress_timeout']

def injectcontext(target, ctx):
    ''' dynamically add a property to a dict of properties
        @param target: target object where context to be injected
        @param dictname: name of the context dict
        @param ctx: values in the context as dict
    '''
    try:
        propDict = getattr(target, CTX_DICT)
        propDict.update(ctx)
    except AttributeError:
        # dict not exist, create one
        propDict = {}
        propDict.update(ctx)
        setattr(target.__class__, CTX_DICT, propDict)
        
def copycontexts(source, target, names):
    """ copy context properties from source to target object """
    for name in names:
        copycontext(source, target, name)

def copycontext(source, target, name):
    ''' copy context property from source to target object
        @param source: source
        @param target: target
        @param dictname: name of the context
        @param name: key of property
    '''
    if existcontext(source, name):
        value = getcontext(source, name)
        injectcontext(target, {name:value})

def getcontext(source, name, defValue = None):
    ''' get property value from a dict of properties
        @param source: source
        @param dictname: name of the context
        @param name: key of the property
        @param defValue: default value if key not exist
        @return: value from context, or default value if key or context not exist
    '''
    try:
        propDict = getattr(source, CTX_DICT)
        return propDict.get(name, defValue)
    except AttributeError:
        return defValue

def popcontext(source, name, defValue = None):
    ''' on successfully get property from a dict of properties, remove the property from dict
        @param source: source
        @param dictname: name of the context
        @param name: key of the property
        @param defValue: default value if key not exist
        @return: value from context, or default value if key or context not exist
    '''
    try:
        propDict = getattr(source, CTX_DICT)
        return propDict.pop(name, defValue)
    except AttributeError:
        return defValue


def existcontext(source, name):
    ''' test if a property exist in context
        @param source: source
        @param dictname: name of the context
        @param name: key of the property
        @return: Boolean of key existence
    '''
    try:
        ctx = getattr(source, CTX_DICT)
        return ctx.has_key(name) and ctx[name] is not None
    except AttributeError:
        return False
    
def resetcontext(source):
    ''' reset all context on source '''
    try:
        ctx = getattr(source, CTX_DICT)
        ctx.clear()
    except AttributeError:
        pass
    


