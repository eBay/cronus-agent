#pylint: disable=W0703,W0105
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
Created on Aug 29, 2011

@author: araveendrann
'''
from pylons.wsgiapp import PylonsApp
import logging
import traceback

LOG = logging.getLogger(__name__)

class CronusPylonApp(PylonsApp):
    '''
    classdocs
    '''

    def __init__(self, config=None, **kwargs):
        '''
        Constructor
        '''
        super(CronusPylonApp, self).__init__(config)
                
    
    def find_controller(self, controller):
        ''' find controller '''
        val = None
        try:
            if (controller in self.globals.dynacontrollers):
                val = self.globals.dynacontrollers[controller]
            else:
                val = super(CronusPylonApp, self).find_controller(controller)
                            
        except Exception as excep:
            err_msg = 'Error status (%s) - %s' % (excep, traceback.format_exc(2))
            LOG.error('Unexpected error: %s' % err_msg)
            
        return val
