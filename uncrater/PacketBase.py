import os, sys
import hexdump
from .coreloop import pycoreloop,pycoreloop_203,pycoreloop_305,pycoreloop_307
pystruct = pycoreloop.pystruct
pystruct_203 = pycoreloop_203.pystruct
pystruct_305 = pycoreloop_305.pystruct
pystruct_307 = pycoreloop_307.pystruct


class PacketBase:
    def __init__ (self, appid, blob = None, blob_fn = None, version=None, **kwargs):
        if (blob is None) and (blob_fn is None):
            raise ValueError
        self.appid = appid
        self._blob = blob
        self._blob_fn = blob_fn
        self._version = version
        self._is_read = False
        for key, value in kwargs.items():
            setattr(self, key, value)
        if blob is not None:
            self._read()
        

        
    def _read(self):
        if self._is_read:
            return
        if self._blob is None:
            self._blob = open(self._blob_fn,"rb").read()    

    def read(self):
        self._read()

    def _analyze_attr(self, attr_name: str, obj: object, full_attr_name: str) -> None:
        attr = getattr(obj, attr_name)
        full_attr_name += f'{attr_name}.'
        if isinstance(attr, object) and type(attr).__module__ != 'builtins':
            self._analyze_hk(attr, full_attr_name)
        else:
            self.attr_dict[full_attr_name.strip('.')].append(attr)

    def _analyze_hk(self, obj: object, full_attr_name='') -> None:
        # slotted classes generated in core_loop.py
        print (obj,full_attr_name)
        if hasattr(obj, '__slots__'):
            for slot in obj.__slots__:
                if slot[0] == '_':
                    continue
                self._analyze_attr(slot, obj, full_attr_name)
        # top level Packet class
        elif obj.__class__.__module__ != 'builtins':
            for attr_name in vars(obj):
                if attr_name[0] == '_':
                    continue
                self._analyze_attr(attr_name, obj, full_attr_name)


    def keys(self):
        def it_keys(d):
            l = []
            klist = getattr(d,"__slots__") if hasattr(d,"__slots__") else dir(d)
            for k in klist:
                if k[0]=='_':
                    continue        
                a = getattr(d,k)
                if not hasattr(a, "__slots__"):
                    if not (callable(a)):
                        l.append(k)
                else:
                    for sk in it_keys(a):
                        l.append(k+'.'+sk)
            return l 
        return it_keys(self)
    
    def __getitem__(self,name):
        def get_dotted(obj,name):
            if '.' in name:
                i = name.find('.')
                first,second = name[:i], name[i+1:]
                if hasattr(obj,first):
                    return get_dotted(getattr(obj,first),second)
                else:
                    return None
            else:
                return getattr(obj,name)
        return get_dotted(self,name)

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

    def copy_attrs (self,src):
        for attr in dir(src): 
            if attr[0] == '_':
                continue
            setattr(self, attr, getattr(src, attr))