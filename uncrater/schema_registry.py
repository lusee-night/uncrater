"""Frozen coreloop schema bindings and wire-version resolution."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib.resources import files
import json
import struct
from types import MappingProxyType
from typing import Any

from .coreloop import (
    pycoreloop_203,
    pycoreloop_305,
    pycoreloop_306_early,
    pycoreloop_306_final,
    pycoreloop_307,
)


class SchemaResolutionError(ValueError):
    """Base class for controlled schema-resolution failures."""

    code = "schema_resolution_error"


class UnsupportedSchemaError(SchemaResolutionError):
    """Raised when a known wire version has no verified frozen binding."""

    code = "unsupported_schema"

    def __init__(self, reported_version: int):
        self.reported_version = reported_version
        super().__init__(
            f"Unsupported coreloop wire schema 0x{reported_version:X}"
        )


class UnknownSchemaError(UnsupportedSchemaError):
    """Raised for an unknown wire version without a diagnostic override."""

    code = "unknown_schema"


class UnsupportedSchemaVariantError(SchemaResolutionError):
    """Raised when a known wire version has an unsupported ABI signature."""

    code = "unsupported_schema_variant"

    def __init__(self, reported_version: int, evidence: tuple[SchemaEvidence, ...]):
        self.reported_version = reported_version
        self.evidence = evidence
        details = ", ".join(item.describe() for item in evidence)
        super().__init__(
            f"Unsupported ABI variant for wire schema 0x{reported_version:X}: "
            f"{details}"
        )


class AmbiguousSchemaError(SchemaResolutionError):
    """Raised when available packet evidence cannot choose a safe binding."""

    code = "ambiguous_schema"

    def __init__(self, reported_version: int):
        self.reported_version = reported_version
        super().__init__(
            f"Wire schema 0x{reported_version:X} needs discriminating ABI evidence"
        )


class SchemaConflictError(SchemaResolutionError):
    """Raised when packet evidence or an explicit variant conflicts."""

    code = "schema_conflict"


@dataclass(frozen=True, slots=True)
class SchemaEvidence:
    """Packet-level evidence used to distinguish schemas sharing a wire ID."""

    appid: int
    payload_length: int
    housekeeping_type: int | None = None

    def describe(self) -> str:
        suffix = ""
        if self.housekeeping_type is not None:
            suffix = f", hk_type={self.housekeeping_type}"
        return f"appid=0x{self.appid:X}, length={self.payload_length}{suffix}"


@dataclass(frozen=True, slots=True)
class PacketSignature:
    """A packet signature that uniquely identifies one frozen ABI variant."""

    appid: int
    payload_length: int
    housekeeping_type: int | None = None

    def matches(self, evidence: SchemaEvidence) -> bool:
        # CDI payloads may retain up to three bytes of four-byte transport padding
        rounded_payload_length = (self.payload_length + 3) & ~3
        return (
            self.appid == evidence.appid
            and evidence.payload_length in (
                self.payload_length,
                rounded_payload_length,
            )
            and (
                self.housekeeping_type is None
                or self.housekeeping_type == evidence.housekeeping_type
            )
        )


@dataclass(frozen=True, slots=True)
class SchemaBinding:
    """Immutable references and provenance for one frozen packet ABI."""

    binding_key: str
    canonical_schema_id: int
    accepted_reported_versions: tuple[int, ...]
    pystruct: Any
    appids: Any
    commands: Any
    errors: Any
    source_release: str
    source_commit: str
    source_files: Mapping[str, str]
    generated_source_files: Mapping[str, str]
    generated_files: Mapping[str, str]
    generation: Mapping[str, Any]
    abi_fingerprint: str
    abi: Mapping[str, Any]
    signatures: tuple[PacketSignature, ...] = ()
    variant: str | None = None

    @property
    def schema_id(self) -> int:
        """Return the canonical wire schema ID."""

        return self.canonical_schema_id

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Return immutable provenance for the generated binding."""

        return MappingProxyType(
            {
                "binding_key": self.binding_key,
                "canonical_schema_id": self.canonical_schema_id,
                "accepted_reported_versions": self.accepted_reported_versions,
                "variant": self.variant,
                "source_release": self.source_release,
                "source_commit": self.source_commit,
                "source_files": self.source_files,
                "generated_source_files": self.generated_source_files,
                "generated_files": self.generated_files,
                "generation": self.generation,
                "abi": self.abi,
                "signatures": self.signatures,
            }
        )

    @property
    def binding_provenance(self) -> Mapping[str, Any]:
        """Return the provenance name used by packet objects."""

        return self.provenance


