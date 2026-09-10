import ctypes
import importlib
import struct

import numpy as np
import pytest

from uncrater.Packet_Calibrator import (
    Packet_Cal_Data,
    Packet_Cal_Debug,
    Packet_Cal_Metadata,
    Packet_Cal_RawPFB,
    Packet_Cal_RegisterDump,
    Packet_Cal_ZoomSpectra,
)
from uncrater.decode_status import PacketDecodeError
from uncrater.schema_registry import BINDINGS_BY_KEY, LATEST_BINDING


def bytes_of(value):
    return ctypes.string_at(ctypes.addressof(value), ctypes.sizeof(value))


def cdi_padded(value):
    payload = bytes_of(value)
    return payload + b"\0" * (-len(payload) % 4)


def page_blob(uid, values):
    return struct.pack("<III", uid, 16, 0) + values.tobytes()


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
def test_calibrator_metadata_uses_each_schema_drift_layout(
    binding_key, reported_version
):
    binding = BINDINGS_BY_KEY[binding_key]
    value = binding.pystruct.calibrator_metadata()
    value.version = reported_version
    value.unique_packet_id = 77
    value.drift[0] = 1
    if hasattr(value, "drift_shift"):
        value.drift_shift = 2

    packet = Packet_Cal_Metadata(
        int(binding.appids.AppID_Calibrator_MetaData),
        blob=cdi_padded(value),
        schema=binding,
        reported_version=reported_version,
    )

    assert packet.decode_status.ok
    assert packet.drift_raw.shape == (1024,)
    assert packet.drift.shape == (1024,)
    assert np.any(packet.drift != 0)


def test_calibrator_metadata_rejects_length_version_and_shift_before_publication():
    binding = LATEST_BINDING
    value = binding.pystruct.calibrator_metadata()
    value.version = 0x305
    mismatch = Packet_Cal_Metadata(
        int(binding.appids.AppID_Calibrator_MetaData),
        blob=bytes_of(value),
        schema=binding,
        reported_version=0x307,
        strict=False,
    )
    assert mismatch.decode_status.codes == ("declared_version_mismatch",)
    assert not hasattr(mismatch, "drift")

    value.version = 0x307
    value.drift_shift = 64
    bad_shift = Packet_Cal_Metadata(
        int(binding.appids.AppID_Calibrator_MetaData),
        blob=bytes_of(value),
        strict=False,
    )
    assert bad_shift.decode_status.codes == ("payload_decode_failed",)
    assert not hasattr(bad_shift, "drift")

    truncated = Packet_Cal_Metadata(
        int(binding.appids.AppID_Calibrator_MetaData),
        blob=bytes_of(value)[:-1],
        strict=False,
    )
    assert truncated.decode_status.codes == ("bad_blob_length",)
    assert not hasattr(truncated, "drift")


def test_calibrator_metadata_structural_failure_raises_by_default():
    with pytest.raises(PacketDecodeError, match="bad_blob_length"):
        Packet_Cal_Metadata(0x280, blob=b"short")


def test_register_dump_requires_exact_payload_without_touching_register_mapping():
    uid = 81
    registers = np.arange(498, dtype="<u4")
    packet = Packet_Cal_RegisterDump(0x201, blob=page_blob(uid, registers))
    assert packet.registers[0x4F] == 0x4F
    assert packet.weights.shape == (410,)

    malformed = Packet_Cal_RegisterDump(
        0x201,
        blob=page_blob(uid, registers) + b"\0",
        strict=False,
    )
    assert malformed.decode_status.codes == ("bad_blob_length",)
    assert not hasattr(malformed, "registers")


@pytest.mark.parametrize(("page", "count"), [(0, 2048), (1, 2048), (2, 1025)])
def test_calibrator_data_pages_have_exact_shapes(page, count):
    uid = 501
    values = np.arange(count, dtype="<i4")
    kwargs = {} if page == 0 else {"expected_id": uid}
    packet = Packet_Cal_Data(0x281 + page, blob=page_blob(uid, values), **kwargs)

    assert packet.data_page == page
    assert packet.decode_status.ok
    if page < 2:
        assert packet.data.shape == (4, 512)
    else:
        assert isinstance(packet.gNacc, int)
        assert packet.gphase.shape == (1024,)


@pytest.mark.parametrize(("page", "count"), [(0, 2047), (1, 2049), (2, 1024)])
def test_calibrator_data_rejects_wrong_page_lengths(page, count):
    uid = 502
    kwargs = {} if page == 0 else {"expected_id": uid}
    packet = Packet_Cal_Data(
        0x281 + page,
        blob=page_blob(uid, np.zeros(count, dtype="<i4")),
        strict=False,
        **kwargs,
    )

    assert packet.decode_status.codes == ("bad_blob_length",)
    assert not hasattr(packet, "data")


def test_calibrator_continuations_require_start_uid_but_mismatch_keeps_data():
    uid = 503
    blob = page_blob(uid, np.zeros(2048, dtype="<i4"))
    orphan = Packet_Cal_Data(0x282, blob=blob, strict=False)
    assert orphan.decode_status.codes == ("orphan_multipart_page",)
    assert not hasattr(orphan, "data")

    mismatch = Packet_Cal_Data(0x282, blob=blob, expected_id=uid + 1)
    assert mismatch.data.shape == (4, 512)
    assert mismatch.decode_status.codes == ("unique_packet_id_mismatch",)
    assert mismatch.error_packed_id_mismatch
    assert mismatch.packed_id_mismatch


