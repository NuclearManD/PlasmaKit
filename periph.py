import neonet as net
from random import randint
import _thread

class PeripheralRemote:
    def __init__(self, address, name, t, dbg = print):
        self.adr = address
        self.name = name
        self.type = t
        if(dbg!=None):
            dbg("Connecting to "+str(address)+"...")
        self.connection = net.NrlConnection(address, 0xF00F1337)
        if(dbg!=None):
            dbg("Exchanging data...")
        self.connection.send(b'ls\x00'+name.encode())
        rv = self.connection.recv()
        if rv==None:
            raise Exception("Connection Error")
        tokens = rv.split(b'\x00')
        if tokens[0]==b'error':
            raise Exception(tokens[1])
        if tokens[0]!=b'ok':
            raise Exception("Protocol Error")
        for i in tokens[1:]:
            self.__add_method__(i)
    def __add_method__(self, name):
        setattr(self, name, eval("lambda self,*a: self.__call_remote__('"+name+"',a)", {}, {}).__get__(self))
    def __call_remote__(self, fn, args):
        print(fn+":", *args)


server_started = False
glob_periphs = {}

# meant to be run in a new thread
def server_code():
    global server_started
    open_port = net.NrlOpenPort(0xF00F1337)
    server_started = True
    while True:
        kleg = open_port.recv()
        if kleg!=None:
            src = kleg[0]
            data = kleg[1].split(b'\x00')
            cmd = data[0]
            if cmd==b"ls":
                if len(data)==1:
                    pkt = b'ok\x00'
                    for i in glob_periphs:
                        pkt+=i.encode()+b'\x00'
                    open_port.send(src, pkt)
                else:
                    if not data[1] in glob_periphs.keys():
                        open_port.send(src, b'error\x00Peripheral \''+data[1]+b'\' not found')
                    else:
                        pkt = b'ok\x00'
                        v = vars(glob_periphs[data[1]])
                        for i in v.keys():
                            if i[:2]!='__' and callable(v[i]):
                                pkt+=i.encode()+b'\x00'
                        open_port.send(src, pkt)
            elif cmd==b'call':
                if len(data)!=4:
                    open_port.send(src, b'error\x00Invalid command structure')
                elif not data[1].decode() in glob_periphs.keys():
                    open_port.send(src, b'error\x00Peripheral \''+data[1]+b'\' not found')
                else:
                    periph = glob_periphs[data[1].decode()]
                    fn = data[2].decode()
                    v = dir(periph)
                    if (not fn in v) or not callable(eval("periph."+fn)):
                        open_port.send(src, b'error\x00Function \''+fn.encode()+b'\' not found')
                    else:
                        resultat = ''
                        try:
                            tmp = eval(data[3])
                            if type(tmp)!=list:
                                tmp = [tmp]
                            resultat = repr(eval("periph."+fn)(*tmp))
                            open_port.send(src, b'ok\x00'+resultat.encode())
                        except Exception as e:
                            resultat = repr(e)
                            open_port.send(src, b'error\x00'+resultat.encode())
            else:
                open_port.send(src, b'error\x00Invalid command \''+cmd+b'\'')
                    
def start_server(address = 0x10820000|randint(0,0xFFFF)):
    print("Connecting to network...")
    net.setup(address)
    print("Starting server...")
    _thread.start_new_thread(server_code,())

def bindLocalPeripheral(obj, name):
    name = name.replace(' ', '_')
    if '__periph_name__' in dir(obj):
        raise Exception("Failed to set name for new peripheral "+name+".  Perhaps it was being binded for the second time?")
    obj.__periph_name__ = name
    glob_periphs[name] = obj
    return obj

