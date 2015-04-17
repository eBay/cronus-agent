#pylint: disable = W0404,W0105
'''
Created on Nov 16, 2010

@author: ppa
'''
try:
    import simplejson as json
except ImportError:
    import json

class MetrixManager():
    """ status class """
    def __init__(self):
        """ constructor """
        self.__data = {} #{priority0: {key, value}, priority1:{key, value}}

    def register(self, key, func, priority = 10):
        """ register key, value pair """
        if priority not in self.__data:
            self.__data[priority] = {}
        self.__data[priority][key] = func

    def unregister(self, key, priority = 10):
        """ unregister key, value pair """
        if priority in self.__data:
            if key in self.__data[priority]:
                del self.__data[priority][key]
                if not len(self.__data[priority]):
                    del self.__data[priority]

    def getStatus(self):
        """ return a list """
        ret = []
        for priority in sorted(self.__data):
            for key, func in self.__data[priority].items():
                ret.append((key, func()))
        return ret

    def getJsonStatus(self):
        """ return a list """
        ret = {}
        for priority in sorted(self.__data):
            for key, func in self.__data[priority].items():
                ret[key] = func()
        return json.dumps(ret)
