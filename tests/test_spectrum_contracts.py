import binascii
import ctypes
import struct

import numpy as np
import pytest

from uncrater.Packet_Spectrum import (
    Packet_Grimm,
    Packet_Metadata,
    Packet_Spectrum,
    Packet_TR_Spectrum,
)
from uncrater.c_utils import encode_10plus6, encode_4_into_5
from uncrater.constants import NCHANNELS, NPRODUCTS
from uncrater.schema_registry import BINDINGS_BY_KEY, LATEST_BINDING

def bytes_of(value):
    return ctypes.string_at(ctypes.addressof(value), ctypes.sizeof(value))


def padded(value, fill=b"\xA5\x5A\xC3"):
    payload = bytes_of(value)
    return payload + fill[: (-len(payload)) % 4]


def metadata_value(
    binding=LATEST_BINDING,
    *,
    uid=0x12345678,
    output_format=None,
    navgf=1,
    weight=2,
    navg2_shift=1,
    tr_start=0,
    tr_stop=4,
    tr_avg_shift=1,
):
    value = binding.pystruct.meta_data()
    value.version = binding.accepted_reported_versions[0]
    value.unique_packet_id = uid
    value.base.format = (
        binding.pystruct.OUTPUT_32BIT
        if output_format is None
        else output_format
    )
    value.base.Navgf = navgf
    value.base.Navg2_shift = navg2_shift
    value.base.tr_start = tr_start
    value.base.tr_stop = tr_stop
    value.base.tr_avg_shift = tr_avg_shift
    if hasattr(value.base, "weight_previous"):
        value.base.weight_previous = weight
    else:
        value.base.weight = weight
    if hasattr(value.base, "weight_current"):
        value.base.weight_current = weight + 1
    return value


def make_metadata(binding=LATEST_BINDING, **kwargs):
    value = metadata_value(binding, **kwargs)
    return Packet_Metadata(
        binding.appids.AppID_MetaData,
        blob=padded(value),
        schema=binding,
        reported_version=binding.accepted_reported_versions[0],
    )


def packet_blob(uid, payload, *, crc=None, padding=b""):
    if crc is None:
        crc = binascii.crc32(payload) & 0xFFFFFFFF
    return struct.pack("<II", uid, crc) + payload + padding


def encode_4_to_5(values):
    return np.concatenate(
        [encode_4_into_5(chunk) for chunk in values.reshape(-1, 4)]
    )


def normal_payload(metadata, values):
    if metadata.format == metadata.schema.pystruct.OUTPUT_32BIT:
        dtype = "<u4" if np.all(values >= 0) else "<i4"
        return np.asarray(values, dtype=dtype).tobytes()
    if metadata.format == metadata.schema.pystruct.OUTPUT_16BIT_10_PLUS_6:
        return encode_10plus6(np.asarray(values, dtype=np.int32)).astype("<u2").tobytes()
    if metadata.format == metadata.schema.pystruct.OUTPUT_16BIT_4_TO_5:
        return encode_4_to_5(np.asarray(values, dtype=np.int32)).astype("<u2").tobytes()
    raise AssertionError("test helper received an unsupported format")


@pytest.mark.parametrize(
    ("binding_key", "reported_version"),
    [
        ("203", 0x203),
        ("305", 0x305),
        ("306-early", 0x306),
        ("306-final", 0x306),
        ("307", 0x307),
    ],
)
@pytest.mark.parametrize(
    ("navgf", "expected_count", "step"),
    [(1, 2048, 0.025), (2, 1024, 0.05), (3, 512, 0.1), (4, 512, 0.1)],
)
def test_metadata_uses_selected_schema_and_validates_frequency_geometry(
    binding_key, reported_version, navgf, expected_count, step
):
    binding = BINDINGS_BY_KEY[binding_key]
    metadata = make_metadata(binding, navgf=navgf)

    assert metadata.schema is binding
    assert metadata.version == reported_version
    assert metadata.expected_frequency_count == expected_count
    assert metadata.frequency.shape == (expected_count,)
    assert metadata.frequency[1] == pytest.approx(step)
    assert metadata.decode_status.ok
    assert f"Previous weight: {metadata.weight}\n" in metadata.info()


@pytest.mark.parametrize(("field", "value"), [("Navgf", 0), ("Navgf", 5), ("Navg2_shift", 16)])
def test_metadata_rejects_invalid_averaging_fields(field, value):
    binding = LATEST_BINDING
    raw = metadata_value(binding)
    setattr(raw.base, field, value)

    metadata = Packet_Metadata(
        binding.appids.AppID_MetaData,
        blob=padded(raw),
        schema=binding,
        reported_version=0x307,
        strict=False,
    )

    assert metadata.decode_status.codes == ("unsupported_format",)
    assert not hasattr(metadata, "base")


