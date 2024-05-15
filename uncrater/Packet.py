import os
import hexdump

class Packet:
    def __init__ (self, appid, blob = None, blob_fn = None):
        if (blob is None) and (blob_fn is None):
            raise ValueError
        self.appid = appid
        self.blob = blob
        self.blob_fn = blob_fn
        

    def _read(self):
        if self.blob is None:
            self.blob = open(self.blob_fn,"rb").read()    

    def xxd(self):
        """ xxd style dump of the contents"""
        self._read()
        return hexdump.hexdump(self.blob,result='return')

    @property
    def desc(self):
        return  "generic"


    def info(self):
        """ ASCII readable description.
        To be specialized
        """
        return self.xxd()
