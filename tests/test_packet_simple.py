import ctypes
import struct

import numpy as np
import pytest

from uncrater import (
    Packet,
    Packet_Bootloader,
    Packet_EOS,
    Packet_Heartbeat,
    Packet_Hello,
    Packet_Housekeep,
    Packet_Watchdog,
    Packet_Waveform,
    Packet_Waveform_Meta,
)
from uncrater.decode_status import PacketDecodeError
from uncrater.schema_registry import BINDINGS_BY_KEY, LATEST_BINDING


CL = LATEST_BINDING.pystruct


def bytes_of(value):
    return ctypes.string_at(ctypes.addressof(value), ctypes.sizeof(value))


def padded(value, padding=b"\xA5\x5A\xC3"):
    payload = bytes_of(value)
    count = (-len(payload)) % 4
    return payload + padding[:count]


def test_known_simple_packets_decode_without_changing_their_public_fields():
    hello_value = CL.startup_hello()
    hello_value.SW_version = 0x307
    hello_value.FW_Version = 0x11223344
    hello_value.FW_ID = 7
    hello_value.unique_packet_id = 99
    hello = Packet(0x209, blob=padded(hello_value, b"\xDE\xAD"))
    assert isinstance(hello, Packet_Hello)
    assert hello.schema.binding_key == "307"
    assert hello.FW_Version == 0x11223344
    assert hello.unique_packet_id == 99

    heartbeat_value = CL.heartbeat()
    heartbeat_value.packet_count = 42
    heartbeat_value.time_32 = 16
    heartbeat_value.magic = b"BRNMRL"
    heartbeat = Packet(0x20A, blob=bytes_of(heartbeat_value))
    assert isinstance(heartbeat, Packet_Heartbeat)
    assert heartbeat.packet_count == 42
    assert heartbeat.ok

    eos_value = CL.end_of_sequence()
    eos_value.unique_packet_id = 123
    eos_value.eos_arg = 9
    eos = Packet(0x207, blob=bytes_of(eos_value))
    assert isinstance(eos, Packet_EOS)
    assert (eos.unique_packet_id, eos.eos_arg) == (123, 9)

    watchdog_value = CL.watchdog_packet()
    watchdog_value.unique_packet_id = 17
    watchdog_value.uC_time = 0x0000123456789ABC
    watchdog_value.tripped = 3
    for appid in (0x20C, 0x2FF):
        watchdog = Packet(appid, blob=padded(watchdog_value, b"\xEF"))
        assert isinstance(watchdog, Packet_Watchdog)
        assert watchdog.unique_packet_id == 17
        assert watchdog.tripped == 3

    bootloader = Packet(
        0x208,
        blob=struct.pack(
            "<8I3I",
            1,
            2,
            16,
            0,
            0x20260820,
            0x123456,
            3,
            0xFEEDFACE,
            4,
            5,
            6,
        ),
    )
    assert isinstance(bootloader, Packet_Bootloader)
    assert bootloader.magic
    np.testing.assert_array_equal(bootloader.payload, [4, 5, 6])

    for packet in (hello, heartbeat, eos, watchdog, bootloader):
        assert packet.decode_status.ok
        assert packet.is_read


@pytest.mark.parametrize("binding_key", ["203", "305"])
def test_historical_simple_packets_use_the_selected_pystruct(binding_key):
    binding = BINDINGS_BY_KEY[binding_key]
    version = binding.accepted_reported_versions[0]

    hello_value = binding.pystruct.startup_hello()
    hello_value.SW_version = version
    hello_value.unique_packet_id = 31
    hello = Packet(0x209, blob=padded(hello_value))
    assert hello.schema is binding
    assert hello.unique_packet_id == 31

    heartbeat_value = binding.pystruct.heartbeat()
    heartbeat_value.packet_count = 23
    heartbeat_value.magic = b"BRNMRL"
    heartbeat = Packet(
        0x20A,
        blob=bytes_of(heartbeat_value),
        reported_version=version,
    )
    assert heartbeat.schema is binding
    assert heartbeat.packet_count == 23