@dataclass(frozen=True, slots=True)
class SchemaResolution:
    """One binding selection with its reported-version provenance."""

    binding: SchemaBinding
    reported_version: int | None
    schema_assumed: bool
    issue_code: str | None = None
    evidence: tuple[SchemaEvidence, ...] = ()

    @property
    def canonical_schema_id(self) -> int:
        """Return the selected binding's canonical schema ID."""

        return self.binding.canonical_schema_id

    @property
    def binding_provenance(self) -> Mapping[str, Any]:
        """Return immutable provenance for the selected binding."""

        return self.binding.provenance


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _load_provenance() -> Mapping[str, Any]:
    path = files("uncrater.coreloop").joinpath("provenance.json")
    return _freeze(json.loads(path.read_text(encoding="utf-8")))


PROVENANCE = _load_provenance()


def _binding(
    key: str,
    module: Any,
    *,
    signatures: tuple[PacketSignature, ...] = (),
) -> SchemaBinding:
    record = PROVENANCE["bindings"][key]
    canonical_schema_id = record["canonical_schema_id"]
    if module.pystruct.VERSION_ID != canonical_schema_id:
        raise RuntimeError(
            f"Frozen binding {key} reports VERSION_ID "
            f"0x{module.pystruct.VERSION_ID:X}, expected 0x{canonical_schema_id:X}"
        )
    abi = record["abi"]
    return SchemaBinding(
        binding_key=key,
        canonical_schema_id=canonical_schema_id,
        accepted_reported_versions=tuple(record["accepted_reported_versions"]),
        variant=record["variant"],
        pystruct=module.pystruct,
        appids=module.appId,
        commands=module.command,
        errors=module._errors,
        source_release=record["source_release"],
        source_commit=record["source_commit"],
        source_files=record["source_files"],
        generated_source_files=record["generated_source_files"],
        generated_files=record["generated_files"],
        generation=record["generation"],
        abi_fingerprint=abi["sha256"],
        abi=abi,
        signatures=signatures,
    )


_EARLY_306_SIGNATURES = (
    PacketSignature(0x206, 2571, 0),
    PacketSignature(0x280, 590),
)

_FINAL_306_SIGNATURES = (
    PacketSignature(0x206, 2692, 0),
    PacketSignature(0x206, 90, 100),
    PacketSignature(0x206, 48, 101),
    PacketSignature(0x280, 597),
)


BINDINGS_BY_KEY = MappingProxyType(
    {
        "203": _binding("203", pycoreloop_203),
        "305": _binding("305", pycoreloop_305),
        "306-early": _binding(
            "306-early",
            pycoreloop_306_early,
            signatures=_EARLY_306_SIGNATURES,
        ),
        "306-final": _binding(
            "306-final",
            pycoreloop_306_final,
            signatures=_FINAL_306_SIGNATURES,
        ),
        "307": _binding("307", pycoreloop_307),
    }
)

BINDINGS = tuple(BINDINGS_BY_KEY.values())
LATEST_BINDING = BINDINGS_BY_KEY["307"]

_UNAMBIGUOUS_BINDINGS = MappingProxyType(
    {
        0x203: BINDINGS_BY_KEY["203"],
        0x305: BINDINGS_BY_KEY["305"],
        0x307: BINDINGS_BY_KEY["307"],
    }
)

KNOWN_UNSUPPORTED_VERSION_IDS = frozenset((0x300, 0x302, 0x308, 0x309))
_KNOWN_REPORTED_VERSION_IDS = frozenset(
    (*_UNAMBIGUOUS_BINDINGS, 0x306, *KNOWN_UNSUPPORTED_VERSION_IDS)
)


def binding_for_key(binding_key: str) -> SchemaBinding:
    """Return a frozen binding by its unique provenance key."""

    return BINDINGS_BY_KEY[binding_key]


def evidence_from_packet(
    appid: int,
    blob: bytes,
) -> SchemaEvidence:
    """Extract schema evidence available before selecting a binding."""

    housekeeping_type = None
    if appid == 0x206 and len(blob) >= 12:
        # The shared housekeeping prefix puts its type at offset 10 in both ABIs
        housekeeping_type = struct.unpack_from("<H", blob, 10)[0]
    return SchemaEvidence(appid, len(blob), housekeeping_type)


def _normalize_evidence(
    evidence: SchemaEvidence
    | Iterable[SchemaEvidence]
    | None,
) -> tuple[SchemaEvidence, ...]:
    if evidence is None:
        return ()
    if isinstance(evidence, SchemaEvidence):
        return (evidence,)
    return tuple(evidence)


