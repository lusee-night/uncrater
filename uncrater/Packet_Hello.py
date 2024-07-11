from .Packet import Packet
from .c2python import copy_attrs
from .core_loop import startup_hello
import struct

class Packet_Hello(Packet):
    @property
    def desc(self):
        return  "Hello!!"

    def _read(self):
        super()._read()
        copy_attrs(startup_hello.from_buffer_copy(self.blob), self)
#        for attrs in dir(res): 
#            if "__" in attrs:
#                continue
##            print(attrs)
#           setattr(self, attrs, getattr(res, attrs))
        #self.version = res.version
        #self.packet_id = res.unique_packet_id
        #self.time_sec = res.time_sec
        #self.time_subsec = res.time_subsec
    
    def info (self):
        self._read()
        
        desc = "Hello Packet\n"
        desc += f"SW_Version : {hex(self.SW_version)}\n"
        desc += f"FW_Version : {hex(self.FW_Version) }\n"
        desc += f"FW_ID      : {hex(self.FW_ID) }\n"
        desc += f"FW_Date    : {hex(self.FW_Date) }\n"
        desc += f"FW_Time    : {hex(self.FW_Time) }\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"time_sec : {self.time_seconds}\n"
        desc += f"time_subsec : {self.time_subseconds}\n"
         
        return desc
    