@pytest.mark.parametrize("hk_type", [0, 1, 2, 3, 100, 101])
def test_all_latest_housekeeping_structures_decode(hk_type):
    value = getattr(CL, f"housekeeping_data_{hk_type}")()
    value.base.version = 0x307
    value.base.unique_packet_id = 100 + hk_type
    value.base.housekeeping_type = hk_type
    if hk_type == 0:
        value.core_state.base.ADC_stat[0].valid_count = 4
        value.core_state.base.ADC_stat[0].sumv = 4 * 0x1FFF
    elif hk_type == 1:
        value.actual_gain[:] = (0, 1, 2, 0)
        value.ADC_stat[0].valid_count = 4
        value.ADC_stat[0].sumv = 4 * 0x1FFF
    elif hk_type == 2:
        value.heartbeat.magic = b"BRNMRL"

    packet = Packet(0x206, blob=padded(value, b"\xFF\xEE\xDD"))

    assert isinstance(packet, Packet_Housekeep)
    assert packet.hk_type == hk_type
    assert packet.unique_packet_id == 100 + hk_type
    assert packet.decode_status.ok
    if hk_type in (0, 1):
        assert packet.adc_valid_count[0] == 4
        assert packet.valid_count is packet.adc_valid_count
    if hk_type == 0:
        assert packet.telemetry == {
            "V1_0": 0.0,
            "V1_8": 0.0,
            "V2_5": 0.0,
            "T_FPGA": -273.15,
        }
        assert packet.telemetry_T_FPGA == -273.15
    elif hk_type == 1:
        assert packet.actual_gain == ["L", "M", "H", "L"]
    elif hk_type == 2:
        assert packet.ok


@pytest.mark.parametrize("binding_key", ["203", "305", "306-early", "306-final"])
def test_historical_housekeeping_type_zero_uses_its_exact_abi(binding_key):
    binding = BINDINGS_BY_KEY[binding_key]
    value = binding.pystruct.housekeeping_data_0()
    value.base.version = binding.accepted_reported_versions[0]
    value.base.unique_packet_id = 41
    value.base.housekeeping_type = 0

    packet = Packet(0x206, blob=padded(value))

    assert packet.schema is binding
    assert packet.unique_packet_id == 41
    assert packet.hk_type == 0
    assert packet.decode_status.ok


def test_housekeeping_rejects_unknown_types_and_invalid_gain_values():
    unknown = bytearray(ctypes.sizeof(CL.housekeeping_data_base))
    struct.pack_into("<H", unknown, 0, 0x307)
    struct.pack_into("<H", unknown, 10, 99)
    unknown_packet = Packet(0x206, blob=bytes(unknown), strict=False)
    assert unknown_packet.decode_status.codes == ("unsupported_format",)
    assert not hasattr(unknown_packet, "hk_type")

    invalid_gain = CL.housekeeping_data_1()
    invalid_gain.base.version = 0x307
    invalid_gain.base.housekeeping_type = 1
    invalid_gain.actual_gain[:] = (0, 1, 3, 0)
    gain_packet = Packet(0x206, blob=padded(invalid_gain), strict=False)
    assert gain_packet.decode_status.codes == ("payload_decode_failed",)
    assert not hasattr(gain_packet, "actual_gain")


def test_heartbeat_and_bootloader_bad_magic_are_nonfatal_findings():
    heartbeat_value = CL.heartbeat()
    heartbeat_value.packet_count = 42
    heartbeat_value.magic = b"WRONG!"
    heartbeat = Packet(0x20A, blob=bytes_of(heartbeat_value))
    assert not heartbeat.ok
    assert heartbeat.packet_count == 42
    assert heartbeat.decode_status.codes == ("invalid_magic",)
    assert not heartbeat.decode_status.issues[0].fatal

    bootloader_blob = struct.pack(
        "<8I",
        0,
        3,
        0,
        0,
        0,
        0,
        0,
        0xDEADBEEF,
    )
    bootloader = Packet(0x208, blob=bootloader_blob)
    assert not bootloader.magic
    assert bootloader.seq == 3
    assert bootloader.payload.size == 0
    assert bootloader.decode_status.codes == ("invalid_magic",)
    assert not bootloader.decode_status.issues[0].fatal


def test_bootloader_payload_length_mismatch_does_not_fabricate_payload():
    blob = struct.pack(
        "<8I1I",
        0,
        0,
        0,
        0,
        0,
        0,
        2,
        0xFEEDFACE,
        11,
    )
    packet = Packet(0x208, blob=blob, strict=False)

    assert packet.decode_status.codes == ("bad_blob_length",)
    assert not hasattr(packet, "payload")