def test_metadata_rejects_declared_version_and_non_struct_lengths():
    binding = LATEST_BINDING
    raw = metadata_value(binding)
    raw.version = 0x305
    mismatch = Packet_Metadata(
        binding.appids.AppID_MetaData,
        blob=padded(raw),
        schema=binding,
        reported_version=0x307,
        strict=False,
    )
    assert mismatch.decode_status.codes == ("declared_version_mismatch",)
    assert not hasattr(mismatch, "base")

    valid_blob = padded(metadata_value(binding))
    for malformed in (valid_blob[:-3], valid_blob + b"\x00"):
        metadata = Packet_Metadata(
            binding.appids.AppID_MetaData,
            blob=malformed,
            schema=binding,
            reported_version=0x307,
            strict=False,
        )
        assert metadata.decode_status.codes == ("bad_blob_length",)
        assert not hasattr(metadata, "base")


def test_all_normal_spectrum_encodings_have_exact_channel_counts():
    binding = LATEST_BINDING
    values = np.tile(np.asarray([0, 64, 128, 256], dtype=np.int32), 128)
    formats = (
        binding.pystruct.OUTPUT_32BIT,
        binding.pystruct.OUTPUT_16BIT_10_PLUS_6,
        binding.pystruct.OUTPUT_16BIT_4_TO_5,
    )

    for output_format in formats:
        metadata = make_metadata(binding, output_format=output_format, navgf=4)
        payload = normal_payload(metadata, values)
        packet = Packet_Spectrum(
            binding.appids.AppID_SpectraHigh,
            blob=packet_blob(metadata.unique_packet_id, payload),
            meta=metadata,
            schema=binding,
            reported_version=0x307,
        )

        assert packet.data.shape == (512,)
        np.testing.assert_array_equal(packet.data[:4], values[:4])
        assert packet.decode_status.ok


def test_signed_spectrum_preserves_product_interpretation():
    binding = LATEST_BINDING
    metadata = make_metadata(binding, navgf=4, weight=1, navg2_shift=0)
    values = np.tile(np.asarray([-4, -3, -2, -1], dtype=np.int32), 128)
    payload = values.astype("<i4").tobytes()

    packet = Packet_Spectrum(
        binding.appids.AppID_SpectraHigh + 4,
        blob=packet_blob(metadata.unique_packet_id, payload),
        meta=metadata,
        schema=binding,
        reported_version=0x307,
    )

    assert packet.product == 4
    np.testing.assert_array_equal(packet.data[:4], values[:4])


def test_historical_very_low_spectrum_uses_binding_appids():
    binding = BINDINGS_BY_KEY["203"]
    metadata = make_metadata(binding, navgf=4, weight=1, navg2_shift=0)
    values = np.arange(metadata.expected_frequency_count, dtype=np.uint32)
    payload = values.astype("<u4").tobytes()

    packet = Packet_Spectrum(
        binding.appids.AppID_SpectraVeryLow + 2,
        blob=packet_blob(metadata.unique_packet_id, payload),
        meta=metadata,
        schema=binding,
        reported_version=0x203,
    )

    assert (packet.priority, packet.product) == (4, 2)
    np.testing.assert_array_equal(packet.data, values)


@pytest.mark.parametrize("output_format_name", ["OUTPUT_32BIT", "OUTPUT_16BIT_10_PLUS_6", "OUTPUT_16BIT_4_TO_5"])
@pytest.mark.parametrize("delta", [-1, 1])
def test_normal_spectrum_rejects_truncated_and_extra_encoded_bytes(
    output_format_name, delta
):
    binding = LATEST_BINDING
    output_format = getattr(binding.pystruct, output_format_name)
    metadata = make_metadata(binding, output_format=output_format, navgf=4)
    values = np.tile(np.asarray([0, 64, 128, 256], dtype=np.int32), 128)
    payload = normal_payload(metadata, values)
    malformed = payload[:-1] if delta < 0 else payload + b"\x00"

    packet = Packet_Spectrum(
        binding.appids.AppID_SpectraHigh,
        blob=packet_blob(metadata.unique_packet_id, malformed),
        meta=metadata,
        schema=binding,
        reported_version=0x307,
        strict=False,
    )

    assert packet.decode_status.codes == ("bad_blob_length",)
    assert not hasattr(packet, "data")


