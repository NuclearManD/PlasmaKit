import neonet as net
from link2 import L2NrlConnection, L2NrlOpenPort
from random import randint
import _thread, os

def lsperiph(adr, password = None):
    con = L2NrlConnection(adr, 0xF00F1337, 0xF00F1338, password)
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

def file_size(fn):
    return os.stat(fn)[6]
_codebase_1 = """class _A:
    def __init__(self, address, name, con):
        self._adr = address
        self._name = name
        self._con = con
    def __call_remote__(self, fn, args):
        self._con.send(b'call\\x00'+self._name.encode()+b"\\x00"+fn+b"\\x00"+repr(list(args)).encode())
        res = self._con.recv()
        if res==None:
            raise Exception("Connection Error")
        else:
            res = res.split(b'\\x00')
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
"""
_codebase_2 = """    def {}(self, *a):
        return self.__call_remote__(b'{}', a)
"""
def PeripheralRemote(address, name, password = None, dbg = print):
    code = _codebase_1
    if(dbg!=None):
        dbg("Connecting to "+hex(address)+"...")
    con = L2NrlConnection(address, 0xF00F1337, 0xF00F1338, password)
    if(dbg!=None):
        dbg("Exchanging data...")
    con.send(b'ls\x00'+name.encode())
    rv = con.recv()
    if rv==None:
        raise Exception("Connection Error")
    tokens = rv.split(b'\x00')
    if tokens[0]==b'error':
        raise Exception(tokens[1].decode())
    if tokens[0]!=b'ok':
        raise Exception("Protocol Error")
    for i in tokens[1:]:
        if len(i)>0:
            i = i.decode()
            code+=_codebase_2.format(i,i)
    l = {}
    exec(code, {}, l)
    
    return l['_A'](address, name, con)
server_started = False
glob_periphs = {}

# meant to be run in a new thread
def server_code(password = None):
    global server_started
    open_port = L2NrlOpenPort(0xF00F1338, 0xF00F1337, password)
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
                    
def start_server(address = 0x10820000|randint(0,0xFFFF), password = None):
    print("Connecting to network...")
    net.setup(address)
    print("Starting server...")
    _thread.start_new_thread(server_code,(password,))

def bindLocalPeripheral(obj, name):
    name = name.replace(' ', '_')
    if '__periph_name__' in dir(obj):
        raise Exception("Failed to set name for new peripheral "+name+".  Perhaps it was being binded for the second time?")
    glob_periphs[name] = obj
    return obj
def unbindLocalPeripheral(name):
    glob_periphs.pop(name)

class PeriphCPU:
    def __init__(self):
        self.work = {}
    def startJob(self, code):
        idn = os.urandom(4)
        self.work[idn] = [_thread.start_new_thread(self.__work__, (code,idn))]
    def __work__(self, code, idn):
        try:
            resultat = eval(code, globals(), {})
        except SyntaxError:
            resultat = exec(code, globals(), {})
        self.work[idn].append(resultat)
    def status(self, idn):
        if not idn in self.work.keys():
            return -1
        if len(self.work[idn])==2:
            return True
        return False
    def getResult(self, idn):
        if not idn in self.work.keys():
            raise ValueError("Invalid job ID")
        if len(self.work[idn])!=2:
            raise Exception("Job not finished.")
        return self.work[idn][1]
    """def killJob(self, idn):
        if not idn in self.work.keys():
            raise ValueError("Invalid job ID")
        if len(self.work[idn])==2:
            raise Exception("Job finished.")
        
        """
    def numRunning(self):
        cnt = 0
        for i in self.work.keys():
            if len(self.work[i])<2:
                cnt+=1
        return cnt
    def cleanFinished(self):
        for i in list(self.work.keys()):
            if len(self.work[i])==2:
                self.work.pop(i)


class PeriphCombinedCPU:
    def __init__(self, cpus):
        if type(cpus)!=list or len(cpus)<1:
            raise ValueError("Cannot accept argument.")
        self.cpus = cpus
        self.cpucnt = 0
        self.work = {}
    def startJob(self, code):
        idn = os.urandom(4)
        cpu = self.cpus[self.cpucnt]
        self.cpucnt = (self.cpucnt+1)%len(self.cpus)
        jobid = cpu.startJob(code)
        self.work[idn] = [cpu, jobid]
    def status(self, idn):
        if not idn in self.work.keys():
            return -1
        return self.work[idn][0].status(self.work[idn][1])
    def getResult(self, idn):
        if not idn in self.work.keys():
            raise ValueError("Invalid job ID")
        return self.work[idn][0].getResult(self.work[idn][1])
    def numRunning(self):
        cnt = 0
        for i in self.cpus:
            cnt+=i.numRunning()
        return cnt
    def cleanFinished(self):
        for i in list(self.work.keys()):
            if self.status(i):
                self.work.pop(i)
        for i in self.cpus:
            i.cleanFinished()
 
class FileBlockDev:
    def __init__(self, filename, num_sectors):
        if os.path.isfile(filename):
            self.file = open(filename, 'ab+')
            self.size = file_size(filename)//512
        else:
            self.file = open(filename, 'wb+')
            for i in range(num_sectors):
                self.file.write(bytes(512))
            self.size = num_sectors

    def readblocks(self, block_num, buf):
        self.file.seek(block_num*512)
        data = self.file.read(len(buf))
        for i in range(len(buf)):
            buf[i] = data[i]

    def writeblocks(self, block_num, buf):
        self.file.seek(block_num*512)
        self.file.write(buf)
    def ioctl(self, op, arg):
        if op == 2:
            self.file.close()
        elif op == 3:
            self.file.flush()
        elif op == 4: # get number of blocks
            return self.size
        elif op == 5: # get block size
            return 512

def uploadFile(adr, cpu_or_term, filename, remotepath = None, dbg = print):
    if remotepath==None:
        remotepath = filename
    if 'exec' in dir(cpu_or_term):
        def execute(code):
            return cpu_or_term.exec(code)
    else:
        def execute(code):
            job = cpu_or_term.startJob(code)
            while True!=cpu_or_term.status(job):
                pass
            return cpu_or_term.getResult(job)
    f1 = open(filename, 'rb')
    tmp_fn = remotepath+'_p_tmp.xyz'
    dir_res = execute('dir()')
    if 'bindLocalPeripheral' in dir_res:
        periph_ident = ''
    elif 'periph' in dir_res:
        periph_ident = 'periph.'
    else:
        periph_ident = '_periph_.'
        execute('import periph as _periph_')
    execute("tmp=open('"+tmp_fn+"', 'wb')\n"
            +periph_ident+"bindLocalPeripheral(tmp, 'tmp')\n")
    if(dbg!=None):
        dbg("Starting data transfer...")
    f2 = PeripheralRemote(adr, 'tmp', dbg)
    while True:
        data = f1.read(512)
        if len(data)==0:
            break
        f2.write(data)
        if(dbg!=None):
            dbg(".", end='')
    f2.close()
    if(dbg!=None):
        dbg("\nTransferred.  Committing...")
    execute("try:\n\tos.remove('"+remotepath+"')\nexcept:\n\tpass\n"+
            "os.rename('"+tmp_fn+"', '"+remotepath+"')")
    execute(periph_ident+"unbindLocalPeripheral('tmp')")
    
