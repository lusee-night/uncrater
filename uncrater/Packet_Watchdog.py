import struct
from .PacketBase import PacketBase, pystruct
from .utils import Time2Time, process_telemetry

class Packet_Watchdog(PacketBase):
    @property
    def desc(self):
        return "Watchdog Packet"

    def _read(self):
        if self._is_read:
            return
        super()._read()

        # Unpack: uint32, uint64, uint8 (little-endian assumed)
        self.unique_packet_id, self.uC_time, self.tripped = struct.unpack_from("<IQB", self._blob)

        self.time = Time2Time(self.uC_time)
        self._is_read = True

    def info(self):
        self._read()
        desc = "Watchdog Packet\n"
        desc += f"Unique Packet ID  : {self.unique_packet_id}\n"
        desc += f"uC Time           : {self.uC_time}\n"
        desc += f"Tripped           : {self.tripped}\n"
        return desc