def test_spectrum_requires_valid_same_schema_metadata():
    binding = LATEST_BINDING
    missing = Packet_Spectrum(
        binding.appids.AppID_SpectraHigh,
        blob=b"\x00" * 8,
        schema=binding,
        reported_version=0x307,
        strict=False,
    )
    assert missing.decode_status.codes == ("missing_metadata",)
    assert not hasattr(missing, "data")

    raw = metadata_value(binding)
    raw.base.Navgf = 0
    invalid_metadata = Packet_Metadata(
        binding.appids.AppID_MetaData,
        blob=padded(raw),
        schema=binding,
        reported_version=0x307,
        strict=False,
    )
    invalid = Packet_Spectrum(
        binding.appids.AppID_SpectraHigh,
        blob=b"\x00" * 8,
        meta=invalid_metadata,
        schema=binding,
        reported_version=0x307,
        strict=False,
    )
    assert invalid.decode_status.codes == ("missing_metadata",)
    assert not hasattr(invalid, "data")

    historical_metadata = make_metadata(BINDINGS_BY_KEY["305"], navgf=4)
    conflict = Packet_Spectrum(
        binding.appids.AppID_SpectraHigh,
        blob=b"\x00" * 8,
        meta=historical_metadata,
        schema=binding,
        reported_version=0x307,
        strict=False,
    )
    assert conflict.decode_status.codes == ("declared_version_mismatch",)
    assert not hasattr(conflict, "data")


def test_nonfatal_unknown_schema_metadata_allows_diagnostic_spectrum_decode():
    binding = LATEST_BINDING
    raw = metadata_value(binding, navgf=4, weight=1, navg2_shift=0)
    raw.version = 0x399
    metadata = Packet_Metadata(
        binding.appids.AppID_MetaData,
        blob=padded(raw),
        schema=binding,
        reported_version=0x399,
        diagnostic_override=True,
    )
    values = np.arange(metadata.expected_frequency_count, dtype=np.uint32)
    payload = values.astype("<u4").tobytes()

    packet = Packet_Spectrum(
        binding.appids.AppID_SpectraHigh,
        blob=packet_blob(metadata.unique_packet_id, payload),
        meta=metadata,
        schema=binding,
        reported_version=0x399,
        diagnostic_override=True,
    )

    assert metadata.decode_status.codes == ("unknown_schema",)
    assert packet.decode_status.codes == ("unknown_schema",)
    np.testing.assert_array_equal(packet.data, values)


@pytest.mark.parametrize(
    ("attribute", "value", "issue_code"),
    [("weight", 0, "payload_decode_failed"), ("format", 255, "unsupported_format")],
)
def test_spectrum_rejects_invalid_weight_and_format(attribute, value, issue_code):
    binding = LATEST_BINDING
    metadata = make_metadata(binding, navgf=4)
    setattr(metadata, attribute, value)
    packet = Packet_Spectrum(
        binding.appids.AppID_SpectraHigh,
        blob=packet_blob(metadata.unique_packet_id, b""),
        meta=metadata,
        schema=binding,
        reported_version=0x307,
        strict=False,
    )

    assert packet.decode_status.codes == (issue_code,)
    assert not hasattr(packet, "data")


def test_uid_and_crc_issues_are_nonfatal_and_keep_spectrum_data():
    binding = LATEST_BINDING
    metadata = make_metadata(binding, navgf=4, weight=1, navg2_shift=0)
    values = np.arange(metadata.expected_frequency_count, dtype=np.uint32)
    payload = values.astype("<u4").tobytes()

    packet = Packet_Spectrum(
        binding.appids.AppID_SpectraHigh,
        blob=packet_blob(metadata.unique_packet_id + 1, payload, crc=0),
        meta=metadata,
        schema=binding,
        reported_version=0x307,
    )

    assert packet.decode_status.codes == (
        "unique_packet_id_mismatch",
        "crc_mismatch",
    )
    assert not any(issue.fatal for issue in packet.decode_status.issues)
    np.testing.assert_array_equal(packet.data, values)
    assert packet.error_packed_id_mismatch
    assert packet.packed_id_mismatch
    assert packet.error_crc_mismatch


def test_time_resolved_geometry_and_crc_exclude_cdi_padding():
    binding = LATEST_BINDING
    metadata = make_metadata(
        binding,
        navg2_shift=0,
        tr_start=0,
        tr_stop=1,
        tr_avg_shift=0,
    )
    values = np.asarray([64], dtype=np.int32)
    encoded = encode_10plus6(values).astype("<u2").tobytes()

    packet = Packet_TR_Spectrum(
        binding.appids.AppID_SpectraTRHigh,
        blob=packet_blob(metadata.unique_packet_id, encoded, padding=b"\xA5\x5A"),
        meta=metadata,
        schema=binding,
        reported_version=0x307,
    )

    assert packet.decode_status.ok
    assert packet.data.shape == (1, 1)
    np.testing.assert_array_equal(packet.data, [[64]])


