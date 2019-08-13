import neonet_raw as ntl
from random import randint
import _thread, time

# Neonet Routing Layer should be called NRL
# Neonet Transit Layer should be called NTL

# I think most of this file will need to be rewritten at some point.
# yea this file is a mess....

# data packet structure:
#  ________________________________________________________________
# | target_address(64) | sender_address(64) | port(32) | data (8n) \
# |____________________|____________________|__________|___________/
#
# since neonet's underlying transit layer keeps track of packet size, we don't need to
# include the length of the data section.
#
# 20 bytes is the minimum data packet length

# registration packet structure:
#  _______________
# | area_code(48) |
# |_______________|
#
# This type of packet's only purpose is to register an area code with an endpoint
# whose uplinks are dynamically allocated
#
# is always 6 bytes


# common addresses

ADR_BCAST    = 0x0000FFFF   # All devices across the entire accessible Neonet network.
ADR_LOCAL    = 0x00000000   # this system, loopback, like localhost.   May not always work!
                            # > It is recommended to use a loopback uplink instead.

DEFAULT_AREA_CODE = "*"

def rand_addr(is_root = True):
    r = 1
    if not is_root:
        r = randint(0,65535)
    r|=randint(0,0x7FFFFFFFFFFF)<<16
    return r

# None of the above addresses are 'absolute addresses'.  An absolute address always maps to the same device
# on the network.

debug_nrl = False#True
is_in_debug = False
def debug(*s):
    global is_in_debug
    if debug_nrl:
        while is_in_debug:
            time.sleep(0.00001)
        is_in_debug = True
        print("DEBUG: ".join(s))
        is_in_debug = False

# this just manages connections and routes packets to their destinations.
# it also receieves NRL packets.
class NrlConnectionManager:
    def __init__(self, address, routing_table={}):
        self.routing = routing_table
        self.uplinks = {}
        self.index = {}
        self.address = address
        self.queue = []
        self.is_updating=False
    def addUplink(self, uplink, key=None):
        if uplink.ping(8000)==-1:
            debug("Ping error!")
            return
        
        if key in self.uplinks.keys():
            self.uplinks[key].close()
            
        ut = uplink.getType()
        
        uplink.sendData((self.address>>16).to_bytes(6,'little'))
        if key==None:
            if not ut in self.index.keys():
                self.index[ut]=0
            key = ut+str(self.index[ut])
            self.index[ut]+=1
        while self.is_updating:
            time.sleep(.0001)
        self.uplinks[key] = uplink
        debug("New Uplink: "+repr(key))
    def addRoute(self, address, key):
        debug("New Route: "+hex(address)+'-0000 -> '+repr(key))
        self.routing[address]=key
    def update(self):
        while self.is_updating:
            time.sleep(0.0001)
        self.is_updating=True
        for i in self.uplinks.keys():
            u = self.uplinks[i]
            u.update()
            while u.available()>0:
                data = u.getPacket()
                if len(data)==6:
                    self.addRoute(int.from_bytes(data,'little'),i)
                elif len(data)>=20:
                    target = int.from_bytes(data[:8],'little')
                    if target == self.address:
                        # it's for me!
                        sender = int.from_bytes(data[8:16],'little')
                        port = int.from_bytes(data[16:20],'little')
                        #print("recv")
                        self.queue.insert(0,[sender,port,data[20:]])
                    else:
                        target = target>>16
                        if not target in self.routing.keys():
                            target = DEFAULT_AREA_CODE # default area code
                        if target in self.routing.keys(): # only transmit if we have a route for it
                            key = self.routing[target] # we have the route!
                            if key!=i and key in self.uplinks.keys():  # transmit to a different uplink or don't transmit at all
                                try:
                                    self.uplinks[key].sendData(data) # send the raw packet
                                except:
                                    pass  # oops, connection closed?  Dunno, but dont die
                else:
                    debug("Error: bad packet of length "+str(len(data))+" was received.")
        self.is_updating=False
    def available(self):
        return len(self.queue)
    def getPacket(self, timeout = 8000):
        self.update()
        if self.available()>0:
            return self.queue.pop()
        timer = ntl.millis() + timeout
        while ntl.millis()<timeout:
            self.update()
            if len(self.queue)>0:
                return self.queue.pop()
            time.sleep(0.005)
        return None
    def sendPacket(self, dest, port, data):
        if dest == self.address:
            # it's for me!
            self.queue.insert(0,[dest,port,data])
            return
        ac = dest>>16 # ac stands for 'area code'
        debug("Area code is "+hex(ac))
        if not ac in self.routing.keys():
            ac = DEFAULT_AREA_CODE # default area code
        if ac in self.routing.keys(): # only transmit if we have a route for it
            key = self.routing[ac] # we have the route!
            if key in self.uplinks.keys():  # transmit to an uplink (if it exists)
                try:
                    data = port.to_bytes(4,'little')+data
                    data = self.address.to_bytes(8,'little')+data
                    data = dest.to_bytes(8,'little')+data
                    self.uplinks[key].sendData(data) # send the raw packet
                except:
                    pass  # oops, connection closed?  Dunno, but dont die
            else:
                debug("Uplink "+repr(key)+" was not found!")
        else:
            debug("No route found to "+hex(dest))
    def updater(self):    
        while True:
            self.update()
            time.sleep(.001)
    def startUpdateThread(self):
        return _thread.start_new_thread(self.updater,())
    def exportRoutingTable(self):
        out = ''
        for i in self.routing.keys():
            if type(i)==str:
                out+="route "+i+' '+self.routing[i]+'\n'
            else:
                out+="route "+hex(i)+'**** '+self.routing[i]+'\n'
        return out
_man = None
def handler(link):
    link.ping(1000)
    print("Connected.")
    _man.addUplink(link)
def test():
    global _man
    c_adr = rand_addr()
    s_adr = rand_addr()
    print("Server address: "+hex(s_adr))
    print("Client address: "+hex(c_adr))
    cman = NrlConnectionManager(c_adr)
    sman = NrlConnectionManager(s_adr)
    cman.startUpdateThread()
    sman.startUpdateThread()
    _man = sman
    port = randint(81,8000)
    print("Using port "+str(port))
    ntl.startNeonetServerThread(handler, port)
    time.sleep(.1)
    cman.addUplink(ntl.TcpClientUplink("localhost",port))
    print("Waiting for routes to resolve...")
    time.sleep(.1)
    cman.sendPacket(s_adr, 1192, b'Hello World!')
    packetBack = sman.getPacket()
    if packetBack==None:
        print("Test failed!")
        return False
    else:
        print("Packet receieved back: "+repr(packetBack))
        return True
def readRoutingTable(text):
    text = text.replace('\r','\n').replace(';','#').replace('\t',' ')
    lines = text.split('\n')
    out = {}
    for i in range(len(lines)):
        line = lines[i].split('#',1)[0]
        if line=='' or line.isspace():
            continue
        r_chunks = line.split(' ')
        chunks = []
        for i in r_chunks:
            i = i.strip()
            if i!='':
                chunks.append(i)
        if chunks[0]=='route':
            if chunks[1]=='*':
                adr = DEFAULT_AREA_CODE
            elif chunks[1].endswith('****'):
                adr = int(chunks[1][2:-4],16)
            else:
                print("Line "+str(i+1)+": Cannot process route "+str(chunks[1])+", but this may be due to a software limitation.")
                continue
            out[adr]=chunks[2]
        else:
            print("Line "+str(i+1)+": Command '"+chunks[0]+"' not found.")
    return out
        
        
