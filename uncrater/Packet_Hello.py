from .PacketBase import PacketBase, pystruct
from .utils import Time2Time
import struct

class Packet_Hello(PacketBase):
    @property
    def desc(self):
        return  "Hello!!"

    def _read(self):
        if self._is_read:
            return
        super()._read()
        self.copy_attrs(pystruct.startup_hello.from_buffer_copy(self._blob))
        self.time = Time2Time(self.time_32, self.time_16)
        self._is_read = True
        
    def info (self):
        self._read()
        
        desc = "Hello Packet\n"
        desc += f"SW_Version : {hex(self.SW_version)}\n"
        desc += f"FW_Version : {hex(self.FW_Version) }\n"
        desc += f"FW_ID      : {hex(self.FW_ID) }\n"
        desc += f"FW_Date    : {hex(self.FW_Date) }\n"
        desc += f"FW_Time    : {hex(self.FW_Time) }\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"time_sec : {self.time}\n"
         
        return desc
    
