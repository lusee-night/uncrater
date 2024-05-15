from .Packet import Packet

class Packet_Heartbeat(Packet):
    @property
    def desc(self):
        return  "Hearbeat"

    def info (self):
        self._read()
        ok = "OK" if (self.blob == b'BRNMRL') else "BAD"
        desc = "Heartbeat Packet\n"
        desc += f"Magic : {ok}\n"
        return desc