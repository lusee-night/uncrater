from tracemalloc import stop
from .PacketBase import PacketBase, pystruct
from .utils import Time2Time, cordic2rad
from pycoreloop import appId as id
import struct, ctypes
import numpy as np


class Packet_Cal_Metadata(PacketBase):
    @property
    def desc(self):
        return "Calibrator Metadata"

    def _read(self):
        if self._is_read:
            return
        super()._read()        
        temp = pystruct.calibrator_metadata.from_buffer_copy(self._blob)               
        self.copy_attrs(temp)
        self.time = Time2Time(self.time_32, self.time_16)
        self._is_read = True
        self.drift_raw = np.array(self.drift).astype(np.int64)
        self.drift_raw = (self.drift_raw << self.drift_shift)
        self.drift = cordic2rad(np.repeat(self.drift_raw,8))
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
        super()._read()        
        self.unique_packet_id = struct.unpack("<I", self._blob[0:4])[0]
        self.time = Time2Time(struct.unpack("<I", self._blob[4:8])[0], struct.unpack("<I", self._blob[8:12])[0])        
        self.registers = struct.unpack("<498I", self._blob[12:12+498*4])
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
        super()._read()
        self.unique_packet_id = struct.unpack("<I", self._blob[0:4])[0]
        self.time = Time2Time(struct.unpack("<I", self._blob[4:8])[0], struct.unpack("<I", self._blob[8:12])[0])  
        self.data_page = self.appid - id.AppID_Calibrator_Data
        if (self.data_page>0) and (self.expected_id != self.unique_packet_id):
            print("Packet ID mismatch!!")
            self.packed_id_mismatch = True


        data = struct.unpack(f"<{len(self._blob[12:])//4}i", self._blob[12:])
        if self.data_page < 2:
            assert(len(data) == 2048)
            
            self.data = np.array(data).reshape(4,512)
        else:
            self.gNacc = data[0]
            self.gphase = np.array(data[1:1025])
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
        super()._read()
        self.channel = (self.appid-id.AppID_Calibrator_RawPFB)//2
        self.part = (self.appid-id.AppID_Calibrator_RawPFB)%2
        self.unique_packet_id = struct.unpack("<I", self._blob[0:4])[0]
        self.time = Time2Time(struct.unpack("<I", self._blob[4:8])[0], struct.unpack("<I", self._blob[8:12])[0])  

        if (self.appid-id.AppID_Calibrator_RawPFB>0) and (self.expected_id != self.unique_packet_id):
            print("Packet ID mismatch!!")
            self.packed_id_mismatch = True

        self.data = struct.unpack(f"<{len(self._blob[12:])//4}i", self._blob[12:])
        self.data = self.data[:2048]
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
        super()._read()
        self.unique_packet_id = struct.unpack("<I", self._blob[0:4])[0]
        self.time = Time2Time(struct.unpack("<I", self._blob[4:8])[0], struct.unpack("<I", self._blob[8:12])[0])  

        payload = self._blob[12:]
        if len(payload)<3*1024*4:
            # let's to to RLE decode it
            def rle_decode (stream,  max_length = 12300, magic = 37):
                if len(stream) >= max_length:
                    return stream
                decoded = bytearray()
                i = 0
                while i < len(stream):
                    if stream[i] == magic:
                        
                        count = stream[i+1]
                        char = stream[i+2]
                        decoded.extend([char] * count)
                        i += 3
                    else:
                        decoded.append(stream[i])
                        i += 1
                return bytes(decoded)
                        
            payload = rle_decode(payload, magic=37, max_length = 3*1024*4)
            if len(payload)<3*1024*4 or len(payload)>3*1024*4+3:
                print (f"RLE decode failed, size = {len(payload)}")
                return
            payload = payload[:3*1024*4] # trim any extra bytes due to CDI padding
            


        self.debug_page = self.appid - id.AppID_Calibrator_Debug
        if (self.debug_page>0) and (self.unique_packet_id != self.expected_id):
            print("Packet ID mismatch!!")
            self.packed_id_mismatch = True
        
        if len(payload)!=3*1024*4:
            print (f"Bad packet size. size = {len(self.blob)} appid = {self.appid:x} page = {self.debug_page}")
            return

        datai = np.array(struct.unpack(f"<{len(payload)//4}i", payload)).reshape(3,1024)
        datau = np.array(struct.unpack(f"<{len(payload)//4}I", payload)).reshape(3,1024)
        dataw = np.array(struct.unpack(f"<{len(payload)//2}H", payload)).reshape(6,1024)

        # the reason we do it this way is because some numbers are unsigned and some are signed
        # now based on page we interpret it right
        if self.debug_page == 0:
            self.have_lock = dataw & 0xFF
            self.lock_ant = (dataw >> 8) & 0xFF
            self.errors = pystruct.calibrator_errors.from_buffer_copy(self._blob[12+2*1024:12+2*1024+ctypes.sizeof(pystruct.calibrator_errors)])
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
        super()._read()

        fft_size = 64
        # ch1 autocorr + ch2 autocorr + ch12 corr real/imaginary parts = 4 arrays in total
        total_entries = fft_size * 4  ## 6 bytes for header
        use_float = True
        self.unique_packet_id = struct.unpack("<I", self._blob[0:4])[0]
        self.pfb_bin = struct.unpack("<H", self._blob[4:6])[0]
        blob = self._blob[6:-2]  # last 2 bytes are padding to make it multiple of 4 bytes
        if len(blob) == total_entries * 4:
            if use_float:
                data = struct.unpack(f"<{total_entries}f", blob)
                dtype = np.float32
            else:
                data = struct.unpack(f"<{total_entries}i", blob)
                dtype = np.int32

            # we always use float32 in NumPy, dtype is just for conversion from raw byte array
            self.AA = np.array(data[0:fft_size], dtype=dtype).astype(np.float32)
            self.BB = np.array(data[fft_size:2*fft_size], dtype=dtype).astype(np.float32).astype(np.float32)
            self.ABR = np.array(data[2*fft_size:3*fft_size], dtype=dtype).astype(np.float32).astype(np.float32)
            self.ABI = np.array(data[3*fft_size:], dtype=dtype).astype(np.float32).astype(np.float32)
        else:
            print(f"ERROR in ZoomSpectrum packet size: expected {total_entries * 4} bytes, got {len(blob)} bytes.")
            self.AA = np.zeros(fft_size, dtype=np.float32)
            self.BB = np.zeros(fft_size, dtype=np.float32)
            self.ABR = np.zeros(fft_size, dtype=np.float32)
            self.ABI = np.zeros(fft_size, dtype=np.float32)

        self._is_read = True

    def info(self):
        self._read()
        desc = " Calibrator Zoom Spectra\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        return desc
