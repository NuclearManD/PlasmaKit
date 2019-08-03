import neonet as net
from random import randint
import _thread

def lsperiph(adr):
    con = net.NrlConnection(adr, 0xF00F1337)
    con.send(b'ls')
    rv = con.recv()
    if rv==None:
        raise Exception("Connection Error")
    tokens = rv.split(b'\x00')
    if tokens[0]==b'error':
        raise Exception(tokens[1].decode())
    if tokens[0]!=b'ok':
        raise Exception("Protocol Error")
    if tokens[-1]==b'':
        return tokens[1:-1]
    return tokens[1:]

class PeripheralRemote:
    def __init__(self, address, name, dbg = print):
        self._adr = address
        self._name = name
        self._methods = {}
        if(dbg!=None):
            dbg("Connecting to "+str(address)+"...")
        self._con = net.NrlConnection(address, 0xF00F1337)
        if(dbg!=None):
            dbg("Exchanging data...")
        self._con.send(b'ls\x00'+name.encode())
        rv = self._con.recv()
        if rv==None:
            raise Exception("Connection Error")
        tokens = rv.split(b'\x00')
        if tokens[0]==b'error':
            raise Exception(tokens[1].decode())
        if tokens[0]!=b'ok':
            raise Exception("Protocol Error")
        for i in tokens[1:]:
            self.__add_method__(i.decode())
    def __add_method__(self, name):
        self._methods[name] = eval("lambda self,*a: self.__call_remote__(b'"+name+"',a)", {}, {}).__get__(self)
    def __call_remote__(self, fn, args):
        self._con.send(b'call\x00'+self._name.encode()+b"\x00"+fn+b"\x00"+repr(list(args)).encode())
        res = self._con.recv()
        if res==None:
            raise Exception("Connection Error")
        else:
            res = res.split(b'\x00')
            if len(res)!=2 or not res[0] in [b'ok', b'raise', b'error']:
                raise Exception("Protocol Error")
            elif res[0]==b'error':
                raise Exception(res[1].decode())
            elif res[0]==b'raise':
                raise eval(res[1])
            elif res[0]==b'ok':
                return eval(res[1])
            else:
                raise Exception("You should never see this error, perhaps Thanos is here?")
    def __getattr__(self, namen):
      if namen in self._methods.keys():
        return self._methods[namen]
      return eval("self."+namen)

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
                    if not data[1].decode() in glob_periphs.keys():
                        open_port.send(src, b'error\x00Peripheral \''+data[1]+b'\' not found')
                    else:
                        pkt = b'ok\x00'
                        periph = glob_periphs[data[1].decode()]
                        v = dir(periph)
                        for i in v:
                            if i[:2]!='__' and callable(eval("periph."+i, {}, {'periph':periph})):
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
                    if (not fn in v) or not callable(eval("periph."+fn, {}, {'periph':periph})):
                        open_port.send(src, b'error\x00Function \''+fn.encode()+b'\' not found')
                    else:
                        resultat = ''
                        try:
                            tmp = eval(data[3])
                            if type(tmp)!=list:
                                tmp = [tmp]
                            resultat = repr(eval("periph."+fn, {}, {'periph':periph})(*tmp))
                            open_port.send(src, b'ok\x00'+resultat.encode())
                        except Exception as e:
                            resultat = repr(e)
                            open_port.send(src, b'raise\x00'+resultat.encode())
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
    glob_periphs[name] = obj
    return obj

