from .PacketBase import PacketBase
import struct
class Packet_Heartbeat(PacketBase):
    @property
    def desc(self):
        return  "Heartbeat"

    def _read(self):
        super()._read()
        self.count = struct.unpack("<I", self.blob[:4])[0]
        self.ok = (self.blob[4:8] == b'BRRL')
        self._read = True

    def info (self):
        self._read()
        ok = "OK" if self.ok else "BAD"
        desc = "Heartbeat Packet\n"
        desc += f"Magic : {ok}\n"
        desc += f"Count : {self.count}\n"
        return desc