def test_raw_pfb_requires_exact_page_and_preserves_uid_mismatch_payload():
    uid = 601
    values = np.arange(2048, dtype="<i4")
    packet = Packet_Cal_RawPFB(
        0x28B,
        blob=page_blob(uid, values),
        expected_id=uid + 1,
    )

    assert (packet.channel, packet.part) == (3, 1)
    np.testing.assert_array_equal(packet.data[:3], [0, 1, 2])
    assert packet.decode_status.codes == ("unique_packet_id_mismatch",)

    malformed = Packet_Cal_RawPFB(
        0x284,
        blob=page_blob(uid, values)[:-4],
        strict=False,
    )
    assert malformed.decode_status.codes == ("bad_blob_length",)
    assert not hasattr(malformed, "data")

    orphan = Packet_Cal_RawPFB(0x285, blob=page_blob(uid, values), strict=False)
    assert orphan.decode_status.codes == ("orphan_multipart_page",)
    assert not hasattr(orphan, "data")


@pytest.mark.parametrize("page", range(8))
def test_every_calibrator_debug_page_decodes_exact_payload(page):
    uid = 701
    payload = bytearray(3 * 1024 * 4)
    if page == 0:
        embedded = LATEST_BINDING.pystruct.calibrator_metadata()
        embedded.version = 0x307
        payload[2048:2048 + ctypes.sizeof(embedded)] = bytes_of(embedded)
    kwargs = {} if page == 0 else {"expected_id": uid}
    packet = Packet_Cal_Debug(
        0x28C + page,
        blob=struct.pack("<III", uid, 16, 0) + payload,
        **kwargs,
    )

    assert packet.debug_page == page
    assert packet.unique_packet_id == uid
    assert packet.is_read
    assert packet.decode_status.ok
    if page == 0:
        assert packet.metadata.from_debug


def test_exact_debug_page_is_not_reinterpreted_as_rle():
    uid = 702
    payload = bytearray([1]) * (3 * 1024 * 4)
    payload[-3:-1] = b"\x8C\x03"

    packet = Packet_Cal_Debug(
        0x28D,
        blob=struct.pack("<III", uid, 16, 0) + payload,
        expected_id=uid,
    )

    assert packet.decode_status.ok
    assert packet.powertop1.shape == (1024,)


@pytest.mark.parametrize(
    ("padding", "ok"),
    [(b"", True), (b"\xA5", False), (b"\xA5\x5A", True),
     (b"\xA5\x5A\xC3", False)],
)
def test_debug_rle_accepts_only_packed_or_uniquely_unpadded_payload(padding, ok):
    uid = 703
    encoded = b"\x8C\xFF" * 48 + b"\x8C\x30"
    packet = Packet_Cal_Debug(
        0x28D,
        blob=struct.pack("<III", uid, 16, 0) + encoded + padding,
        expected_id=uid,
        strict=False,
    )

    assert packet.decode_status.ok is ok
    assert hasattr(packet, "powertop1") is ok


def test_debug_rle_rejects_ambiguous_padding_candidates(monkeypatch):
    module = importlib.import_module("uncrater.Packet_Calibrator")
    expected = 3 * 1024 * 4
    monkeypatch.setattr(module, "rle_decode", lambda stream, original_size: b"\0" * expected)
    packet = Packet_Cal_Debug(
        0x28D,
        blob=struct.pack("<III", 704, 16, 0) + b"ABCD",
        expected_id=704,
        strict=False,
    )

    assert packet.decode_status.codes == ("payload_decode_failed",)
    assert not hasattr(packet, "powertop1")


def test_debug_page_validates_embedded_version_and_continuation_uid():
    uid = 705
    payload = bytearray(3 * 1024 * 4)
    embedded = LATEST_BINDING.pystruct.calibrator_metadata()
    embedded.version = 0x305
    payload[2048:2048 + ctypes.sizeof(embedded)] = bytes_of(embedded)
    mismatch = Packet_Cal_Debug(
        0x28C,
        blob=struct.pack("<III", uid, 16, 0) + payload,
        strict=False,
    )
    assert mismatch.decode_status.codes == ("declared_version_mismatch",)
    assert not hasattr(mismatch, "metadata")

    orphan = Packet_Cal_Debug(
        0x28D,
        blob=struct.pack("<III", uid, 16, 0) + bytes(3 * 1024 * 4),
        strict=False,
    )
    assert orphan.decode_status.codes == ("orphan_multipart_page",)

    uid_mismatch = Packet_Cal_Debug(
        0x28D,
        blob=struct.pack("<III", uid, 16, 0) + bytes(3 * 1024 * 4),
        expected_id=uid + 1,
    )
    assert uid_mismatch.powertop1.shape == (1024,)
    assert uid_mismatch.decode_status.codes == ("unique_packet_id_mismatch",)


@pytest.mark.parametrize("padding", [b"", b"\xA5\x5A"])
def test_zoom_accepts_only_packed_or_cdi_rounded_float_payload(padding):
    uid = 801
    values = np.arange(256, dtype="<f4")
    packet = Packet_Cal_ZoomSpectra(
        0x270,
        blob=struct.pack("<IH", uid, 23) + values.tobytes() + padding,
    )

    assert isinstance(packet.unique_packet_id, int)
    assert packet.pfb_bin == 23
    assert all(getattr(packet, name).shape == (64,)
               for name in ("AA", "BB", "ABR", "ABI"))
    assert packet.ABI[-1] == 255


@pytest.mark.parametrize("padding", [b"\xA5", b"\xA5\x5A\xC3"])
def test_zoom_rejects_wrong_padding_without_zero_arrays(padding):
    values = np.arange(256, dtype="<f4")
    packet = Packet_Cal_ZoomSpectra(
        0x270,
        blob=struct.pack("<IH", 802, 23) + values.tobytes() + padding,
        strict=False,
    )

    assert packet.decode_status.codes == ("bad_blob_length",)
    assert not any(hasattr(packet, name) for name in ("AA", "BB", "ABR", "ABI"))
