from Crypto.Cipher import AES

class aes:
    def __init__(self, pwd, t):
        self.cr = AES.new(pwd, AES.MODE_ECB)
    def encrypt(self, data):
        return self.cr.encrypt(data)
    def decrypt(self, data):
        return self.cr.decrypt(data)
