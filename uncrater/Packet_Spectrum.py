from .PacketBase import PacketBase, pystruct
from .utils import Time2Time, process_ADC_stats, process_telemetry
from .c_utils import decode_10plus6
import os, sys
import struct
import numpy as np
import binascii
from typing import Tuple

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

# now try to import pycoreloop
try:
    from pycoreloop import appId as id
except ImportError:
    print("Can't import pycoreloop\n")
    print("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo.")
    sys.exit(1)


class Packet_Metadata(PacketBase):
    @property
    def desc(self):
        return "Data Product Metadata"

    def _read(self):
        if self._is_read:
            return
        super()._read()
        # TODO: check if this actually works
        self.copy_attrs(pystruct.meta_data.from_buffer_copy(self._blob))
        self.format = self.seq.format
        self.time = Time2Time(self.base.time_32, self.base.time_16)
        self.errormask = self.base.errors
        adc = process_ADC_stats(self.base.ADC_stat)
        for k, v in adc.items():
            setattr(self, "adc_" + k, v)
        telemetry = process_telemetry(self.base.TVS_sensors)
        for k, v in telemetry.items():
            setattr(self, "telemetry_" + k, v)

        self._is_read = True

    def info(self):
        self._read()
        desc = ""
        desc += f"Version : {self.version}\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"Errormask: {self.errormask}\n"
        desc += f"Time: {self.time}\n"
        desc += f"Current weight: {self.base.weight_current}\n"
        desc += f"Previous weight: {self.base.weight_previous}\n"
        return desc

    @property
    def frequency(self):
        Navgf = self.seq.Navgf
        if Navgf == 1:
            return np.arange(2048) * 0.025
        elif Navgf == 2:
            return np.arange(1024) * 0.05
        else:
            return np.arange(512) * 0.1


class Packet_SpectrumBase(PacketBase):

    @property
    def desc(self):
        return "Power Spectrum"

    def set_meta(self, meta):
        self.meta = meta

    def set_priority(self):
        raise RuntimeError("Packet_SpectrumBase is abstract, do not instantiate")

    def parse_spectra(self):
        raise RuntimeError("Packet_SpectrumBase is abstract, do not instantiate")

    def get_fmt_and_ptype(self) -> Tuple[str, np.number]:
        if self.product < 4:
            return "I", np.uint32
        else:
            return "i", np.int32

    def check_crc(self):
        calculated_crc = binascii.crc32(self._blob[8:]) & 0xFFFFFFFF
        self.error_crc_mismatch = not (self.crc == calculated_crc)
        if self.error_crc_mismatch:
            print(f"CRC: {self.crc:x} {calculated_crc:x}")
            print("WARNING CRC mismatch!!!!!")
            try:
                Ndata = len(self._blob[8:]) // 4
                data = struct.unpack(f"<{Ndata}{self.get_fmt_and_ptype()[0]}", self._blob[8:])
                print(data, Ndata)
            except:
                pass

    def _read(self):
        if self._is_read:
            return

        self.error_packed_id_mismatch = False
        self.error_data_read = False
        self.error_crc_mismatch = False

        self.set_priority()
        super()._read()
        self.unique_packet_id, self.crc = struct.unpack("<II", self._blob[:8])

        if not hasattr(self, "meta"):
            print("Loading packet without metadata!")
            self.packed_id_mismatch = True

        if self.meta.unique_packet_id != self.unique_packet_id:
            print("Packet ID mismatch!!")
            self.packed_id_mismatch = True

        if self.meta.format == 0 and len(self._blob[8:]) // 4 > 2048:
            print("Spurious data, trimming!!!")
            self._blob = self._blob[: 8 + 2048 * 4]

        self.parse_spectra()
        self.check_crc()

        self._is_read = True

    @property
    def frequency(self):
        return self.meta.frequency

    def info(self):
        self._read()
        desc = ""
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"crc : {self.crc}\n"
        desc += f"Npoints: {len(self.data)}\n"
        return desc


class Packet_Spectrum(Packet_SpectrumBase):

    def set_priority(self):
        if (
            self.appid >= id.AppID_SpectraHigh
            and self.appid < id.AppID_SpectraHigh + 16
        ):
            self.priority = 1
            self.product = self.appid - id.AppID_SpectraHigh
        elif (
            self.appid >= id.AppID_SpectraMed and self.appid < id.AppID_SpectraMed + 16
        ):
            self.priority = 2
            self.product = self.appid - id.AppID_SpectraMed
        else:
            assert (
                self.appid >= id.AppID_SpectraLow
                and self.appid < id.AppID_SpectraLow + 16
            )
            self.priority = 3
            self.product = self.appid - id.AppID_SpectraLow

    def parse_spectra(self):
        if self.meta.format == 0 and len(self._blob[8:]) // 4 > 2048:
            print("Spurious data, trimming!!!")
            self._blob = self._blob[: 8 + 2048 * 4]

        fmt, ptype = self.get_fmt_and_ptype()

        if self.meta.format == 0:
            Ndata = len(self._blob[8:]) // 4
            try:
                data = struct.unpack(f"<{Ndata}{fmt}", self._blob[8:])
            except:
                self.error_data_read = True
                data = np.zeros(Ndata)
        else:
            raise NotImplementedError("Only format 0 is supported")
        self.data = np.array(data, dtype=ptype).astype(np.float64)


class Packet_TR_Spectrum(Packet_SpectrumBase):
    def set_priority(self):
        if (
            self.appid >= id.AppID_SpectraTRHigh
            and self.appid < id.AppID_SpectraTRHigh + 16
        ):
            self.priority = 1
            self.product = self.appid - id.AppID_SpectraTRHigh
        elif (
            self.appid >= id.AppID_SpectraTRMed
            and self.appid < id.AppID_SpectraTRMed + 16
        ):
            self.priority = 2
            self.product = self.appid - id.AppID_SpectraTRMed
        else:
            assert (
                self.appid >= id.AppID_SpectraTRLow
                and self.appid < id.AppID_SpectraTRLow + 16
            )
            self.priority = 3
            self.product = self.appid - id.AppID_SpectraTRLow

    def parse_spectra(self):
        # TODO: check length?
        # if self.meta.format==0 and len(self._blob[8:])//4>2048:
        #     print ("Spurious data, trimming!!!")
        #     self._blob = self._blob[:8 + 2048 * 4]

        if self.meta.format == 0:
            # data consists of uint16_t, _blob has type int32_t
            Ndata = len(self._blob[8:]) // 2
            try:
                enc_data = struct.unpack(f"<{Ndata}H", self._blob[8:])
                enc_data = np.array(enc_data, dtype=np.uint16)
                data = decode_10plus6(enc_data)
            except:
                self.error_data_read = True
                data = np.zeros(Ndata, dtype=np.int32)
        else:
            raise NotImplementedError("Only format 0 is supported")
        self.data = np.array(data, dtype=np.int32)
