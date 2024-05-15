from .Packet import Packet
import struct
import numpy as np

class Packet_Housekeep(Packet):
    @property
    def desc(self):
        return  "Housekeeping"

    def _read(self):
        super()._read()
        fmt = "<H I H"
        cs,ce = 0,struct.calcsize(fmt)
        self.version, self.packet_id, self.hk_type = struct.unpack(fmt, self.blob[cs:ce])
        fmt = "<"+("h h I I I i Q"*4)         
        cs,ce = ce, ce + struct.calcsize(fmt)
        values = struct.unpack(fmt, self.blob[cs:ce])
        self.adc_min = np.array(values[0::7])
        self.adc_max = np.array(values[1::7])
        self.valid_count = np.array(values[2::7])
        self.invalid_count_max = np.array(values[3::7])
        self.invalid_count_min = np.array(values[4::7])
        self.adc_mean = np.array(values[5::7])
        self.adc_rms = np.sqrt(np.array(values[6::7]))
        fmt = "B B B B"
        cs = ce
        values = struct.unpack(fmt,self.blob[cs:cs+4])
        self.actual_gain = ["LMH"[i] for i in values]
        
        
    
    def info (self):
        self._read()
        
        desc = "House Packet Type {self.hk_type}\n"
        desc += f"Version : {self.version}\n"
        desc += f"packet_id : {self.packet_id}\n"
        if self.hk_type == 0:
            desc += f"TBC"
        elif self.hk_type == 1:
            desc += f"adc_min : {self.adc_min}\n"            
            desc += f"adc_max : {self.adc_max}\n"            
            desc += f"valid_count : {self.valid_count}\n"            
            desc += f"invalid_count_max : {self.invalid_count_max}\n"            
            desc += f"invalid_count_min : {self.invalid_count_min}\n"            
            desc += f"adc_mean : {self.adc_mean}\n"            
            desc += f"adc_rms : {self.adc_rms}\n"            
        return desc
    