def _variant_binding(variant: str) -> SchemaBinding:
    if variant == "early":
        return BINDINGS_BY_KEY["306-early"]
    if variant == "final":
        return BINDINGS_BY_KEY["306-final"]
    raise SchemaResolutionError(f"Unknown 0x306 schema variant {variant!r}")


def _binding_for_306(
    *,
    variant: str | None,
    evidence: tuple[SchemaEvidence, ...],
) -> SchemaBinding:
    explicit = None if variant is None else _variant_binding(variant)
    matches: set[str] = set()
    unsupported_discriminating: list[SchemaEvidence] = []

    for item in evidence:
        discriminating = item.appid == 0x280 or (
            item.appid == 0x206
            and item.housekeeping_type in (0, 100, 101)
        )
        item_matches = {
            key
            for key in ("306-early", "306-final")
            if any(
                signature.matches(item)
                for signature in BINDINGS_BY_KEY[key].signatures
            )
        }
        matches.update(item_matches)
        if discriminating and not item_matches:
            unsupported_discriminating.append(item)

    if len(matches) > 1:
        raise SchemaConflictError(
            "Packet evidence identifies conflicting 0x306 ABIs"
        )
    if matches and unsupported_discriminating:
        raise SchemaConflictError(
            "Packet evidence mixes a supported 0x306 ABI with an unsupported layout"
        )
    if unsupported_discriminating:
        raise UnsupportedSchemaVariantError(
            0x306,
            tuple(unsupported_discriminating),
        )
    if not matches:
        # A variant label is a caller assertion, not evidence about packet bytes
        raise AmbiguousSchemaError(0x306)

    matched_key = next(iter(matches))
    if explicit is not None and explicit.binding_key != matched_key:
        raise SchemaConflictError(
            f"Explicit variant {explicit.binding_key} conflicts with packet evidence"
        )
    return BINDINGS_BY_KEY[matched_key]


def resolve_wire_version(
    reported_version: int | None,
    *,
    variant: str | None = None,
    evidence: SchemaEvidence
    | Iterable[SchemaEvidence]
    | None = None,
    diagnostic_override: bool = False,
) -> SchemaResolution:
    """Resolve a reported version and retain how the selection was made."""

    if reported_version is None:
        if variant is not None:
            raise SchemaConflictError(
                "A variant cannot accompany a missing version"
            )
        return SchemaResolution(LATEST_BINDING, None, True)

    if reported_version == 0x306:
        evidence = tuple(dict.fromkeys(_normalize_evidence(evidence)))
        binding = _binding_for_306(
            variant=variant,
            evidence=_normalize_evidence(evidence),
        )
        return SchemaResolution(binding, reported_version, False, evidence=evidence)

    if variant is not None:
        raise SchemaConflictError("Only wire schema 0x306 accepts a variant")
    if reported_version in _UNAMBIGUOUS_BINDINGS:
        return SchemaResolution(
            _UNAMBIGUOUS_BINDINGS[reported_version],
            reported_version,
            False,
        )
    if reported_version in KNOWN_UNSUPPORTED_VERSION_IDS:
        raise UnsupportedSchemaError(reported_version)
    if diagnostic_override:
        return SchemaResolution(
            LATEST_BINDING,
            reported_version,
            True,
            issue_code="unknown_schema",
        )
    raise UnknownSchemaError(reported_version)


def resolve_packet_stream(packets, *, variant=None, diagnostic_override=False,
                          inherited=None):
    """Resolve all version prefixes and structural evidence before typed decode.

    Packets are (AppID, bytes) pairs. An inherited resolution supplies evidence
    from the full input when this is a subset; local bytes must agree with it.
    Missing or truncated version prefixes remain the packet decoder's concern.
    """
    from .appids import normalize_dcb_appid

    versions = set()
    evidence = []
    for appid, blob in packets:
        appid = normalize_dcb_appid(appid)
        if appid == 0x209 and len(blob) >= 4:
            versions.add(struct.unpack_from("<I", blob)[0])
        elif appid in (0x206, 0x20F, 0x280) and len(blob) >= 2:
            versions.add(struct.unpack_from("<H", blob)[0])
        if appid in (0x206, 0x280):
            evidence.append(evidence_from_packet(appid, blob))
    if inherited is not None:
        if not isinstance(inherited, SchemaResolution):
            raise TypeError("inherited schema must be a SchemaResolution")
        expected = inherited.reported_version
        if any(version != expected for version in versions):
            raise SchemaConflictError("Packet versions conflict with the input schema")
        versions = set() if expected is None else {expected}
        evidence = [*inherited.evidence, *evidence]
    if len(versions) > 1:
        raise SchemaConflictError("One input reports conflicting wire schema versions")
    reported_version = next(iter(versions), None)
    resolution = resolve_wire_version(
        reported_version, variant=variant, evidence=evidence,
        diagnostic_override=diagnostic_override,
    )
    if inherited is not None and (
        resolution.binding is not inherited.binding
        or resolution.schema_assumed != inherited.schema_assumed
        or resolution.issue_code != inherited.issue_code
    ):
        raise SchemaConflictError("Input schema resolution conflicts with its evidence")
    return resolution


