import importlib
import struct

import pytest

from uncrater.PacketBase import PacketBase, Packet_Unsupported
from uncrater.Packet_Hello import Packet_Hello
from uncrater.Packet_Housekeep import Packet_Housekeep
from uncrater.Packet_Spectrum import Packet_Metadata, Packet_Spectrum
from uncrater.Packet_Waveform import Packet_Waveform
from uncrater.schema_registry import (
    AmbiguousSchemaError,
    BINDINGS_BY_KEY,
    SchemaConflictError,
    SchemaEvidence,
    UnsupportedSchemaError,
)


packet_module = importlib.import_module("uncrater.Packet")
dispatch_module = importlib.import_module("uncrater.packet_dispatch")


def test_packet_base_records_binding_metadata():
    packet = PacketBase(0x123, blob_fn="unused")

    assert packet.schema is BINDINGS_BY_KEY["307"]
    assert packet.schema_id == 0x307
    assert packet.reported_version is None
    assert packet.schema_assumed
    assert packet.binding_provenance["binding_key"] == "307"


def test_packet_base_rejects_conflicting_version_aliases():
    with pytest.raises(SchemaConflictError, match="version and reported_version"):
        PacketBase(
            0x123,
            blob_fn="unused",
            version=0x203,
            reported_version=0x305,
        )


@pytest.mark.parametrize(
    ("reported_version", "binding_key"),
    [(0x203, "203"), (0x305, "305"), (0x307, "307")],
)
def test_packet_base_resolves_exact_reported_versions(
    reported_version, binding_key
):
    packet = PacketBase(
        0x123,
        blob_fn="unused",
        reported_version=reported_version,
    )

    assert packet.schema is BINDINGS_BY_KEY[binding_key]
    assert packet.schema_id == reported_version
    assert packet.reported_version == reported_version
    assert not packet.schema_assumed


def test_packet_base_uses_306_packet_evidence():
    packet = PacketBase(
        0x206,
        blob_fn="unused",
        reported_version=0x306,
        evidence=SchemaEvidence(0x206, 2571, 0),
    )

    assert packet.schema is BINDINGS_BY_KEY["306-early"]
    assert packet.schema_id == 0x306
    assert packet.reported_version == 0x306
    assert not packet.schema_assumed


def test_packet_base_rejects_306_evidence_conflicting_with_session_binding():
    with pytest.raises(SchemaConflictError):
        PacketBase(
            0x206,
            blob_fn="unused",
            schema=BINDINGS_BY_KEY["306-final"],
            reported_version=0x306,
            evidence=SchemaEvidence(0x206, 2571, 0),
        )


def test_historical_only_appid_dispatch_depends_on_binding():
    # blob_fn keeps dispatch tests independent of typed historical decoders
    historical = packet_module.Packet(0x2D0, blob_fn="unused", version=0x203)
    latest = packet_module.Packet(0x2D0, blob_fn="unused", version=0x307)

    assert isinstance(historical, Packet_Spectrum)
    assert historical.schema.binding_key == "203"
    assert type(latest) is PacketBase
    assert latest.schema.binding_key == "307"


def test_factory_still_requires_a_blob_or_filename():
    with pytest.raises(ValueError):
        packet_module.Packet(0x209)


def test_dispatch_mappings_are_cached_by_binding_key():
    dispatch_module.packet_dict_for_binding.cache_clear()

    first = dispatch_module.packet_dict_for_binding("203")
    second = dispatch_module.packet_dict_for_binding("203")
    latest = dispatch_module.packet_dict_for_binding("307")

    assert first is second
    assert latest == packet_module.PacketDict
    assert dispatch_module.packet_dict_for_binding.cache_info().hits == 1


def test_factory_normalizes_only_dcb_waveform_appid():
    normalized = packet_module.Packet(0x4F0, blob_fn="unused")
    untouched = packet_module.Packet(0x4F1, blob_fn="unused")

    assert isinstance(normalized, Packet_Waveform)
    assert normalized.appid == 0x2F0
    assert normalized.original_appid == 0x4F0
    assert type(untouched) is PacketBase
    assert untouched.appid == 0x4F1
    assert untouched.original_appid == 0x4F1


@pytest.mark.parametrize("appid", range(0x2E0, 0x2E4))
def test_fw_direct_spectra_are_explicitly_unsupported(appid):
    packet = packet_module.Packet(appid, blob=b"payload", strict=False)

    assert type(packet) is Packet_Unsupported
    assert packet.decode_status.codes == ("unsupported_format",)
    assert not hasattr(packet, "data")


@pytest.mark.parametrize(
    ("appid", "payload", "reported_version"),
    [
        (0x209, struct.pack("<I", 0x203), 0x203),
        (0x20F, struct.pack("<H", 0x305), 0x305),
        (0x206, struct.pack("<H", 0x307), 0x307),
    ],
)
def test_bootstrap_reads_fixed_version_prefix_from_blob(
    appid, payload, reported_version
):
    kwargs = {}

    dispatch_module.bootstrap_schema(appid, payload, None, kwargs)

    assert kwargs["reported_version"] == reported_version


