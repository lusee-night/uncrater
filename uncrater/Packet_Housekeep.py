from .Packet import Packet
import struct
import numpy as np
from .c2python import c2py

class Packet_Housekeep(Packet):
    @property
    def desc(self):
        return  "Housekeeping"

    def _read(self):
        super()._read()
        fmt = "<H I H"
        cs,ce = 0,struct.calcsize(fmt)
        self.version, self.packet_id, self.hk_type = struct.unpack(fmt, self.blob[cs:ce])
        if self.hk_type == 1:
            res = c2py('housekeeping_data_1', self.blob)
            self.min = np.array([x.min-0x1fff for x in res.ADC_stat])
            self.max = np.array([x.max-0x1fff for x in res.ADC_stat])
            self.valid_count = np.array([x.valid_count for x in res.ADC_stat])
            self.invalid_count_max = np.array([x.invalid_count_max for x in res.ADC_stat])
            self.invalid_count_min = np.array([x.invalid_count_min for x in res.ADC_stat])
            sumx = np.array([x.sumv for x in res.ADC_stat])
            sumxx = np.array([x.sumv2 for x in res.ADC_stat])
            print (sumx, sumxx)
            self.adc_mean = sumx/self.valid_count-0x1fff
            self.adc_var = sumxx/self.valid_count-(sumx/self.valid_count)**2
            self.adc_mean[self.valid_count == 0] = 0 
            self.adc_var[self.valid_count ==0 ] = 0
            self.adc_rms = np.sqrt(self.adc_var)
            self.version = res.version
            print ("I am here", self.min)
    
    
    def info (self):
        self._read()
        
        desc = f"House Packet Type {self.hk_type}\n"
        desc += f"Version : {self.version}\n"
        desc += f"packet_id : {self.packet_id}\n"
        if self.hk_type == 0:
            desc += f"TBC"
        elif self.hk_type == 1:
            desc += f"adc_min : {self.min}\n"            
            desc += f"adc_max : {self.max}\n"            
            desc += f"valid_count : {self.valid_count}\n"            
            desc += f"invalid_count_max : {self.invalid_count_max}\n"            
            desc += f"invalid_count_min : {self.invalid_count_min}\n"            
            desc += f"adc_mean : {self.adc_mean}\n"            
            desc += f"adc_rms : {self.adc_rms}\n"            
        return desc
    
