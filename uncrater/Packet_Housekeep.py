from .PacketBase import PacketBase, pystruct, pystruct_203, pystruct_305, pystruct_307
from .utils import Time2Time, process_ADC_stats, process_telemetry
import struct
import numpy as np


class Packet_Housekeep(PacketBase):
    valid_types = set([0,1,2,3,100,101])

    @property
    def desc(self):
        return "Housekeeping"

    # TODO: fix the housekeeping type logic
    def _read(self):
        if self._is_read:
            return
        super()._read()
        # fmt = "<H I I H"
        # cs,ce = 0,struct.calcsize(fmt)
        # self.version, self.unique_packet_id, self.errors, self.housekeeping_type = struct.unpack(fmt, self.blob[cs:ce])
        
        # Select the appropriate pystruct based on version
        if self._version==0x203:
            ps = pystruct_203
        elif self._version==0x305:
            ps = pystruct_305
        elif self._version==0x307:
            ps = pystruct_307
        else:
            ps = pystruct
            
        temp = ps.housekeeping_data_base.from_buffer_copy(self._blob)
        self.time = 0
        self.hk_type = temp.housekeeping_type
        self.version = temp.version
        self.unique_packet_id = temp.unique_packet_id
        self.errors = temp.errors
        if self.version != ps.VERSION_ID:
            print("WARNING: Version ID mismatch")

        if temp.housekeeping_type not in self.valid_types:
            print("HK type = ", temp.housekeeping_type)
            print("HK type not recognized, corrupter HK packet?")


        if temp.housekeeping_type == 0:
            self.copy_attrs(ps.housekeeping_data_0.from_buffer_copy(self._blob))
            self.time = Time2Time(
                self.core_state.base.time_32, self.core_state.base.time_16
            )
            adc = process_ADC_stats(self.core_state.base.ADC_stat)
            for k, v in adc.items():
                setattr(self, k, v)
            telemetry = process_telemetry(self.core_state.base.TVS_sensors)
            for k, v in telemetry.items():
                setattr(self, "telemetry_" + k, v)
        elif temp.housekeeping_type == 1:
            self.copy_attrs(ps.housekeeping_data_1.from_buffer_copy(self._blob))
            adc = process_ADC_stats(self.ADC_stat)
            for k, v in adc.items():
                setattr(self, k, v)
            self.actual_gain = ["LMH"[i] for i in self.actual_gain]
        elif temp.housekeeping_type == 2:
            self.copy_attrs(ps.housekeeping_data_2.from_buffer_copy(self._blob))
            self.ok = (self.heartbeat.magic == b'BRNMRL')
            self.time = Time2Time(self.heartbeat.time_32, self.heartbeat.time_16)
            self.telemetry = process_telemetry(self.heartbeat.TVS_sensors)

        elif temp.housekeeping_type == 3:
            self.copy_attrs(ps.housekeeping_data_3.from_buffer_copy(self._blob))

        elif temp.housekeeping_type == 100:
            self.copy_attrs(ps.housekeeping_data_100.from_buffer_copy(self._blob))
        elif temp.housekeeping_type == 101:
            self.copy_attrs(ps.housekeeping_data_101.from_buffer_copy(self._blob))
        
        self._is_read = True

    def info(self):
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
