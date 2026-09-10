from tracemalloc import stop
from .PacketBase import PacketBase
from .utils import Time2Time, cordic2rad, rle_decode
import struct, ctypes
import numpy as np


class Packet_Cal_Metadata(PacketBase):
    @property
    def desc(self):
        return "Calibrator Metadata"

    def _read(self):
        if self._is_read:
            return
        temp = self._decode_struct(self.schema.pystruct.calibrator_metadata)
        if temp is None:
            return
        if not self._check_declared_version(temp.version):
            return
        drift_raw = np.array(temp.drift).astype(np.int64)
        if hasattr(temp, "drift_shift"):
            drift_shift = temp.drift_shift
            if not 0 <= drift_shift <= 16:
                self._fail(
                    "payload_decode_failed",
                    f"invalid calibrator drift shift {drift_shift}",
                )
                return
            drift_raw = np.repeat(drift_raw << drift_shift, 8)
        self.copy_attrs(temp)
        self.time = Time2Time(self.time_32, self.time_16)
        self.drift_raw = drift_raw
        self.drift = cordic2rad(drift_raw)
        self.from_debug=False
        self._is_read = True

    def info(self):
        self._read()
        desc = " Calibrator Metadata\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"Time: {self.time}\n"
        return desc





## Obsolete at this point, but might return
class Packet_Cal_RegisterDump(PacketBase):
    @property
    def desc(self):
        return "Calibrator RegisterDump"

    def _read(self):
        if self._is_read:
            return
        if not self._validate_length(12 + 498 * 4, allow_cdi_padding=False):
            return
        self.unique_packet_id, time_32, time_16 = struct.unpack_from("<III", self._blob)
        self.time = Time2Time(time_32, time_16)
        self.registers = struct.unpack_from("<498I", self._blob, 12)
        self.reset = self.registers[0x00]
        self.Nac1 = self.registers[0x01]
        self.Nac2 = self.registers[0x02]
        self.notch_index = self.registers[0x03]
        self.cplx_index = self.registers[0x04]
        self.sum1_index = self.registers[0x05]
        self.sum2_index = self.registers[0x06]
        self.power_top_index = self.registers[0x07]
        self.power_bot_index = self.registers[0x08]
        self.drift_fd_index = self.registers[0x09]
        self.drift_sd1_index = self.registers[0x0A]
        self.drift_sd2_index = self.registers[0x0B]
        self.default_drift = cordic2rad(self.registers[0x0C])
        self.have_lock_value = self.registers[0x0D]
        self.have_lock_radian = cordic2rad(self.registers[0x0E])
        self.lower_guard_value = cordic2rad(self.registers[0x0F])
        self.upper_guard_value = cordic2rad(self.registers[0x10])
        self.power_ratio = self.registers[0x11]
        self.antenna_enable = self.registers[0x12]
        self.error_stick = self.registers[0x13]
        self.cf_enable = self.registers[0x14]
        self.cf_tst_mode_en = self.registers[0x15]
        self.cf_start_addr = self.registers[0x16]
        self.cf_mem_busy = self.registers[0x17]
        self.cf_data_ready = self.registers[0x18]
        self.cf_drop_err = self.registers[0x19]
        self.cf_timestamp_lower = self.registers[0x1A]
        self.cf_timestamp_upper = self.registers[0x1B]
        self.phaser_err = self.registers[0x1C:0x24]
        self.averager_err_cnt = self.registers[0x24:0x34]
        self.process_err_cnt = self.registers[0x34:0x3C]
        self.enable = self.registers[0x3C]
        self.power_index = self.registers[0x3D]
        self.fd_sd_index = self.registers[0x3E]
        self.fdx_sdx_index = self.registers[0x3F]
        self.hold_drift = self.registers[0x40]
        self.sum0_shift_index = self.registers[0x41]
        self.snron = self.registers[0x42]
        self.snroff = self.registers[0x43]
        self.nsettle = self.registers[0x44]
        self.delta_drift_cor_a = self.registers[0x45]
        self.delta_drift_cor_b = self.registers[0x46]
        self.readout_mode = self.registers[0x4D]
        self.freq_bin = self.registers[0x4F]
        self.weights = np.array(self.registers[0x50:0x50+410])
        self.stage3_err_cnt = self.registers[0x1EB]
        self.prod_index = self.registers[0x1F0]
        self.prod_index2 = self.registers[0x1F1]
        self._is_read = True

    def info(self):
        self._read()
        desc = " Calibrator Metadata\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"Time: {self.time}\n"
        desc += f"Readout mode:" + str(self.readout_mode) + "\n"
        return desc

