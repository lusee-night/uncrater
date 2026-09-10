from dataclasses import FrozenInstanceError

import pytest

from uncrater.coreloop import (
    pycoreloop_203,
    pycoreloop_305,
    pycoreloop_306_early,
    pycoreloop_306_final,
    pycoreloop_307,
)
from uncrater.schema_registry import (
    AmbiguousSchemaError,
    BINDINGS,
    BINDINGS_BY_KEY,
    LATEST_BINDING,
    SchemaConflictError,
    SchemaEvidence,
    UnknownSchemaError,
    UnsupportedSchemaError,
    UnsupportedSchemaVariantError,
    binding_for_key,
    binding_for_wire_version,
    evidence_from_packet,
    resolve_wire_version,
    resolve_packet_stream,
    schema_resolution_record,
    schema_resolution_from_record,
    schema_assumed_for,
)


EXPECTED_SOURCES = {
    "203": ("2r03", "798da926b6c4af0ea410ddf0c4191cb15fbcf9e3"),
    "305": ("3r05", "9355df3c89055cee84b6fee69dbfcd199487e0aa"),
    "306-early": (
        "3r06-early",
        "9e8db56c0e723968d2c01c26f32bf727a1a7a014",
    ),
    "306-final": (
        "3r06-final",
        "bb016489adb1d209e36fec814d928e38454aa5d4",
    ),
    "307": ("3r09", "38770b94bd20dfdbf52d1d8b872a716537b851f3"),
}

EXPECTED_MODULES = {
    "203": pycoreloop_203,
    "305": pycoreloop_305,
    "306-early": pycoreloop_306_early,
    "306-final": pycoreloop_306_final,
    "307": pycoreloop_307,
}


def test_frozen_bindings_have_exact_source_provenance():
    assert tuple(binding.binding_key for binding in BINDINGS) == (
        "203",
        "305",
        "306-early",
        "306-final",
        "307",
    )
    for key, (release, commit) in EXPECTED_SOURCES.items():
        binding = BINDINGS_BY_KEY[key]
        module = EXPECTED_MODULES[key]
        assert binding.source_release == release
        assert binding.source_commit == commit
        assert binding.pystruct is module.pystruct
        assert binding.appids is module.appId
        assert binding.commands is module.command
        assert binding.errors is module._errors
        assert binding.pystruct.VERSION_ID == binding.canonical_schema_id
        assert binding.abi_fingerprint == binding.abi["sha256"]
        assert len(binding.abi_fingerprint) == 64
        with pytest.raises(FrozenInstanceError):
            binding.source_commit = "0" * 40


def test_binding_provenance_is_deeply_immutable():
    provenance = LATEST_BINDING.provenance
    with pytest.raises(TypeError):
        provenance["source_release"] = "changed"
    with pytest.raises(TypeError):
        provenance["source_files"]["new"] = "hash"
    with pytest.raises(TypeError):
        LATEST_BINDING.abi["sha256"] = "0" * 64


def test_latest_is_pinned_3r09_wire_307():
    assert LATEST_BINDING is binding_for_key("307")
    assert LATEST_BINDING.canonical_schema_id == 0x307
    assert LATEST_BINDING.source_release == "3r09"


def test_306_bindings_preserve_one_reported_id_and_two_variants():
    early = binding_for_key("306-early")
    final = binding_for_key("306-final")
    assert early.accepted_reported_versions == (0x306,)
    assert final.accepted_reported_versions == (0x306,)
    assert early.canonical_schema_id == final.canonical_schema_id == 0x306
    assert early.variant == "early"
    assert final.variant == "final"


@pytest.mark.parametrize(
    ("reported_version", "binding_key"),
    [(0x203, "203"), (0x305, "305"), (0x307, "307")],
)
def test_unambiguous_reported_versions_select_exact_binding(
    reported_version, binding_key
):
    resolution = resolve_wire_version(reported_version)
    assert resolution.binding is BINDINGS_BY_KEY[binding_key]
    assert resolution.reported_version == reported_version
    assert resolution.canonical_schema_id == reported_version
    assert not resolution.schema_assumed
    assert resolution.issue_code is None


def test_missing_version_assumes_latest():
    resolution = resolve_wire_version(None)
    assert resolution.binding is LATEST_BINDING
    assert resolution.reported_version is None
    assert resolution.schema_assumed
    assert resolution.issue_code is None
    assert binding_for_wire_version(None) is LATEST_BINDING
    assert schema_assumed_for(None)
    with pytest.raises(FrozenInstanceError):
        resolution.reported_version = 0x307


