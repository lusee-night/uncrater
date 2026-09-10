from .PacketBase import PacketBase
from .utils import Time2Time, process_ADC_stats, process_telemetry
import struct
import numpy as np


class Packet_Housekeep(PacketBase):
    valid_types = set([0,1,2,3,100,101])

    @property
    def desc(self):
        return "Housekeeping"

    def _read(self):
        if self._is_read:
            return
        # Reported 0x306 has two ABIs, selected from packet evidence before decoding
        ps = self.schema.pystruct
        temp = self._decode_prefix_struct(ps.housekeeping_data_base)
        if temp is None:
            return

        hk_type = temp.housekeeping_type
        version = temp.version
        unique_packet_id = temp.unique_packet_id
        errors = temp.errors
        if not self._check_declared_version(version):
            return

        if hk_type not in self.valid_types:
            self._fail(
                "unsupported_format",
                f"housekeeping type {hk_type} is not recognized",
            )
            return
        struct_type = getattr(ps, f"housekeeping_data_{hk_type}", None)
        if struct_type is None:
            self._fail(
                "unsupported_format",
                f"housekeeping type {hk_type} is unavailable in binding {self.schema.binding_key}",
            )
            return
        attrs = self._decode_struct(struct_type)
        if attrs is None:
            return

        gains = None
        if hk_type == 1:
            gains = []
            for value in attrs.actual_gain:
                if value >= 3:
                    self._fail(
                        "payload_decode_failed",
                        f"invalid actual gain value {value}",
                    )
                    return
                gains.append("LMH"[value])

        # Common decoding handles every valid type; the branches below add derived fields for 0-2
        self.copy_attrs(attrs)
        self.time = 0
        self.hk_type = hk_type
        self.version = version
        self.unique_packet_id = unique_packet_id
        self.errors = errors

        if hk_type == 0:
            self.time = Time2Time(
                self.core_state.base.time_32, self.core_state.base.time_16
            )
            self._set_adc_stats(self.core_state.base.ADC_stat)
            self._set_telemetry(self.core_state.base.TVS_sensors)
        elif hk_type == 1:
            self._set_adc_stats(self.ADC_stat)
            self.actual_gain = gains
        elif hk_type == 2:
            self.ok = (self.heartbeat.magic == b'BRNMRL')
            if not self.ok:
                self._issue("invalid_magic", "housekeeping heartbeat magic does not match BRNMRL")
            self.time = Time2Time(self.heartbeat.time_32, self.heartbeat.time_16)
            self._set_telemetry(self.heartbeat.TVS_sensors)

        self._is_read = True

    def _set_adc_stats(self, stats):
        for k, v in process_ADC_stats(stats).items():
            setattr(self, k, v)
            setattr(self, "adc_" + k, v)

    def _set_telemetry(self, sensors):
        self.telemetry = process_telemetry(sensors)
        for k, v in self.telemetry.items():
            setattr(self, "telemetry_" + k, v)

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