class Packet_Cal_Data(PacketBase):
    @property
    def desc(self):
        return "Calibrator Data"

    def set_meta_id(self, id):
        self.expected_id = id

    def _read(self):
        if self._is_read:
            return
        self.data_page = self.appid - self.schema.appids.AppID_Calibrator_Data
        if self.data_page > 0 and not hasattr(self, "expected_id"):
            self._fail("orphan_multipart_page", "calibrator continuation has no start page")
            return
        expected_size = (8204, 8204, 4112)[self.data_page]
        if not self._validate_length(expected_size, allow_cdi_padding=False):
            return
        self.unique_packet_id, time_32, time_16 = struct.unpack_from("<III", self._blob)
        self.time = Time2Time(time_32, time_16)
        if self.data_page > 0 and self.expected_id != self.unique_packet_id:
            self._issue(
                "unique_packet_id_mismatch",
                f"packet UID {self.unique_packet_id} does not match multipart UID {self.expected_id}",
                details={"expected_uid": self.expected_id,
                         "packet_uid": self.unique_packet_id},
            )

        data = np.frombuffer(self._blob, dtype="<i4", offset=12)
        if self.data_page < 2:
            self.data = data.copy().reshape(4,512)
        else:
            self.gNacc = int(data[0])
            self.gphase = data[1:].copy()
            self.data = (self.gNacc, self.gphase)

        self._is_read = True

    def info(self):
        self._read()
        desc = " Calibrator Data\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"gNacc: {self.gNacc}\n"
        desc += f"gphase: {self.gphase}\n"
        return desc

class Packet_Cal_RawPFB(PacketBase):
    @property
    def desc(self):
        return "Calibrator Raw PFB"

    def set_meta_id(self, id):
        self.expected_id = id

    def _read(self):
        if self._is_read:
            return
        page = self.appid - self.schema.appids.AppID_Calibrator_RawPFB
        self.channel = page//2
        self.part = page%2
        if page > 0 and not hasattr(self, "expected_id"):
            self._fail("orphan_multipart_page", "raw-PFB continuation has no start page")
            return
        if not self._validate_length(8204, allow_cdi_padding=False):
            return
        self.unique_packet_id, time_32, time_16 = struct.unpack_from("<III", self._blob)
        self.time = Time2Time(time_32, time_16)

        if page > 0 and self.expected_id != self.unique_packet_id:
            self._issue(
                "unique_packet_id_mismatch",
                f"packet UID {self.unique_packet_id} does not match multipart UID {self.expected_id}",
                details={"expected_uid": self.expected_id,
                         "packet_uid": self.unique_packet_id},
            )

        self.data = np.frombuffer(self._blob, dtype="<i4", offset=12,
                                  count=2048).copy()
        self._is_read = True

    def info(self):
        self._read()
        desc = " Calibrator Raw PFB\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        return desc





