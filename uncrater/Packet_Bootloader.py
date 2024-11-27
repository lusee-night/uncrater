from .PacketBase import PacketBase
from .utils import Time2Time
import struct
import numpy as np


class Packet_Bootloader(PacketBase):
    @property
    def desc(self):
        return  "Raw Waveform"

    def _read(self):
        if self._is_read:
            return
        super()._read()
        self.header = struct.unpack("8I", self._blob[:32])
        msg_type = ["BL_STARTUP", "BL_JumpTo_FLT_SW", "BL_PRGM_CHKSUM", "BL_PRGM_VERIFY", "BL_ERROR"]
        self.msg_type = self.header[0]
        if (self.msg_type<5):
            self.msg_type_str = msg_type[self.msg_type]
        else:
            self.msg_type_str = "Unknown"
        self.seq = self.header[1]
        self.time = Time2Time(self.header[2],self.header[3])
        self.compilation_date = self.header[4]
        self.compilation_time = self.header[5]
        self.payload_len = self.header[6]
        self.magic = (self.header[7]==0xfeedface)
        try:
            self.payload = np.array(struct.unpack(f"{self.payload_len}I", self._blob[32:32+self.payload_len*4]))
        except:
            self.payload = None


                
    def info (self):
        self._read()
        desc = "Bootloader Packet\n"
        desc += f"MSG_Type : {self.msg_type_str}\n" 
        desc += f"Seq      : {self.seq}\n"
        desc += f"Timestamp: {self.time}\n"
        desc += f"Compilation date: {self.compilation_date:X}\n"
        desc += f"Compilation time: {self.compilation_time:X}\n"
        desc += f"Payload Length: {self.payload_len}\n"
        desc += f"Magic OK: {self.magic}\n"
        desc += f"Payload: "
        for v in self.payload:
            desc+=f" {v:X}"
        desc+="\n"
        if self.msg_type == 1:
            desc += f"Loading region: {self.payload[0]}\n"
        elif self.msg_type==2:
            for i in range(6):
                desc += f"Region {i+1} : Size = {self.payload[3*i+0]*4} Checksum = {self.payload[3*i+1]:X} Expected Checksum = {self.payload[3*i+2]:X} \n"
            

        return desc
    
