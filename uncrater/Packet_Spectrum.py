from .Packet import Packet,  copy_attrs, pystruct
import os, sys
import struct
import numpy as np
import binascii

if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

# now try to import pycoreloop
try:
    from pycoreloop import appId as id
except ImportError:
    print ("Can't import pycoreloop\n")
    print ("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo.")
    sys.exit(1)



class Packet_Metadata(Packet):
    @property
    def desc(self):
        return  "Data Product Metadata"

    def _read(self):
        super()._read()
        # TODO: check if this actually works
        copy_attrs(struct.meta_data.from_buffer_copy(self.blob), self)
        self.format = self.seq.format
        self.time_seconds = self.base.time_seconds
        self.errormask = self.base.errors

    def info (self):
        self._read()
        desc = ""
        desc += f"Version : {self.version}\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"Errormask: {self.errormask}\n"  
        return desc

class Packet_Spectrum(Packet):
    
    def set_expected(self, format, expected_packet_id):
        self.expected_packet_id = expected_packet_id
        self.format = format
        
    
    @property
    def desc(self):
        return  "Power Spectrum"
    
    @property
    def data(self):
        self._read()
        return self._data

    @property
    def power(self):
        self._read()
        return self.data
    
    def _read(self):
        if hasattr(self, '_data'):
            return
        if self.appid>=id.AppID_SpectraHigh and self.appid<id.AppID_SpectraHigh+16:
            self.priority = 1
        elif self.appid>=id.AppID_SpectraMed and self.appid<id.AppID_SpectraMed+16:
            self.priority = 2
        else:
            assert (self.appid>=id.AppID_SpectraLow and self.appid<id.AppID_SpectraLow+16)
            self.priority = 3
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
        self._data = np.array(data, dtype=np.int32).astype(np.float32)
        


    def info (self):
        self._read()
        desc = ""
        desc += f"packet_id : {self.packet_id}\n"
        desc += f"crc : {self.crc}\n" 
        desc += f"Npoints: {len(self.data)}\n"  
        return desc
