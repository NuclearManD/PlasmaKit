import neonet_routing_layer as nrl
import neonet_raw as ntl
import time

# this module's purpose is to connect to neonet and establish connections.
# it does not (easily) support more advanced setups, like network switches between different types of hardware.


address = nrl.rand_addr(False)

DEFAULT_TCP_SERVERS = [('68.5.129.54',1155)]#,('192.168.0.1',16927)]

man = None

_is_setup = False
def setup(adr=address, tcp_servers = DEFAULT_TCP_SERVERS, routing_table={nrl.DEFAULT_AREA_CODE:"tcp0"}):
    global address, man, _is_setup
    if _is_setup:
        return "Already set up!"
    address = adr
    man = nrl.NrlConnectionManager(address,routing_table)
    man.startUpdateThread()
    for i in tcp_servers:
        man.addUplink(ntl.TcpClientUplink(i[0],i[1]))
    man.addUplink(ntl.LoopbackUplink())
    man.addUplink(ntl.NullUplink())
    _is_setup = True
class NrlConnection:
    def __init__(self, adr, oport, iport = None):
        self.adr=adr
        self.oport=oport
        if iport==None:
            self.iport = oport
        else:
            self.iport = iport
        self.queue = []
    def send(self,data):
        if man==None:
            return False
        return man.sendPacket(self.adr,self.oport, data)
    def recv(self,timeout = 8000):
        if self.available()>0:
            return self.queue.pop()
        else:
            timer = ntl.millis()+timeout
            while timer>ntl.millis():
                if self.available()>0:
                    return self.queue.pop()
                time.sleep(0.0001)
            return None
    def available(self):
        if man==None:
            return len(self.queue)
        i=0
        while i<len(man.queue):
            if man.queue[i][0]==self.adr and man.queue[i][1]==self.iport:
                self.queue.insert(0,man.queue.pop(i)[2])
            else:
                i+=1
        return len(self.queue)

class NrlOpenPort:
    def __init__(self, oport, iport = None):
        self.oport=oport
        if iport==None:
            self.iport = oport
        else:
            self.iport = iport
        self.queue = []
    def send(self, adr, data):
        if man==None:
            return False
        return man.sendPacket(adr,self.oport, data)
    def recv(self,timeout = 8000):
        if self.available()>0:
            return self.queue.pop()
        else:
            timer = ntl.millis()+timeout
            while timer>ntl.millis():
                if self.available()>0:
                    return self.queue.pop()
                time.sleep(0.0001)
            return None
    def available(self):
        if man==None:
            return len(self.queue)
        i=0
        while i<len(man.queue):
            if man.queue[i][1]==self.iport:
                pk = man.queue.pop(i)
                self.queue.insert(0,[pk[0],pk[2]])
            else:
                i+=1
        return len(self.queue)
