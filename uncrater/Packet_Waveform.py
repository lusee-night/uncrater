from .Packet import Packet
import struct
import numpy as np


class Packet_Waveform(Packet):
    @property
    def desc(self):
        return  "Raw Waveform"

    def _read(self):
        if hasattr(self,"waveform"):
            return
        super()._read()
        fmt = "16384H"
        self.waveform = np.array(struct.unpack(fmt,self.blob))
        self.waveform[self.waveform>8192] -= 16384 
        print (self.waveform)
        self.ch = self.appid - 0x2f0
        
    def info (self):
        self._read()
        desc = f"Raw waveform for channel {self.ch}\n"        
        desc += f"Min value: {self.waveform.min()}"
        desc += f"Max value: {self.waveform.max()}"
        desc += f"Mean value: {self.waveform.mean()}"
        return desc
    