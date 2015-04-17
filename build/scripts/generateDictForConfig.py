import json

configDict = {
          'orchestrator': {
                           'reg': {
                                   'server:main': {'port': 9010}, 
                                   'app:main': {'stateserver.port': 9000},
                                   'handler_orchestrator': {'level':'NOTSET'}
                                   },
                           'dev': {
                                   'server:main': {'port': 11010}, 
                                   'app:main': {'stateserver.port': 11000},
                                   'handler_orchestrator': {'level':'DEBUG'}
                                   },
                           'test': {
                                   'server:main': {'port': 10010}, 
                                   'app:main': {'stateserver.port': 10000},
                                   'handler_orchestrator': {'level':'CRITICAL'}
                                   },
                           'prod': {
                                   'server:main': {'port': 12010}, 
                                   'app:main': {'stateserver.port': 12000},
                                   'handler_orchestrator': {'level':'DEBUG'}
                                   }
                           },
          'agent':        {
                           'reg': {
                                   'server:main': {'port': 9020}, 
                                   'app:main': {'stateserver.port': 9000},
                                   'handler_agent': {'level':'NOTSET'}
                                   },
                           'dev': {
                                   'server:main': {'port': 11020}, 
                                   'app:main': {'stateserver.port': 11000},
                                   'handler_agent': {'level':'DEBUG'}
                                   },
                           'test': {
                                   'server:main': {'port': 10020}, 
                                   'app:main': {'stateserver.port': 10000},
                                   'handler_agent': {'level':'CRITICAL'}
                                   },
                           'prod': {
                                   'server:main': {'port': 12020}, 
                                   'app:main': {'stateserver.port': 12000},
                                   'handler_agent': {'level':'DEBUG'}
                                   }
                           },
           'dashboard': {}
          }

if __name__ == '__main__':
    f = open('iniChanges.json', 'w')
    f.write(json.dumps(configDict))
    f.close