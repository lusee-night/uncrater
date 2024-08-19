from .PacketBase import PacketBase, pystruct
from .utils import Time2Time
import struct
import numpy as np


class Packet_Housekeep(PacketBase):
    valid_types = set(range(2))
    
    @property
    def desc(self):
        return  "Housekeeping"

    # TODO: fix the housekeeping type logic
    def _read(self):
        super()._read()
        # fmt = "<H I I H"
        # cs,ce = 0,struct.calcsize(fmt)
        # self.version, self.unique_packet_id, self.errors, self.housekeeping_type = struct.unpack(fmt, self.blob[cs:ce])
        temp = pystruct.housekeeping_data_base.from_buffer_copy(self._blob)
        self.time = 0

        if temp.housekeeping_type not in self.valid_types:
            raise ValueError(f'{temp.housekeeping_type} is not a valid housekeeping type')
        if temp.housekeeping_type == 1:
            self.copy_attrs(pystruct.housekeeping_data_1.from_buffer_copy(self._blob))
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

            for n in ['min max valid_count invalid_count_max invalid_count_min total_count mean rms'.split()]:
                self.payload[n] = getattr(self,n)

        elif temp.housekeeping_type == 0:
            self.copy_attrs(pystruct.housekeeping_data_0.from_buffer_copy(self._blob))
            self.time  = Time2Time(self.core_state.base.time_32, self.core_state.base.time_16)
            self.payload['time'] = self.time

    def info (self):
        self._read()
        
        desc = f"House Packet Type {self.base.housekeeping_type}\n"
        desc += f"Version : {self.base.version}\n"
        desc += f"packet_id : {self.base.unique_packet_id}\n"
        desc += f"error_mask: {self.base.errors}\n"
        if self.base.housekeeping_type == 0:
            desc += f"TBC"
        elif self.base.housekeeping_type == 1:
            desc += f"adc_min : {self.min}\n"            
            desc += f"adc_max : {self.max}\n"            
            desc += f"valid_count : {self.valid_count}\n"            
            desc += f"invalid_count_max : {self.invalid_count_max}\n"            
            desc += f"invalid_count_min : {self.invalid_count_min}\n"  
            desc += f"total_count : {self.total_count}\n"                        
            desc += f"adc_mean : {self.mean}\n"            
            desc += f"adc_rms : {self.rms}\n"            
        return desc
    