@pytest.mark.parametrize("reported_version", [0x300, 0x302, 0x308, 0x309])
def test_known_unsupported_versions_fail_even_with_diagnostic_override(
    reported_version,
):
    with pytest.raises(UnsupportedSchemaError) as error:
        binding_for_wire_version(reported_version)
    assert error.value.code == "unsupported_schema"
    with pytest.raises(UnsupportedSchemaError):
        binding_for_wire_version(
            reported_version,
            diagnostic_override=True,
        )


def test_unknown_version_requires_explicit_diagnostic_override():
    with pytest.raises(UnknownSchemaError) as error:
        resolve_wire_version(0x40A)
    assert isinstance(error.value, UnsupportedSchemaError)
    assert error.value.code == "unknown_schema"

    resolution = resolve_wire_version(0x40A, diagnostic_override=True)
    assert resolution.binding is LATEST_BINDING
    assert resolution.reported_version == 0x40A
    assert resolution.schema_assumed
    assert resolution.issue_code == "unknown_schema"
    assert (
        binding_for_wire_version(0x40A, diagnostic_override=True)
        is LATEST_BINDING
    )
    assert schema_assumed_for(0x40A, diagnostic_override=True)


@pytest.mark.parametrize(
    ("evidence", "binding_key"),
    [
        (SchemaEvidence(0x206, 2571, 0), "306-early"),
        (SchemaEvidence(0x206, 2572, 0), "306-early"),
        (SchemaEvidence(0x280, 590), "306-early"),
        (SchemaEvidence(0x280, 592), "306-early"),
        (SchemaEvidence(0x206, 2692, 0), "306-final"),
        (SchemaEvidence(0x206, 90, 100), "306-final"),
        (SchemaEvidence(0x206, 92, 100), "306-final"),
        (SchemaEvidence(0x206, 48, 101), "306-final"),
        (SchemaEvidence(0x280, 597), "306-final"),
        (SchemaEvidence(0x280, 600), "306-final"),
    ],
)
def test_306_packet_signatures_select_only_verified_variants(
    evidence, binding_key
):
    resolution = resolve_wire_version(0x306, evidence=evidence)
    assert resolution.binding is BINDINGS_BY_KEY[binding_key]
    assert resolution.reported_version == 0x306
    assert not resolution.schema_assumed


def test_306_matching_explicit_early_variant_still_requires_evidence():
    assert (
        binding_for_wire_version(
            0x306,
            variant="early",
            evidence=SchemaEvidence(0x206, 2571, 0),
        ).binding_key
        == "306-early"
    )


def test_306_matching_explicit_final_variant_still_requires_evidence():
    assert (
        binding_for_wire_version(
            0x306,
            variant="final",
            evidence=SchemaEvidence(0x206, 2692, 0),
        ).binding_key
        == "306-final"
    )


@pytest.mark.parametrize("variant", [None, "early", "final"])
def test_306_without_discriminating_evidence_is_ambiguous(variant):
    with pytest.raises(AmbiguousSchemaError) as error:
        binding_for_wire_version(0x306, variant=variant)
    assert error.value.code == "ambiguous_schema"

    with pytest.raises(AmbiguousSchemaError):
        binding_for_wire_version(
            0x306,
            variant=variant,
            evidence=SchemaEvidence(0x209, 30),
        )


def test_306_housekeeping_length_without_type_is_not_enough():
    with pytest.raises(AmbiguousSchemaError):
        binding_for_wire_version(
            0x306,
            variant="early",
            evidence=SchemaEvidence(0x206, 2571),
        )


@pytest.mark.parametrize("payload_length", [2573, 2700, 2709, 2711, 2713, 2714])
def test_unverified_306_housekeeping_layouts_fail_closed(payload_length):
    with pytest.raises(UnsupportedSchemaVariantError) as error:
        binding_for_wire_version(
            0x306,
            evidence=SchemaEvidence(0x206, payload_length, 0),
        )
    assert error.value.code == "unsupported_schema_variant"


def test_conflicting_306_evidence_fails_closed():
    evidence = (
        SchemaEvidence(0x206, 2571, 0),
        SchemaEvidence(0x280, 597),
    )
    with pytest.raises(SchemaConflictError) as error:
        binding_for_wire_version(0x306, evidence=evidence)
    assert error.value.code == "schema_conflict"

    with pytest.raises(SchemaConflictError):
        binding_for_wire_version(
            0x306,
            variant="early",
            evidence=SchemaEvidence(0x206, 2692, 0),
        )


