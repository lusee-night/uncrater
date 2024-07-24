from .Packet import Packet, copy_attrs, pystruct
import struct

class Packet_Hello(Packet):
    @property
    def desc(self):
        return  "Hello!!"

    def _read(self):
        super()._read()
        copy_attrs(struct.startup_hello.from_buffer_copy(self.blob), self)
    
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
    
