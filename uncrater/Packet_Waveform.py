from .PacketBase import PacketBase
from .utils import Time2Time
import struct
import numpy as np



class Packet_Waveform(PacketBase):
    @property
    def desc(self):
        return  "Raw Waveform"

    def _read(self):
        if self._is_read:
            return
        if not self._validate_length(2 * 16384, allow_cdi_padding=False):
            return
        ch = self.appid - self.schema.appids.AppID_RawADC
        waveform = np.frombuffer(self._blob, dtype="<u2", count=16384).astype(np.int32)
        # Coreloop encodes negative samples as 16384 + value, including -8192 as code 8192
        waveform[waveform>=8192] -= 16384
        self.waveform = waveform.astype(np.int16)
        self.ch = ch
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
        if any(issue.fatal for issue in self.decode_status.issues):
            return
        # Coreloop emits metadata after waveforms, so it annotates packets already decoded
        for p in self.packets:
            if p is not None:
                p.timestamp = self.timestamp
                p.meta = self

    def _read(self):
        if self._is_read:
            return
        attrs = self._decode_struct(self.schema.pystruct.waveform_metadata)
        if attrs is None:
            return
        self.copy_attrs(attrs)
        self.time = Time2Time(self.time_32, self.time_16)
        self._is_read = True
