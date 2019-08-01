class PeripheralRemote:
    def __init__(self, address, name, t):
        self.adr = address
        self.name = name
        self.type = t
    def __add_method__(self, name):
        setattr(self, name, eval("lambda self,*a: self.__call_remote__('"+name+"',a)", {}, {}).__get__(self))
    def __call_remote__(self, fn, args):
        print(fn+":", *args)
        
