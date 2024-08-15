from .PacketBase import PacketBase,  copy_attrs, pystruct
from .utils import Time2Time
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



class Packet_Metadata(PacketBase):
    @property
    def desc(self):
        return  "Data Product Metadata"

    def _read(self):
        super()._read()
        # TODO: check if this actually works
        copy_attrs(pystruct.meta_data.from_buffer_copy(self._blob), self)
        self.format = self.seq.format
        self.time = Time2Time(self.base.time_32, self.base.time_16)
        self.errormask = self.base.errors

    def info (self):
        self._read()
        desc = ""
        desc += f"Version : {self.version}\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"Errormask: {self.errormask}\n"  
        desc += f"Time: {self.time}\n"
        desc += f"Current weight: {self.base.weight_current}\n"
        desc += f"Previous weight: {self.base.weight_previous}\n"
        return desc

class Packet_Spectrum(PacketBase):
    
    
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

    def set_meta(self, meta):
        self.meta = meta
        
    def _read(self):
        if hasattr(self, '_data'):
            return
        self.error_packed_id_mismatch = False
        self.error_data_read = False
        self.error_crc_mismatch = False
        if not hasattr(self, 'meta'):
            print ("Loading packet without metadata!")
            self.packed_id_mismatch=True
            
        
        if self.appid>=id.AppID_SpectraHigh and self.appid<id.AppID_SpectraHigh+16:
            self.priority = 1
            self.product = self.appid - id.AppID_SpectraHigh
        elif self.appid>=id.AppID_SpectraMed and self.appid<id.AppID_SpectraMed+16:
            self.priority = 2
            self.product = self.appid - id.AppID_SpectraMed
        else:
            assert (self.appid >= id.AppID_SpectraLow and self.appid < id.AppID_SpectraLow + 16)
            self.priority = 3
            self.product = self.appid - id.AppID_SpectraLow
        super()._read()
        self.unique_packet_id, self.crc = struct.unpack('<II', self._blob[:8])
        if self.meta.unique_packet_id != self.unique_packet_id:
            print ("Packet ID mismatch!!")
            self.packed_id_mismatch=True
        
        
        if self.meta.format==0 and len(self._blob[8:])//4>2048:
            print ("Spurious data, trimming!!!")
            self._blob = self._blob[:8 + 2048 * 4]
            
        calculated_crc = binascii.crc32(self._blob[8:]) & 0xffffffff
        self.error_crc_mismatch = not(self.crc == calculated_crc)
        if self.error_crc_mismatch:
            print (f"CRC: {self.crc:x} {calculated_crc:x}")
            print ("WARNING CRC mismatch!!!!!")        
            try:
                Ndata= len(self._blob[8:])//4
                data = struct.unpack(f'<{Ndata}i', self._blob[8:])
                print (data,Ndata)
                
            except:
                pass

        if self.meta.format==0:
            Ndata= len(self._blob[8:])//4
            try:
                data = struct.unpack(f'<{Ndata}i', self._blob[8:])
            except:
                self.error_data_read=True
                data = np.zeros(Ndata)
        else:
            raise NotImplementedError("Only format 0 is supported")
        self._data = np.array(data, dtype=np.int32).astype(np.float32)
        


    def info (self):
        self._read()
        desc = ""
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"crc : {self.crc}\n" 
        desc += f"Npoints: {len(self.data)}\n"  
        return desc
