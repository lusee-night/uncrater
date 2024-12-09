from .PacketBase import PacketBase
from .utils import Time2Time
from pycoreloop import appId as id
import struct

class Packet_Cal_Metadata(PacketBase):
    @property
    def desc(self):
        return "Calibrator Metadata"

    def _read(self):
        if self._is_read:
            return
        super()._read()        
        self.unique_packet_id = struct.unpack("<I", self._blob[0:4])[0]
        self.time = Time2Time(struct.unpack("<I", self._blob[4:8])[0], struct.unpack("<H", self._blob[8:12])[0])        
        self.registers = struct.unpack("<497I", self._blob[12:12+497*4])
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
        self.default_drift = self.registers[0x0C]
        self.have_lock_value = self.registers[0x0D]
        self.have_lock_radian = self.registers[0x0E]
        self.lower_guard_value = self.registers[0x0F]
        self.upper_guard_value = self.registers[0x10]
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
        self.phaser = self.registers[0x1C]
        self.averager_err_cnt = self.registers[0x24]
        self.process_err_cnt = self.registers[0x34]
        self.enable = self.registers[0x3C]
        self.power_index = self.registers[0x3D]
        self.fd_sd_index = self.registers[0x3E]
        self.fd_xsdx_index = self.registers[0x3F]
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

    def set_meta(self, meta):
        self.meta = meta

    def _read(self):
        if self._is_read:
            return
        super()._read()
        self.unique_packet_id = struct.unpack("<I", self._blob[0:4])[0]

        if self.meta.unique_packet_id != self.unique_packet_id:
            print("Packet ID mismatch!!")
            self.packed_id_mismatch = True

        self.data = struct.unpack(f"<{len(self._blob[4:])//4}I", self._blob[4:])
        self.data = []
        for ch in range(4):
            data = self.data[ch*1024:ch*1024+512]+1j*self.data[ch*1024+512:ch*1024+1024]
            self.data.append(data)
        self.gNacc = self.data[4*1024+1]
        self.gphase = self.data[4*1024+2:]


        self._is_read = True

    def info(self):
        self._read()
        desc = " Calibrator Data\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        return desc

class Packet_Cal_RawPFB(PacketBase):
    @property
    def desc(self):
        return "Calibrator Raw PFB"

    def set_meta(self, meta):
        self.meta = meta

    def _read(self):
        if self._is_read:
            return
        super()._read()
        self.channel = self.appid-id.AppID_RawPFB
        self.unique_packet_id = struct.unpack("<I", self._blob[0:4])[0]

        if self.meta.unique_packet_id != self.unique_packet_id:
            print("Packet ID mismatch!!")
            self.packed_id_mismatch = True


        self.data = struct.unpack(f"<{len(self._blob[4:])//4}I", self._blob[4:])
        self.real = self.data[:1024]
        self.imag = self.data[1024:]
        self.data= self.real + 1j*self.imag
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

    def set_meta(self, meta):
        self.meta = meta

    def _read(self):
        if self._is_read:
            return
        super()._read()
        self.unique_packet_id = struct.unpack("<I", self._blob[0:4])[0]

        if self.meta.unique_packet_id != self.unique_packet_id:
            print("Packet ID mismatch!!")
            self.packed_id_mismatch = True

        self.debug_page = self.appid - id.AppID_CalDebug
        self.data = np.array(struct.unpack(f"<{len(self._blob[4:])//4}I", self._blob[4:]))
        self.data = self.data.reshape((6,1024))

    def info(self):
        self._read()
        desc = " Calibrator Debug\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        return desc
