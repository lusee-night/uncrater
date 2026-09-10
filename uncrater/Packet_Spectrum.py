from .PacketBase import PacketBase
from .utils import Time2Time, process_ADC_stats, process_telemetry
from .c_utils import decode_10plus6, decode_5_into_4
import struct
import numpy as np
import binascii
from typing import Tuple
from .constants import NCHANNELS, NPRODUCTS


def frequency_averaging_factor(value):
    if value == 1:
        return 1
    if value == 2:
        return 2
    if value in (3, 4):
        # Both historical wire values select the four-channel averaging mode
        return 4
    raise ValueError(f"invalid Navgf value {value}")


class Packet_Metadata(PacketBase):
    @property
    def desc(self):
        return "Data Product Metadata"

    def _read(self):
        if self._is_read:
            return
        attrs = self._decode_struct(self.schema.pystruct.meta_data)
        if attrs is None:
            return
        if not self._check_declared_version(attrs.version):
            return
        try:
            frequency_averaging_factor(attrs.base.Navgf)
        except ValueError as exc:
            self._fail("unsupported_format", str(exc))
            return
        navg2_shift = attrs.base.Navg2_shift
        if not 0 <= navg2_shift <= 15:
            self._fail(
                "unsupported_format",
                f"invalid Navg2_shift value {navg2_shift}",
            )
            return

        self.copy_attrs(attrs)
        # Schema 203 calls the completed weight "previous"; later schemas use "weight"
        self.weight = self.base.weight_previous if hasattr(self.base, 'weight_previous') else self.base.weight
        self.format = self.base.format
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
        if hasattr(self.base, "weight_current"):
            desc += f"Current weight: {self.base.weight_current}\n"
        desc += f"Previous weight: {self.weight}\n"
        return desc

    @property
    def frequency(self):
        factor = frequency_averaging_factor(self.base.Navgf)
        return np.arange(NCHANNELS // factor) * (0.025 * factor)

    @property
    def expected_frequency_count(self):
        factor = frequency_averaging_factor(self.base.Navgf)
        return NCHANNELS // factor


class Packet_SpectrumBase(PacketBase):

    @property
    def desc(self):
        return "Power Spectrum"

    def set_meta(self, meta):
        self.meta = meta

    def set_priority(self) -> None:
        raise RuntimeError("Packet_SpectrumBase is abstract, do not instantiate")

    def parse_spectra(self) -> bool:
        raise RuntimeError("Packet_SpectrumBase is abstract, do not instantiate")

    def get_fmt_and_ptype(self) -> Tuple[str, np.number]:
        if self.product < 4:
            return "I", np.uint32
        else:
            return "i", np.int32

    def check_crc(self):
        # The CRC covers encoded science words, excluding any final CDI padding
        payload_size = self._crc_payload_size
        calculated_crc = binascii.crc32(self._blob[8 : 8 + payload_size]) & 0xFFFFFFFF
        if self.crc != calculated_crc:
            self._issue(
                "crc_mismatch",
                f"stored CRC 0x{self.crc:08X} does not match 0x{calculated_crc:08X}",
                details={"calculated_crc": calculated_crc, "stored_crc": self.crc},
            )

    def _read(self):
        if self._is_read:
            return
        self.set_priority()
        if not self._validate_min_length(8):
            return
        metadata = getattr(self, "meta", None)
        if metadata is None or any(
                issue.fatal for issue in metadata.decode_status.issues):
            self._fail("missing_metadata", "spectrum packet requires science metadata")
            return
        metadata_uid = metadata.unique_packet_id
        metadata_binding_key = metadata.schema.binding_key
        if metadata_binding_key != self.schema.binding_key:
            self._fail(
                "declared_version_mismatch",
                f"spectrum binding {self.schema.binding_key} does not match metadata binding {metadata_binding_key}",
            )
            return

        self.unique_packet_id, self.crc = struct.unpack_from("<II", self._blob, 0)
        if metadata_uid != self.unique_packet_id:
            self._issue(
                "unique_packet_id_mismatch",
                f"packet UID {self.unique_packet_id} does not match metadata UID {metadata_uid}",
                details={
                    "metadata_uid": metadata_uid,
                    "packet_uid": self.unique_packet_id,
                },
            )

        if not self.parse_spectra():
            return
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
        appids = self.schema.appids
        families = [
            ("AppID_SpectraHigh", 1),
            ("AppID_SpectraMed", 2),
            ("AppID_SpectraLow", 3),
            ("AppID_SpectraVeryLow", 4),
        ]
        for name, priority in families:
            base = getattr(appids, name, None)
            if base is not None and base <= self.appid < base + NPRODUCTS:
                self.priority = priority
                self.product = self.appid - base
                return
        raise ValueError(
            f"AppID 0x{self.appid:03X} is not a spectrum in binding "
            f"{self.schema.binding_key}"
        )

    def parse_spectra(self):
        payload = self._blob[8:]
        pystruct = self.schema.pystruct
        fmt, ptype = self.get_fmt_and_ptype()
        expected = self.meta.expected_frequency_count
        navg2_shift = self.meta.base.Navg2_shift
        weight = self.meta.weight
        if weight == 0:
            self._fail("payload_decode_failed", "metadata weight is zero")
            return False

        if self.meta.format == pystruct.OUTPUT_32BIT:
            expected_bytes = 4 * expected
            if not self._validate_length(8 + expected_bytes, allow_cdi_padding=False):
                return False
            dtype = "<u4" if fmt == "I" else "<i4"
            data = np.frombuffer(payload, dtype=dtype, count=expected)
        elif self.meta.format == pystruct.OUTPUT_16BIT_10_PLUS_6:
            expected_bytes = 2 * expected
            if not self._validate_length(8 + expected_bytes, allow_cdi_padding=False):
                return False
            compressed_data = np.frombuffer(payload, dtype="<u2", count=expected)
            data = decode_10plus6(compressed_data)
        elif self.meta.format == pystruct.OUTPUT_16BIT_4_TO_5:
            expected_words = expected // 4 * 5
            expected_bytes = 2 * expected_words
            if not self._validate_length(8 + expected_bytes, allow_cdi_padding=False):
                return False
            compressed_data = np.frombuffer(payload, dtype="<u2", count=expected_words)
            data = decode_5_into_4(compressed_data)
        else:
            self._fail(
                "unsupported_format",
                f"spectrum format {self.meta.format} is not supported",
            )
            return False

        self._crc_payload_size = expected_bytes
        self.data = data.astype(ptype).astype(np.float64) / weight * (1 << navg2_shift)
        return True



class Packet_TR_Spectrum(Packet_SpectrumBase):
    def set_priority(self):
        appids = self.schema.appids
        families = [
            ("AppID_SpectraTRHigh", 1),
            ("AppID_SpectraTRMed", 2),
            ("AppID_SpectraTRLow", 3),
        ]
        for name, priority in families:
            base = getattr(appids, name, None)
            if base is not None and base <= self.appid < base + NPRODUCTS:
                self.priority = priority
                self.product = self.appid - base
                return
        raise ValueError(
            f"AppID 0x{self.appid:03X} is not a TR spectrum in binding "
            f"{self.schema.binding_key}"
        )

    def parse_spectra(self):
        start = self.meta.base.tr_start
        stop = self.meta.base.tr_stop
        avg_shift = self.meta.base.tr_avg_shift
        navg2_shift = self.meta.base.Navg2_shift
        if (
            start < 0
            or stop <= start
            or stop > NCHANNELS
            or not 0 <= avg_shift <= 15
            or not 0 <= navg2_shift <= 15
        ):
            self._fail(
                "payload_decode_failed",
                f"invalid TR geometry start={start}, stop={stop}, avg_shift={avg_shift}, Navg2_shift={navg2_shift}",
            )
            return False
        span = stop - start
        average = 1 << avg_shift
        if span % average:
            self._fail(
                "payload_decode_failed",
                f"TR span {span} is not divisible by averaging factor {average}",
            )
            return False
        Nbins = span // average
        Navg2 = 1 << navg2_shift
        expected = Navg2 * Nbins
        if not self._validate_length(8 + 2 * expected):
            return False
        enc_data = np.frombuffer(self._blob, dtype="<u2", offset=8, count=expected)
        data = decode_10plus6(enc_data)
        self._crc_payload_size = 2 * expected
        self.data = data.reshape(Navg2, Nbins)
        return True

class Packet_Grimm(PacketBase):
    @property
    def desc(self):
        return "Grimm Select Frequencies"

    def _read(self):
        if self._is_read:
            return
        if not self._validate_min_length(4):
            return
        self.unique_packet_id = struct.unpack_from("<I", self._blob, 0)[0]
        payload = self._blob[4:]
        if len(payload) % 2:
            self._fail("bad_blob_length", "Grimm payload byte count must be even")
            return
        compressed_data = np.frombuffer(payload, dtype="<u2")
        if compressed_data.size % 5:
            self._fail(
                "payload_decode_failed",
                "Grimm compressed word count must be divisible by five",
            )
            return
        data = decode_5_into_4(compressed_data)
        values_per_average = NPRODUCTS * 4
        if data.size == 0 or data.size % values_per_average:
            self._fail(
                "payload_decode_failed",
                f"decoded Grimm count {data.size} is not divisible by {values_per_average}",
            )
            return
        self.data = data.reshape((-1, NPRODUCTS, 4))
        self._is_read = True

    def info(self):
        self._read()
        desc = ""
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"Npoints: {len(self.data)}\n"
        return desc