class Packet_Cal_Debug(PacketBase):
    @property
    def desc(self):
        return "Calibrator Debug"

    def set_meta_id(self, id):
        self.expected_id = id

    def _read(self):
        if self._is_read:
            return
        self.debug_page = self.appid - self.schema.appids.AppID_Calibrator_Debug
        if self.debug_page > 0 and not hasattr(self, "expected_id"):
            self._fail("orphan_multipart_page", "calibrator debug continuation has no start page")
            return
        if not self._validate_min_length(12):
            return
        self.unique_packet_id, time_32, time_16 = struct.unpack_from("<III", self._blob)
        self.time = Time2Time(time_32, time_16)

        if self.debug_page > 0 and self.unique_packet_id != self.expected_id:
            self._issue(
                "unique_packet_id_mismatch",
                f"packet UID {self.unique_packet_id} does not match multipart UID {self.expected_id}",
                details={"expected_uid": self.expected_id,
                         "packet_uid": self.unique_packet_id},
            )

        payload = self._decode_debug_payload(self._blob[12:])
        if payload is None:
            return

        datai = np.array(struct.unpack(f"<{len(payload)//4}i", payload)).reshape(3,1024)
        datau = np.array(struct.unpack(f"<{len(payload)//4}I", payload)).reshape(3,1024)
        dataw = np.array(struct.unpack(f"<{len(payload)//2}H", payload)).reshape(6,1024)

        # the reason we do it this way is because some numbers are unsigned and some are signed
        # now based on page we interpret it right
        if self.debug_page == 0:
            metadata_type = self.schema.pystruct.calibrator_metadata
            metadata_size = ctypes.sizeof(metadata_type)
            metadata = metadata_type.from_buffer_copy(payload[2*1024:2*1024+metadata_size])
            if not self._check_declared_version(metadata.version):
                return
            self.have_lock = dataw[0] & 0xFF
            self.lock_ant = (dataw[0] >> 8) & 0xFF
            ## the actual metadata packet that would come is hidden in here
            metadata.unique_packet_id = self.unique_packet_id
            metadata.time = Time2Time(metadata.time_32, metadata.time_16)
            # Keep the old underscored marker while publishing the canonical flag
            metadata._from_debug = True
            metadata.from_debug = True
            self.metadata = metadata
            self.drift = cordic2rad(datau[1])
            self.powertop0 = datau[2]
        elif self.debug_page == 1:
            self.powertop1 = datau[0]
            self.powertop2 = datau[1]
            self.powertop3 = datau[2]
        elif self.debug_page == 2:
            self.powerbot0 = datau[0]
            self.powerbot1 = datau[1]
            self.powerbot2 = datau[2]
        elif self.debug_page == 3:
            self.powerbot3 = datau[0]
            self.fd0 = datai[1]
            self.fd1 = datai[2]
        elif self.debug_page == 4:
            self.fd2 = datai[0]
            self.fd3 = datai[1]
            self.sd0 = datai[2]
        elif self.debug_page == 5:
            self.sd1 = datai[0]
            self.sd2 = datai[1]
            self.sd3 = datai[2]
        elif self.debug_page == 6:
            self.fdx = datai[0]
            self.sdx = datai[1]
            # snr fields are in Q16.4 format
            self.snr0 = (datau[2] / 16.0)
        elif self.debug_page == 7:
            self.snr1 = (datau[0] / 16.0)
            self.snr2 = (datau[1] / 16.0)
            self.snr3 = (datau[2] / 16.0)
        self._is_read = True

    def _decode_debug_payload(self, encoded):
        expected = 3*1024*4
        if len(encoded) == expected:
            return encoded
        if len(encoded) > expected:
            self._fail(
                "bad_blob_length",
                f"debug payload exceeds {expected} bytes",
                details={"actual": len(encoded), "maximum": expected},
            )
            return None

        # CDI does not retain the compressed length before its 0-3 padding bytes.
        # Accept only one exact-size decode so padding cannot become payload data.
        padding_options = range(4) if len(encoded)%4 == 0 else (0,)
        candidates = []
        for padding in padding_options:
            candidate = encoded if padding == 0 else encoded[:-padding]
            try:
                decoded = rle_decode(candidate, original_size=expected)
            except ValueError:
                continue
            if len(decoded) == expected:
                candidates.append(decoded)
        if len(candidates) != 1:
            self._fail(
                "payload_decode_failed",
                f"debug RLE produced {len(candidates)} exact-size candidates",
            )
            return None
        return candidates[0]

    def info(self):
        self._read()
        desc = " Calibrator Debug\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        return desc


class Packet_Cal_ZoomSpectra(PacketBase):
    @property
    def desc(self):
        return "Calibrator Zoom Data"

    def _read(self):
        if self._is_read:
            return

        fft_size = 64
        # ch1 autocorr + ch2 autocorr + ch12 corr real/imaginary parts = 4 arrays in total
        total_entries = fft_size * 4  ## 6 bytes for header
        if not self._validate_length(6 + total_entries * 4):
            return
        self.unique_packet_id, self.pfb_bin = struct.unpack_from("<IH", self._blob)
        data = np.frombuffer(self._blob, dtype="<f4", offset=6,
                             count=total_entries).copy()

        self.AA = data[0:fft_size]
        self.BB = data[fft_size:2*fft_size]
        self.ABR = data[2*fft_size:3*fft_size]
        self.ABI = data[3*fft_size:]

        self._is_read = True

    def info(self):
        self._read()
        desc = " Calibrator Zoom Spectra\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        return desc
