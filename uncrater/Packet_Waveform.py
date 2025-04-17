from .PacketBase import PacketBase
import struct
import numpy as np


class Packet_Waveform(PacketBase):
    @property
    def desc(self):
        return  "Raw Waveform"

    def _read(self):
        if self._is_read:
            return
        super()._read()
        fmt = "16384H"
        try:
            self.waveform = np.array(struct.unpack(fmt, self._blob))
        except struct.error as e:
            print (f"Wrong packet size in waveform!! Ignoring: {e}")
            self.waveform = np.zeros(16384, dtype=np.uint16)
        self.waveform[self.waveform>8192] -= 16384 
        self.ch = self.appid - 0x2f0
        if self.ch>=512:
            self.ch -= 512
        self._is_read = True
                
    def info (self):
        self._read()
        desc = f"Raw waveform for channel {self.ch}\n"        
        desc += f"Min value: {self.waveform.min()}\n"
        desc += f"Max value: {self.waveform.max()}\n"
        desc += f"Mean value: {self.waveform.mean()}\n"
        return desc
    
