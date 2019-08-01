def __read_pin_voltage__(pn):
    return float(input("[EXT HARDWARE] Enter voltage of pin "+str(pn)+">"))
def __read_pin__(pn):
    if input("Is pin "+str(pn)+" HIGH? [Y/n]")[0]=="Y":
      return 1
    return 0
class Pin:
    IN = 0
    OUT = 1
    PULL_UP = 1
    def __init__(self, pinnum, t = IN, ex = -1):
        self.p = pinnum
        self.v = 0
        self.conf = [t,ex]
    def value(self, v=None):
        if v==None:
            return __read_pin__(self.p)
        self.v = v
        return v
    def __repr__(self):
        if self.__module__!="__main__":
            q = self.__module__+"."
        else:
            q=""
        return q+"Pin("+str(self.p)+")"
class PWM:
    def __init__(self, pin, freq=0, duty=0):
        if freq<0:
          raise ValueError("Frequency must be positive")
        if(duty>1023 or duty<0):
          raise ValueError("Duty must be in range 0-1023")
        if pin.conf[0]!=Pin.OUT:
          raise ValueError("Pin must be in output mode!")
        self.p = pin
        self.f = freq
        self.d = duty
    def freq(self, f):
        if f<0:
          raise ValueError("Frequency must be positive")
        self.f = f
    def duty(self, d):
        if(d>100 or d<0):
          raise ValueError("Duty must be in range 0-100")
        self.d = d
class ADC:
    def __init__(self, pin, bits = 12):
        if bits>12 or bits<1:
          raise ValueError("bits must be in range 1-12")
        if pin.conf[0]!=Pin.IN:
          raise ValueError("Pin must be in input mode!")
        self.pin = pin
        self.b = bits
    def read(self):
        return int(min(__read_pin_voltage__(self.pin.p),1)*((2**self.b)-1))
