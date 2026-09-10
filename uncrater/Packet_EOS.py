from .PacketBase import PacketBase
from .utils import Time2Time
import struct

class Packet_EOS(PacketBase):
    @property
    def desc(self):
        return  "Goodbye!!"

    def _read(self):
        if self._is_read:
            return
        attrs = self._decode_struct(self.schema.pystruct.end_of_sequence)
        if attrs is None:
            return
        self.copy_attrs(attrs)
        self._is_read = True
        
    def info (self):
        self._read()
        
        desc = "End of Sequence Packet\n"
        desc += f"Unique packet ID : {hex(self.unique_packet_id)}\n"
        desc += f"EOS arg          : {hex(self.eos_arg)}\n"         
        return desc
    
