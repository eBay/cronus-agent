#pylint: disable=W0612, W0703,W0105
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
GraphiteD

@author: biyu
'''


from pylons import config
import logging
import multiprocessing
import socket
import select


LOG = logging.getLogger(__name__)

class GraphiteDServer(multiprocessing.Process):
    """ udp server for receiving graphite metrics """

    def __init__(self, inputp):
        ''' constructor '''
        multiprocessing.Process.__init__(self)

        self.__port = int(config['graphite_udp_port'])
        self.__sock = socket.socket(socket.AF_INET, # Internet
                 socket.SOCK_DGRAM) # UDP
        self.__sock.setblocking(False)
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__sock.bind(("0.0.0.0", self.__port))
        self.__inputp = inputp
        self.exit = multiprocessing.Event()

    def run(self):
        ''' run '''
        try:
            while not self.exit.is_set():
                ready = select.select([self.__sock], [], [], 0.1)
                if ready[0]:    
                    data, addr = self.__sock.recvfrom(65535) 
                    LOG.debug("graphite received message: %s - %s" % (data, addr))
                    self.__inputp.send(data)
        
        finally:        
            if self.__sock:
                self.__sock.close()
        
    def stop(self):
        """ stop this thread from running at the next check """
        self.exit.set()
    
    @staticmethod
    def read_queue(output_p):
        """ read and process message from queue """
        while True:
            try:
                msg = output_p.recv()    # Read msg off the pipe and do nothing
                LOG.debug("graphite received message from queue: %s" % msg)
                GraphiteDServer.handle_msg(msg)
            except EOFError:
                break
#        while True:
#            try: 
#                line = queue.get_nowait()
#            except Queue.Empty:
#                time.sleep(1)
#            else: # got line
#                GraphiteDServer.handle_msg(line)
    
    @staticmethod        
    def handle_msg(msg):
        ''' handle data '''
        # Adding a bit of extra sauce so clients can
        # send multiple samples in a single UDP
        # packet.
        try:
            data = {}
            for line in msg.splitlines():
                if not line.strip():
                    continue
                (mres, mservice, mname, mvalue) = GraphiteDServer.handle_line(line)
                key = (mservice, mres)
                if key not in data:
                    data[(mservice, mres)] = []
                data[key].append({'key': mname, 'value': mvalue})
            
            appGlobal = config['pylons.app_globals']
            for (mdata_key, mdata_value) in data.items():
                appGlobal.agentMonitor.runExtMonitor(mdata_key[0], 'graphite', mdata_key[1], mdata_value)
                
        except Exception as exc:
            LOG.error(str(exc))

    @staticmethod        
    def handle_line(line):
        '''
        graphite data format "metric_path value timestamp"
        our special graphite format "service.metric_path.resSec value timestamp"
        service = system|application|agent|actualservice
        resSec = 10|20|30
        '''
        bits = line.split(None, 2)
        mpath = bits.pop(0)
        mvalue = bits.pop(0)
        LOG.debug('%s %s' % (mpath, mvalue))
        msbits = mpath.split('.', 1)
        mservice = msbits.pop(0)
        mrbits = msbits.pop(0).rsplit('.', 1)
        mname = mrbits.pop(0)
        mres = mrbits.pop(0)
        LOG.debug('%s %s %s %s' % (mres, mservice, mname, mvalue))
        
        return (mres, mservice, mname, mvalue)