def test_supported_and_unverified_306_evidence_fails_closed():
    evidence = (
        SchemaEvidence(0x206, 2571, 0),
        SchemaEvidence(0x206, 2700, 0),
    )
    with pytest.raises(SchemaConflictError):
        binding_for_wire_version(0x306, evidence=evidence)

    with pytest.raises(UnsupportedSchemaVariantError):
        binding_for_wire_version(
            0x306,
            variant="early",
            evidence=SchemaEvidence(0x206, 2700, 0),
        )


def test_housekeeping_packet_provides_schema_evidence():
    blob = bytearray(2571)
    blob[10:12] = (0).to_bytes(2, "little")
    evidence = evidence_from_packet(0x206, bytes(blob))
    assert evidence == SchemaEvidence(0x206, 2571, 0)
    assert binding_for_wire_version(0x306, evidence=evidence).binding_key == "306-early"


def test_variant_is_rejected_for_other_version_states():
    with pytest.raises(SchemaConflictError):
        binding_for_wire_version(0x307, variant="final")
    with pytest.raises(SchemaConflictError):
        binding_for_wire_version(None, variant="final")


def input_schema_packets(key, hk_type=0):
    binding = binding_for_key(key)
    hello = binding.pystruct.startup_hello()
    hello.SW_version = binding.canonical_schema_id
    hk = getattr(binding.pystruct, f"housekeeping_data_{hk_type}")()
    hk.base.version = binding.canonical_schema_id
    hk.base.housekeeping_type = hk_type
    return [(0x209, bytes(hello)), (0x206, bytes(hk))]


@pytest.mark.parametrize("key", ["306-early", "306-final"])
def test_full_input_schema_proof_round_trips_and_decodes_subsets(tmp_path, key):
    from uncrater import Collection

    resolution = resolve_packet_stream(input_schema_packets(key))
    assert resolution.binding.binding_key == key
    assert resolution.evidence
    restored = schema_resolution_from_record(schema_resolution_record(resolution))
    assert restored == resolution
    subset = input_schema_packets(key, hk_type=1)
    assert resolve_packet_stream(subset, inherited=restored).binding is resolution.binding
    for index, (appid, blob) in enumerate(subset):
        (tmp_path / f"{index:05d}_{appid:04x}.bin").write_bytes(blob)
    collection = Collection(tmp_path, schema_resolution=restored)
    assert collection.selected_schema_bindings == (key,)
    assert len(collection.housekeeping_packets) == 1
    assert collection.decode_status.ok
    assert collection.canonical_report()["input_schema"] == schema_resolution_record(restored)


@pytest.mark.parametrize("change", ["version", "evidence", "variant"])
def test_inherited_schema_rejects_local_contradictions(change):
    resolution = resolve_packet_stream(input_schema_packets("306-early"))
    packets = input_schema_packets("306-final" if change == "evidence" else "307")
    options = {}
    if change == "variant":
        packets = []
        options["variant"] = "final"
    with pytest.raises(SchemaConflictError):
        resolve_packet_stream(packets, inherited=resolution, **options)


def test_full_input_schema_rejects_mixed_versions():
    with pytest.raises(SchemaConflictError):
        resolve_packet_stream(input_schema_packets("306-early") + input_schema_packets("307"))


@pytest.mark.parametrize("field, value", [("binding_key", "307"), ("abi_fingerprint", "0" * 64),
                                           ("schema_assumed", True), ("reported_version", True),
                                           ("evidence", [{"appid": False, "payload_length": 2572, "housekeeping_type": 0}])])
def test_stored_schema_rejects_malformed_or_forged_claims(field, value):
    from uncrater.schema_registry import SchemaResolutionError

    record = schema_resolution_record(resolve_packet_stream(input_schema_packets("306-early")))
    record[field] = value
    with pytest.raises(SchemaResolutionError):
        schema_resolution_from_record(record)


@pytest.mark.parametrize("key", ["306-early", "306-final"])
def test_versionless_subset_inherits_effective_reported_version(tmp_path, key):
    import numpy as np
    from uncrater import Collection

    resolution = resolve_packet_stream(input_schema_packets(key))
    metadata = resolution.binding.pystruct.waveform_metadata()
    metadata.unique_packet_id = 9
    (tmp_path / "00000_02f0.bin").write_bytes(np.zeros(16384, dtype="<u2").tobytes())
    (tmp_path / "00001_02fa.bin").write_bytes(bytes(metadata))
    collection = Collection(tmp_path, schema_resolution=resolution)
    assert collection.reported_schema_ids == (0x306,)
    assert len(collection.waveform_groups) == 1
    assert all(packet.reported_version == 0x306 for packet in collection.cont)
