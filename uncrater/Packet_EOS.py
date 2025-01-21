from .PacketBase import PacketBase, pystruct
from .utils import Time2Time
import struct

class Packet_EOS(PacketBase):
    @property
    def desc(self):
        return  "Goodbye!!"

    def _read(self):
        if self._is_read:
            return
        super()._read()
        self.copy_attrs(pystruct.end_of_sequence.from_buffer_copy(self._blob))
        self._is_read = True
        
    def info (self):
        self._read()
        
        desc = "End of Sequence Packet\n"
        desc += f"Unique packet ID : {hex(self.unique_packet_id)}\n"
        desc += f"EOS arg          : {hex(self.eos_arg)}\n"         
        return desc
    
