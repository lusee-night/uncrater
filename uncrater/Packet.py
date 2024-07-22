import os, sys
import hexdump

if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

# now try to import pycoreloop
try:
    from pycoreloop import struct 
except ImportError:
    print ("Can't import pycoreloop\n")
    print ("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo.")
    sys.exit(1)


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

    def read(self):
        self._read()

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

def copy_attrs (src, dst):
    for attr in dir(src): 
        if attr[0] == '_':
            continue
        setattr(dst, attr, getattr(src, attr))