def test_waveform_signed_values_channel_and_exact_length():
    samples = np.zeros(16_384, dtype="<u2")
    samples[:4] = (0, 8192, 8193, 16383)
    packet = Packet(0x2F2, blob=samples.tobytes())

    assert isinstance(packet, Packet_Waveform)
    assert packet.ch == 2
    assert packet.waveform.shape == (16_384,)
    assert packet.waveform.dtype == np.int16
    np.testing.assert_array_equal(packet.waveform[:4], [0, -8192, -8191, -1])

    for malformed in (samples.tobytes()[:-2], samples.tobytes() + b"\x00\x00"):
        failed = Packet(0x2F2, blob=malformed, strict=False)
        assert failed.decode_status.codes == ("bad_blob_length",)
        assert not hasattr(failed, "waveform")


def test_following_waveform_metadata_attaches_only_after_a_valid_decode():
    waveform = Packet(0x2F0, blob=bytes(2 * 16_384))
    metadata_value = CL.waveform_metadata()
    metadata_value.unique_packet_id = 91
    metadata_value.time_32 = 16
    metadata_value.timestamp = 0x1122334455667788
    metadata = Packet(0x2FA, blob=padded(metadata_value, b"\x99\x88"))

    assert isinstance(metadata, Packet_Waveform_Meta)
    assert metadata.is_read
    metadata.set_packets([waveform])
    assert waveform.meta is metadata
    assert waveform.timestamp == 0x1122334455667788

    next_waveform = Packet(0x2F1, blob=bytes(2 * 16_384))
    malformed = Packet(0x2FA, blob=bytes(17), strict=False)
    malformed.set_packets([next_waveform])
    assert malformed.decode_status.codes == ("bad_blob_length",)
    assert next_waveform.meta is None
    assert next_waveform.timestamp == 0xFFFFFFFFFFFFFFFF


def test_diagnostic_unknown_schema_metadata_still_attaches_decoded_timestamp():
    waveform = Packet(0x2F0, blob=bytes(2 * 16_384))
    metadata_value = CL.waveform_metadata()
    metadata_value.timestamp = 0x0123456789ABCDEF
    metadata = Packet(
        0x2FA,
        blob=padded(metadata_value),
        reported_version=0x399,
        diagnostic_override=True,
        strict=False,
    )

    assert metadata.decode_status.codes == ("unknown_schema",)
    metadata.set_packets([waveform])
    assert waveform.meta is metadata
    assert waveform.timestamp == 0x0123456789ABCDEF


@pytest.mark.parametrize(
    ("appid", "blob", "missing_field"),
    [
        (0x209, struct.pack("<I", 0x307), "SW_version"),
        (0x20A, bytes(ctypes.sizeof(CL.heartbeat) - 1), "packet_count"),
        (0x207, bytes(ctypes.sizeof(CL.end_of_sequence) - 1), "eos_arg"),
        (0x20C, bytes(ctypes.sizeof(CL.watchdog_packet) - 1), "tripped"),
        (0x208, bytes(31), "header"),
        (0x2F0, bytes(2 * 16_384 - 2), "waveform"),
        (0x2FA, bytes(ctypes.sizeof(CL.waveform_metadata) - 1), "timestamp"),
    ],
)
def test_malformed_simple_packets_record_typed_failure_without_fields(
    appid, blob, missing_field
):
    packet = Packet(appid, blob=blob, strict=False)

    assert packet.decode_status.codes == ("bad_blob_length",)
    assert packet.is_read
    assert not hasattr(packet, missing_field)


def test_malformed_housekeeping_does_not_publish_prefix_fields():
    blob = bytearray(ctypes.sizeof(CL.housekeeping_data_base))
    struct.pack_into("<H", blob, 0, 0x307)
    struct.pack_into("<H", blob, 10, 0)
    packet = Packet(0x206, blob=bytes(blob), strict=False)

    assert packet.decode_status.codes == ("bad_blob_length",)
    assert not hasattr(packet, "base")
    assert not hasattr(packet, "hk_type")


def test_structural_failure_raises_by_default():
    with pytest.raises(PacketDecodeError) as caught:
        Packet(0x2F0, blob=bytes(2 * 16_384 - 2))

    assert caught.value.code == "bad_blob_length"