def test_time_resolved_shape_uses_both_averaging_dimensions():
    binding = LATEST_BINDING
    metadata = make_metadata(
        binding,
        navg2_shift=2,
        tr_start=2,
        tr_stop=10,
        tr_avg_shift=1,
    )
    values = np.arange(16, dtype=np.int32) * 64
    encoded = encode_10plus6(values).astype("<u2").tobytes()
    packet = Packet_TR_Spectrum(
        binding.appids.AppID_SpectraTRMed + 3,
        blob=packet_blob(metadata.unique_packet_id, encoded),
        meta=metadata,
        schema=binding,
        reported_version=0x307,
    )

    assert (packet.priority, packet.product) == (2, 3)
    assert packet.data.shape == (4, 4)
    np.testing.assert_array_equal(packet.data.ravel(), values)


@pytest.mark.parametrize(
    ("start", "stop", "avg_shift", "navg2_shift"),
    [(4, 4, 0, 0), (0, NCHANNELS + 1, 0, 0), (0, 3, 1, 0), (0, 1, 16, 0), (0, 1, 0, 16)],
)
def test_time_resolved_rejects_invalid_geometry(start, stop, avg_shift, navg2_shift):
    binding = LATEST_BINDING
    metadata = make_metadata(binding)
    metadata.base.tr_start = start
    metadata.base.tr_stop = stop
    metadata.base.tr_avg_shift = avg_shift
    metadata.base.Navg2_shift = navg2_shift

    packet = Packet_TR_Spectrum(
        binding.appids.AppID_SpectraTRHigh,
        blob=packet_blob(metadata.unique_packet_id, b""),
        meta=metadata,
        schema=binding,
        reported_version=0x307,
        strict=False,
    )

    assert packet.decode_status.codes == ("payload_decode_failed",)
    assert not hasattr(packet, "data")


@pytest.mark.parametrize("padding", [b"\x00", b"\x00\x00\x00\x00"])
def test_time_resolved_accepts_only_raw_or_four_byte_rounded_length(padding):
    binding = LATEST_BINDING
    metadata = make_metadata(
        binding,
        navg2_shift=0,
        tr_start=0,
        tr_stop=1,
        tr_avg_shift=0,
    )
    encoded = encode_10plus6(np.asarray([64], dtype=np.int32)).astype("<u2").tobytes()
    packet = Packet_TR_Spectrum(
        binding.appids.AppID_SpectraTRHigh,
        blob=packet_blob(metadata.unique_packet_id, encoded, padding=padding),
        meta=metadata,
        schema=binding,
        reported_version=0x307,
        strict=False,
    )

    assert packet.decode_status.codes == ("bad_blob_length",)
    assert not hasattr(packet, "data")


def test_grimm_uid_and_shape():
    values = np.arange(2 * NPRODUCTS * 4, dtype=np.int32) * 64
    compressed = encode_4_to_5(values).astype("<u2").tobytes()
    blob = struct.pack("<I", 0xAABBCCDD) + compressed

    grimm = Packet_Grimm(LATEST_BINDING.appids.AppID_SpectraGrimm, blob=blob)
    assert isinstance(grimm.unique_packet_id, int)
    assert grimm.unique_packet_id == 0xAABBCCDD
    assert grimm.data.shape == (2, NPRODUCTS, 4)
    np.testing.assert_array_equal(grimm.data.ravel(), values)


def test_grimm_rejects_an_extra_word_after_a_complete_encoded_stream():
    values = np.arange(NPRODUCTS * 4, dtype=np.int32) * 64
    compressed = encode_4_to_5(values).astype("<u2").tobytes()
    packet = Packet_Grimm(
        LATEST_BINDING.appids.AppID_SpectraGrimm,
        blob=struct.pack("<I", 1) + compressed + b"\xFF\x7E",
        strict=False,
    )

    assert packet.decode_status.codes == ("payload_decode_failed",)
    assert not hasattr(packet, "data")


@pytest.mark.parametrize(
    ("payload", "issue_code"),
    [
        (b"\x00", "bad_blob_length"),
        (b"\x00\x00" * 2, "payload_decode_failed"),
        (b"\x00\x00" * 5, "payload_decode_failed"),
        (b"", "payload_decode_failed"),
    ],
)
def test_grimm_rejects_odd_non_grouped_and_wrong_shape_payloads(payload, issue_code):
    packet = Packet_Grimm(
        LATEST_BINDING.appids.AppID_SpectraGrimm,
        blob=struct.pack("<I", 1) + payload,
        strict=False,
    )

    assert packet.decode_status.codes == (issue_code,)
    assert not hasattr(packet, "data")
