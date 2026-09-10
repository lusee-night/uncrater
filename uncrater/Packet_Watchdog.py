from .PacketBase import PacketBase
from .utils import Time2Time
import struct

class Packet_Watchdog(PacketBase):
    @property
    def desc(self):
        return "Watchdog Packet"

    def _read(self):
        if self._is_read:
            return
        temp = self._decode_struct(self.schema.pystruct.watchdog_packet)
        if temp is None:
            return
        self.copy_attrs(temp)
        self.time = Time2Time(self.uC_time & 0xFFFFFFFF, (self.uC_time >> 32) & 0xFFFF)
        self._is_read = True

    def info(self):
        self._read()
        desc = "Watchdog Packet\n"
        desc += f"Unique Packet ID  : {self.unique_packet_id}\n"
        desc += f"uC Time           : {self.uC_time}\n"
        desc += f"Tripped           : {self.tripped}\n"
        return desc
