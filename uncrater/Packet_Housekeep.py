from .PacketBase import PacketBase, pystruct
from .utils import Time2Time, process_ADC_stats
import struct
import numpy as np





class Packet_Housekeep(PacketBase):
    valid_types = set(range(2))
    
    @property
    def desc(self):
        return  "Housekeeping"

    # TODO: fix the housekeeping type logic
    def _read(self):
        if self._is_read:
            return
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
            adc=process_ADC_stats(self.ADC_stat)
            for k,v in adc.items():
                setattr(self, k, v)
            self.version = self.version
            self.error_mask = self.errors
            self.actual_gain = ["LMHD"[i] for i in self.actual_gain]

        elif temp.housekeeping_type == 0:
            self.copy_attrs(pystruct.housekeeping_data_0.from_buffer_copy(self._blob))
            self.time  = Time2Time(self.core_state.base.time_32, self.core_state.base.time_16)
    
        self._is_read=True

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
    
