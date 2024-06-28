from .Packet import Packet
import struct
import numpy as np
from .c2python import c2py, copy_attrs
from .core_loop import housekeeping_data_base, housekeeping_data_0, housekeeping_data_1

class Packet_Housekeep(Packet):
    @property
    def desc(self):
        return  "Housekeeping"

    def _read(self):
        super()._read()
        # fmt = "<H I I H"
        # cs,ce = 0,struct.calcsize(fmt)
        # self.version, self.unique_packet_id, self.errors, self.housekeeping_type = struct.unpack(fmt, self.blob[cs:ce])
        temp = housekeeping_data_base.from_buffer_copy(self.blob)
        if temp.housekeeping_type == 1:
            copy_attrs(housekeeping_data_1.from_buffer_copy(self.blob), self)
            self.min = np.array([x.min-0x1fff for x in self.ADC_stat])
            self.max = np.array([x.max-0x1fff for x in self.ADC_stat])
            self.valid_count = np.array([x.valid_count for x in self.ADC_stat])
            self.invalid_count_max = np.array([x.invalid_count_max for x in self.ADC_stat])
            self.invalid_count_min = np.array([x.invalid_count_min for x in self.ADC_stat])
            sumx = np.array([x.sumv for x in self.ADC_stat])
            sumxx = np.array([x.sumv2 for x in self.ADC_stat])
            self.mean = sumx/self.valid_count-0x1fff
            self.var = sumxx/self.valid_count-(sumx/self.valid_count)**2
            self.mean[self.valid_count == 0] = 0 
            self.var[self.valid_count ==0 ] = 0
            self.total_count = self.valid_count+self.invalid_count_min+self.invalid_count_max
            self.rms = np.sqrt(self.var)
            self.version = self.version
            self.error_mask = self.errors
            self.actual_gain = ["LMHD"[i] for i in self.actual_gain]
        elif temp.housekeeping_type == 0:
            copy_attrs(housekeeping_data_0.from_buffer_copy(self.blob), self)

    def info (self):
        self._read()
        
        desc = f"House Packet Type {self.housekeeping_type}\n"
        desc += f"Version : {self.version}\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"error_mask: {self.errors}\n"
        if self.housekeeping_type == 0:
            desc += f"TBC"
        elif self.housekeeping_type == 1:
            desc += f"adc_min : {self.min}\n"            
            desc += f"adc_max : {self.max}\n"            
            desc += f"valid_count : {self.valid_count}\n"            
            desc += f"invalid_count_max : {self.invalid_count_max}\n"            
            desc += f"invalid_count_min : {self.invalid_count_min}\n"  
            desc += f"total_count : {self.total_count}\n"                        
            desc += f"adc_mean : {self.mean}\n"            
            desc += f"adc_rms : {self.rms}\n"            
        return desc
    