@pytest.mark.parametrize(
    ("appid", "payload"),
    [
        (0x209, struct.pack("<I", 0x203)),
        (0x20F, struct.pack("<H", 0x203)),
        (0x206, struct.pack("<H", 0x203)),
        (0x280, struct.pack("<H", 0x203)),
    ],
)
def test_bootstrap_rejects_packet_version_conflicting_with_session(
    appid, payload
):
    with pytest.raises(SchemaConflictError, match="session version"):
        dispatch_module.bootstrap_schema(
            appid,
            payload,
            None,
            {"reported_version": 0x307},
        )


@pytest.mark.parametrize(
    ("appid", "payload", "PacketType", "binding_key"),
    [
        (0x209, struct.pack("<I", 0x203), Packet_Hello, "203"),
        (0x20F, struct.pack("<H", 0x305), Packet_Metadata, "305"),
    ],
)
def test_factory_bootstraps_version_from_file(
    tmp_path, appid, payload, PacketType, binding_key
):
    packet_path = tmp_path / "packet.bin"
    packet_path.write_bytes(payload)

    packet = packet_module.Packet(appid, blob_fn=packet_path)

    assert isinstance(packet, PacketType)
    assert packet.reported_version == int(binding_key, 16)
    assert packet.schema.binding_key == binding_key
    assert not packet.schema_assumed


@pytest.mark.parametrize(
    ("payload_length", "binding_key"),
    [(2571, "306-early"), (2692, "306-final")],
)
def test_factory_uses_306_housekeeping_length_evidence(
    tmp_path, payload_length, binding_key
):
    payload = bytearray(payload_length)
    struct.pack_into("<H", payload, 0, 0x306)
    struct.pack_into("<H", payload, 10, 0)
    packet_path = tmp_path / "housekeeping.bin"
    packet_path.write_bytes(payload)

    packet = packet_module.Packet(0x206, blob_fn=packet_path)

    assert isinstance(packet, Packet_Housekeep)
    assert packet.reported_version == 0x306
    assert packet.schema.binding_key == binding_key
    assert not packet.schema_assumed


@pytest.mark.parametrize(
    ("session_length", "packet_length"),
    [(2571, 2692), (2692, 2571)],
)
def test_factory_rejects_conflicting_306_session_and_packet_evidence(
    session_length, packet_length
):
    payload = bytearray(packet_length)
    struct.pack_into("<H", payload, 0, 0x306)
    struct.pack_into("<H", payload, 10, 0)

    with pytest.raises(SchemaConflictError, match="conflicting 0x306 ABIs"):
        packet_module.Packet(
            0x206,
            blob=bytes(payload),
            reported_version=0x306,
            evidence=SchemaEvidence(0x206, session_length, 0),
        )


@pytest.mark.parametrize(
    ("payload_length", "binding_key"),
    [(590, "306-early"), (597, "306-final")],
)
def test_factory_uses_306_calibrator_metadata_length_evidence(
    tmp_path, payload_length, binding_key
):
    payload = bytearray(payload_length)
    struct.pack_into("<H", payload, 0, 0x306)
    packet_path = tmp_path / "calibrator_metadata.bin"
    packet_path.write_bytes(payload)

    packet = packet_module.Packet(0x280, blob_fn=packet_path)

    assert packet.reported_version == 0x306
    assert packet.schema.binding_key == binding_key
    assert not packet.schema_assumed


def test_306_hello_without_abi_evidence_is_ambiguous(tmp_path):
    packet_path = tmp_path / "hello.bin"
    packet_path.write_bytes(struct.pack("<I", 0x306))

    with pytest.raises(AmbiguousSchemaError):
        packet_module.Packet(0x209, blob_fn=packet_path)


@pytest.mark.parametrize("reported_version", [0x300, 0x302, 0x308, 0x309])
def test_factory_rejects_known_unsupported_versions(reported_version):
    with pytest.raises(UnsupportedSchemaError):
        packet_module.Packet(
            0x210,
            blob_fn="unused",
            reported_version=reported_version,
        )


def test_diagnostic_override_preserves_unknown_reported_version():
    packet = packet_module.Packet(
        0x555,
        blob_fn="unused",
        reported_version=0x40A,
        diagnostic_override=True,
    )

    assert type(packet) is PacketBase
    assert packet.schema.binding_key == "307"
    assert packet.reported_version == 0x40A
    assert packet.schema_assumed


def test_packetdict_remains_compatibility_only():
    assert packet_module.PacketDict == dispatch_module.packet_dict_for_binding("307")
    assert "PacketDict" not in packet_module.__all__
