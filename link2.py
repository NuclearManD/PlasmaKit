from ucryptolib import aes
import neonet as net
import os, time

def encode(data, pwd):
    if pwd==None:
        return data
    q = os.urandom(1)
    pwd = (pwd+hex(q[0])[2:]).zfill(16)
    data = len(data).to_bytes(2, 'little') + data
    data = data + bytes(16-len(data)%16)
    encryptor = aes(pwd.encode(), 1)
    out = q+encryptor.encrypt(data)
    return out
def decode(data, pwd):
    if pwd==None:
        return data
    pwd = (pwd+hex(data[0])[2:]).zfill(16)
    decryptor = aes(pwd.encode(), 1)
    data = decryptor.decrypt(data[1:])
    return data[2:2+int.from_bytes(data[:2], 'little')]

class L2NrlConnection:
    def __init__(self, adr, oport, iport = None, password=None):
        self.adr=adr
        self.oport=oport
        if iport==None:
            self.iport = oport
        else:
            self.iport = iport
        self.queue = []
        self.pwd = password
    def send(self,data):
        if net.man==None:
            return False
        return net.man.sendPacket(self.adr,self.oport, encode(data, self.pwd))
    def recv(self,timeout = 8000):
        if self.available()>0:
            return self.queue.pop()
        else:
            timer = net.ntl.millis()+timeout
            while timer>net.ntl.millis():
                if self.available()>0:
                    try:
                        return decode(self.queue.pop(), self.pwd)
                    except:
                        pass
                time.sleep(0.0001)
            return None
    def available(self):
        if net.man==None:
            return len(self.queue)
        i=0
        while i<len(net.man.queue):
            if net.man.queue[i][0]==self.adr and net.man.queue[i][1]==self.iport:
                self.queue.insert(0,net.man.queue.pop(i)[2])
            else:
                i+=1
        return len(self.queue)

class L2NrlOpenPort:
    def __init__(self, oport, iport = None, password = None):
        self.oport=oport
        if iport==None:
            self.iport = oport
        else:
            self.iport = iport
        self.queue = []
        self.pwd = password
    def send(self, adr, data):
        if net.man==None:
            return False
        return net.man.sendPacket(adr,self.oport, encode(data, self.pwd))
    def recv(self,timeout = 8000):
        if self.available()>0:
            return self.queue.pop()
        else:
            timer = net.ntl.millis()+timeout
            while timer>net.ntl.millis():
                if self.available()>0:
                    return self.queue.pop()
                time.sleep(0.0001)
            return None
    def available(self):
        if net.man==None:
            return len(self.queue)
        i=0
        while i<len(net.man.queue):
            if net.man.queue[i][1]==self.iport:
                pk = net.man.queue.pop(i)
                try:
                    self.queue.insert(0,[pk[0],decode(pk[2], self.pwd)])
                except:
                    pass
            else:
                i+=1
        return len(self.queue)