def schema_resolution_record(resolution):
    """Serialize input-wide evidence without local paths or mutable bindings."""
    return {
        "binding_key": resolution.binding.binding_key,
        "abi_fingerprint": resolution.binding.abi_fingerprint,
        "reported_version": resolution.reported_version,
        "schema_assumed": resolution.schema_assumed,
        "evidence": [
            {"appid": item.appid, "payload_length": item.payload_length,
             "housekeeping_type": item.housekeeping_type}
            for item in resolution.evidence
        ],
    }


def schema_resolution_from_record(record, *, diagnostic_override=False):
    """Re-resolve persisted evidence and reject inconsistent schema claims."""
    keys = {"binding_key", "abi_fingerprint", "reported_version", "schema_assumed", "evidence"}
    if not isinstance(record, dict) or set(record) != keys:
        raise SchemaResolutionError("Invalid input schema record")
    version = record["reported_version"]
    if version is not None and (type(version) is not int or not 0 <= version <= 0xFFFFFFFF):
        raise SchemaResolutionError("Invalid reported schema version")
    if type(record["schema_assumed"]) is not bool or not isinstance(record["evidence"], list):
        raise SchemaResolutionError("Invalid input schema evidence")
    evidence = []
    for item in record["evidence"]:
        if not isinstance(item, dict) or set(item) != {"appid", "payload_length", "housekeeping_type"}:
            raise SchemaResolutionError("Invalid packet schema evidence")
        if (type(item["appid"]) is not int or not 0 <= item["appid"] <= 0x7FF
                or type(item["payload_length"]) is not int or item["payload_length"] < 0
                or (item["housekeeping_type"] is not None and (
                    type(item["housekeeping_type"]) is not int or not 0 <= item["housekeeping_type"] <= 0xFFFF))):
            raise SchemaResolutionError("Invalid packet schema evidence values")
        evidence.append(SchemaEvidence(**item))
    resolution = resolve_wire_version(version, evidence=evidence, diagnostic_override=diagnostic_override)
    if (resolution.binding.binding_key != record["binding_key"]
            or resolution.binding.abi_fingerprint != record["abi_fingerprint"]
            or resolution.schema_assumed != record["schema_assumed"]):
        raise SchemaConflictError("Stored input schema disagrees with resolved evidence")
    return resolution


def binding_for_wire_version(
    reported_version: int | None,
    *,
    variant: str | None = None,
    evidence: SchemaEvidence
    | Iterable[SchemaEvidence]
    | None = None,
    diagnostic_override: bool = False,
) -> SchemaBinding:
    """Return the frozen binding selected for a reported wire version."""

    return resolve_wire_version(
        reported_version,
        variant=variant,
        evidence=evidence,
        diagnostic_override=diagnostic_override,
    ).binding


def schema_assumed_for(
    reported_version: int | None,
    *,
    diagnostic_override: bool = False,
) -> bool:
    """Return whether resolution would assume the latest schema."""

    if reported_version is None:
        return True
    return (
        diagnostic_override
        and reported_version not in _KNOWN_REPORTED_VERSION_IDS
    )


__all__ = [
    "AmbiguousSchemaError",
    "BINDINGS",
    "BINDINGS_BY_KEY",
    "KNOWN_UNSUPPORTED_VERSION_IDS",
    "LATEST_BINDING",
    "PROVENANCE",
    "PacketSignature",
    "SchemaBinding",
    "SchemaConflictError",
    "SchemaEvidence",
    "SchemaResolution",
    "SchemaResolutionError",
    "UnknownSchemaError",
    "UnsupportedSchemaError",
    "UnsupportedSchemaVariantError",
    "binding_for_key",
    "binding_for_wire_version",
    "evidence_from_packet",
    "resolve_wire_version",
    "resolve_packet_stream",
    "schema_resolution_record",
    "schema_resolution_from_record",
    "schema_assumed_for",
]
