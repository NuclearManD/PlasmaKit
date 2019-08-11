import periph, _thread
net = periph.net
from random import randint

def gen_adr():
    area_code_base = 0xDBC700000000
    area_code = area_code_base | randint(0,0xFFFFFF)
    return (area_code<<16)|0x0001

csys = None
server_started = False
def server_code(netkey, sys):
    global server_started
    open_port = net.NrlOpenPort(0x192291, 0x291192)
    server_started = True
    while True:
        kleg = open_port.recv(60000)
        if kleg!=None:
            src = kleg[0]
            data = kleg[1].split(b'\x00')
            cmd = data[0]
            if cmd==b'getkey':
                open_port.send(src,netkey.encode())
            elif cmd==b'has_cpu':
                if sys.local_cpu!=None:
                    res = b'1'
                else:
                    res = b'0'
                open_port.send(src, res)
            elif cmd==b'register':
                open_port.send(src, b'ok')
                if (not src in sys.peers) and sys.test_peer(src):
                    sys.add_peer(src)
                    
def start_server(address, netkey, sys):
    periph.start_server(address)
    print("Starting system server...")
    _thread.start_new_thread(server_code,(netkey,sys))

default_peers = []
class System:
    def __init__(self, peers=default_peers, address = gen_adr(), netkey = 'comnet', use_cpu = True, dbg = print):
        global csys
        if csys!=None:
            raise Exception("System already exists.")
        if use_cpu:
            self.local_cpu = periph.PeriphCPU()
            periph.bindLocalPeripheral(self.local_cpu, 'sys_cpu')
        else:
            self.local_cpu = None

        self.netkey = netkey
        
        start_server(address, netkey, self)
        csys = self

        if(dbg!=None):
            dbg("Connecting to peers...")
        self.peers = []
            
        for i in peers:
            try:
                if self.test_peer(i):
                    self.add_peer(i)
            except:
                if(dbg!=None):
                    dbg(hex(i)+" is not online.")
        
        #self.global_cpu = periph.PeriphCombinedCPU(cpus)
    def test_peer(self, adr):
        con = net.NrlConnection(adr, 0x291192, 0x192291)
        con.send(b'getkey')
        return con.recv(8000).decode()==self.netkey
    def add_peer(self, adr):
        
