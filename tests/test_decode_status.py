import ctypes

import pytest

from uncrater.PacketBase import PacketBase, Packet_Unsupported, cdi_rounded_size
from uncrater.decode_status import DecodeStatus


class TinyStruct(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("value", ctypes.c_uint16)]


def test_decode_status_serialization_and_counts_are_deterministic():
    status = DecodeStatus()
    status.add("zeta", "last", appid=0x210, details={"b": 2, "a": 1})
    status.add("alpha", "first", source="packet.bin")
    status.add("zeta", "again")

    assert status.codes == ("zeta", "alpha", "zeta")
    assert status.counts() == {"alpha": 1, "zeta": 2}
    assert status.as_dict()["issues"][0]["details"] == {"a": 1, "b": 2}


def test_nonfatal_issue_keeps_decoded_data_available():
    packet = PacketBase(0x210, blob=b"payload")
    packet.data = b"decoded"
    packet._issue("crc_mismatch", "CRC did not match")

    assert packet.data == b"decoded"
    assert packet.decode_status.codes == ("crc_mismatch",)
    assert not packet.decode_status.ok
    assert not packet.decode_status.issues[0].fatal


def test_file_read_errors_propagate(tmp_path):
    path = tmp_path / "0001_02F0.bin"
    packet = PacketBase(0x2F0, blob_fn=path)

    with pytest.raises(FileNotFoundError):
        packet.read()


def test_blob_property_is_read_only_and_xxd_uses_loaded_bytes():
    packet = PacketBase(0x999, blob=b"\x00\x01\xFE\xFF")

    assert packet.blob == b"\x00\x01\xFE\xFF"
    assert "0000" in packet.xxd()
    assert "00 01 FE FF" in packet.xxd()
    with pytest.raises(AttributeError):
        packet.blob = b"other"


def test_length_and_struct_helpers_do_not_publish_invalid_data():
    packet = PacketBase(0x999, blob=b"\x01", strict=False)

    assert packet._decode_struct(TinyStruct) is None
    assert packet.decode_status.codes == ("bad_blob_length",)
    assert not hasattr(packet, "value")
    assert cdi_rounded_size(5) == 8


def test_declared_version_mismatch_uses_structural_failure_policy():
    packet = PacketBase(0x20F, blob=b"", reported_version=0x307, strict=False)

    assert not packet._check_declared_version(0x305)
    assert packet.decode_status.codes == ("declared_version_mismatch",)


def test_diagnostic_unknown_schema_records_the_selected_fallback():
    packet = PacketBase(
        0x210,
        blob=b"",
        reported_version=0x399,
        diagnostic_override=True,
        strict=False,
    )

    assert packet.schema_assumed
    assert packet.decode_status.codes == ("unknown_schema",)
    assert packet.decode_status.issues[0].details == (
        ("selected_binding", packet.schema.binding_key),
    )


def test_unsupported_packet_uses_structural_failure_policy():
    packet = Packet_Unsupported(0x2E0, blob=b"payload", strict=False)

    assert packet.decode_status.codes == ("unsupported_format",)
    assert not hasattr(packet, "data")
