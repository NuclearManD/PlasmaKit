import periph, _thread
net = periph.net
from random import randint
from link2 import *

def gen_adr():
    area_code_base = 0x7BC700000000
    area_code = area_code_base | randint(0,0xFFFFFF)
    return (area_code<<16)|0x0001

server_started = False
def server_code(netkey, sys, psw):
    global server_started
    open_port = L2NrlOpenPort(0x192291, 0x291192, psw)
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
                _thread.start_new_thread(sys.add_peer,(src,))
                    
def start_server(address, netkey, sys, password):
    periph.start_server(address, password)
    print("Starting system server...")
    _thread.start_new_thread(server_code,(netkey, sys, password))

default_peers = []
class System:
    def __init__(self, peers=default_peers, address = gen_adr(), netkey = 'comnet', use_cpu = True, password = None, dbg = print):
        if use_cpu:
            self.local_cpu = periph.PeriphCPU()
            periph.bindLocalPeripheral(self.local_cpu, 'sys_cpu')
        else:
            self.local_cpu = None

        self.netkey = netkey
        self.psw = password
        
        start_server(address, netkey, self, password)

        if(dbg!=None):
            dbg("Connecting to peers...")
        self.peers = []
        self.cpus = []
            
        for i in peers:
            try:
                self.add_peer(i)
            except:
                if(dbg!=None):
                    dbg(hex(i)+" is not online.")
        
        self.global_cpu = periph.PeriphCombinedCPU(self.cpus+[self.local_cpu])
    def add_peer(self, adr):
        con = L2NrlConnection(adr, 0x291192, 0x192291, self.psw)
        con.send(b'getkey')
        for i in self.peers:
            if i[0]==adr:
                return
        if con.recv(8000).decode()==self.netkey:
            con.send(b'register')
            if con.recv()!=b'ok':
                return
            self.peers.append([adr,con])
            con.send(b'has_cpu')
            if con.recv()==b'1':
                self.cpus.append(periph.PeripheralRemote(adr, 'sys_cpu', self.psw))
    def ls_periph(self):
        devices = []
        for peer in self.peers:
            for i in periph.lsperiph(peer[0], self.psw):
                devices.append(peer[0], i)
    
