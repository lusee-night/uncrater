from .PacketBase import PacketBase, pystruct
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
        self.waveform = np.array(struct.unpack(fmt, self._blob))
        self.waveform[self.waveform>8192] -= 16384 
        self.ch = self.appid - 0x2f0
        if self.ch>=512:
            self.ch -= 512
        self._is_read = True
        self.timestamp = 0xFFFFFFFFFFFFFFFF
        self.meta = None                

    def info (self):
        self._read()
        desc = f"Raw waveform for channel {self.ch}\n"        
        desc += f"Min value: {self.waveform.min()}\n"
        desc += f"Max value: {self.waveform.max()}\n"
        desc += f"Mean value: {self.waveform.mean()}\n"
        desc += f"ADC Time: {self.timestamp}\n"
        return desc
    

class Packet_Waveform_Meta(PacketBase):
    @property
    def desc(self):
        return  "Raw Waveform Meta"

    def set_packets(self, packets):
        self.packets = packets
        self._read()
        for i,p in enumerate(self.packets):
            if p is not None:
                p.timestamp = self.timestamp
                p.meta = self

    def _read(self):
        if self._is_read:
            return
        super()._read()
        self.copy_attrs(pystruct.waveform_metadata.from_buffer_copy(self._blob))
        self.is_read=True


