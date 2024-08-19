from .PacketBase import PacketBase, pystruct
from .PacketBase import PacketBase
from .utils import Time2Time

import struct
class Packet_Heartbeat(PacketBase):
    @property
    def desc(self):
        return  "Heartbeat"

    def _read(self):
        super()._read()
        temp = pystruct.heartbeat.from_buffer_copy(self._blob)       
        self.copy_attrs(temp)
        self.ok = (self.magic == b'BRNMRL')
        self.time = Time2Time(self.time_32, self.time_16)
        self.payload['ok'] = self.ok
        self.payload['time'] = self.time
        self._read = True

    def info (self):
        self._read()
        ok = "OK" if self.ok else "BAD"
        desc = "Heartbeat Packet\n"
        desc += f"Magic : {ok}\n"
        desc += f"Count : {self.packet_count}\n"
        return desc
