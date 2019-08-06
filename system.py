import periph
from random import randint

def gen_adr():
    area_code_base = 0xDBC700000000
    area_code = area_code_base | randint(0,0xFFFFFF)
    return (area_code<<16)|0x0001

default_peers = []

class System:
    def __init__(self, peers=default_peers, address = gen_adr(), use_cpu = True, dbg = print):
        periph.start_server(address)
        if use_cpu:
            self.local_cpu = periph.PeriphCPU()
        else:
            self.local_cpu = None

        if(dbg!=None):
            dbg("Connecting to peers...")

        for i in peers:
            try:
                periph = periph.lsperiph(i)
            except:
                if(dbg!=None):
                    dbg(hex(i)+" is not online.")
        
        self.global_cpu = periph.PeriphCombinedCPU(cpus)
