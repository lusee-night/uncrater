from .Packet import Packet
import struct

class Packet_Hello(Packet):
    @property
    def desc(self):
        return  "Hello!!"

    def _read(self):
        super()._read()
        fmt = "<H I I H"
        if len(self.blob) != struct.calcsize(fmt):
            raise ValueError("Incorrect metadata size")
        values = struct.unpack(fmt, self.blob)
        self.version, self.packet_id, self.time_sec, self.time_subsec = values
    
    def info (self):
        self._read()
        
        desc = "Hello Packet\n"
        desc += f"Version : {self.version}\n"
        desc += f"packet_id : {self.packet_id}\n"
        desc += f"time_sec : {self.time_sec}\n"
        desc += f"time_subsec : {self.time_subsec}\n"
         
        return desc
    