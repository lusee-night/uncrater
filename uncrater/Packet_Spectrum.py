from .Packet import Packet
import struct
import numpy as np
import binascii
from .c2python import c2py

class Packet_Metadata(Packet):
    @property
    def desc(self):
        return  "Data Product Metadata"

    def _read(self):
        super()._read()
        res = c2py('meta_data', self.blob)
        self.version = res.version
        self.packet_id = res.unique_packet_id
        self.format = res.seq.format
        self.time_seconds = res.base.time_seconds

    def info (self):
        self._read()
        desc = ""
        desc += f"Version : {self.version}\n"
        desc += f"packet_id : {self.packet_id}\n"
        return desc

class Packet_Spectrum(Packet):
    
    def set_expected(self, format, expected_packet_id):
        self.expected_packet_id = expected_packet_id
        self.format = format
        
    
    @property
    def desc(self):
        return  "Data Product Metadata"

    @property
    def power(self):
        self._read()
        return self.data
    
    def _read(self):
        if hasattr(self, 'spectrum'):
            return
        super()._read()
        self.packet_id, self.crc = struct.unpack('<II', self.blob[:8])
        if self.expected_packet_id != self.packet_id:
            raise ValueError("Packet ID mismatch")
        calculated_crc = binascii.crc32(self.blob[8:]) & 0xffffffff
        if self.crc != calculated_crc:
            raise ValueError("CRC mismatch")
        if self.format==0:
            Ndata= len(self.blob[8:])//4
            data = struct.unpack(f'<{Ndata}i', self.blob[8:])
        else:
            raise NotImplementedError("Only format 0 is supported")
        self.data = np.array(data, dtype=np.int32).astype(np.float32)


    def info (self):
        self._read()
        desc = ""
        desc += f"packet_id : {self.packet_id}\n"
        desc += f"crc : {self.crc}\n" 
        desc += f"Npoints: {len(self.data)}\n"  
        return desc
