import struct
from functools import lru_cache

from .appids import normalize_dcb_appid
from .constants import NPRODUCTS
from .PacketBase import PacketBase, Packet_Unsupported
from .Packet_Bootloader import Packet_Bootloader
from .Packet_Calibrator import Packet_Cal_Data, Packet_Cal_Debug, Packet_Cal_Metadata, Packet_Cal_RawPFB, Packet_Cal_ZoomSpectra
from .Packet_EOS import Packet_EOS
from .Packet_Heartbeat import Packet_Heartbeat
from .Packet_Hello import Packet_Hello
from .Packet_Housekeep import Packet_Housekeep
from .Packet_Spectrum import Packet_Grimm, Packet_Metadata, Packet_Spectrum, Packet_TR_Spectrum
from .Packet_Watchdog import Packet_Watchdog
from .Packet_Waveform import Packet_Waveform, Packet_Waveform_Meta
from .schema_registry import SchemaConflictError, SchemaEvidence, binding_for_key, evidence_from_packet, resolve_wire_version


def add_range(packet_types, appid_module, constant_name, count, PacketType):
    start = getattr(appid_module, constant_name, None)
    if start is not None:
        for i in range(count):
            packet_types[start + i] = PacketType


@lru_cache(maxsize=None)
def packet_dict_for_binding(binding_key):
    # AppID meanings are part of a schema, so each frozen binding gets a classifier
    binding_id = binding_for_key(binding_key).appids
    packet_types = {}
    singleton_types = {
        "AppID_uC_Housekeeping": Packet_Housekeep,
        "AppID_uC_Start": Packet_Hello,
        "AppID_uC_Heartbeat": Packet_Heartbeat,
        "AppID_Watchdog": Packet_Watchdog,
        "AppID_FW_Watchdog": Packet_Watchdog,
        "AppID_End_Of_Sequence": Packet_EOS,
        "AppID_MetaData": Packet_Metadata,
        "AppID_SpectraGrimm": Packet_Grimm,
        "AppID_Calibrator_MetaData": Packet_Cal_Metadata,
        "AppID_ZoomSpectra": Packet_Cal_ZoomSpectra,
        "AppID_RawADC_Meta": Packet_Waveform_Meta,
        "AppID_uC_Bootloader": Packet_Bootloader,
    }
    for constant_name, PacketType in singleton_types.items():
        appid_value = getattr(binding_id, constant_name, None)
        if appid_value is not None:
            packet_types[appid_value] = PacketType

    for constant_name in (
        "AppID_SpectraHigh", "AppID_SpectraMed", "AppID_SpectraLow",
        "AppID_SpectraVeryLow",
    ):
        add_range(packet_types, binding_id, constant_name, NPRODUCTS, Packet_Spectrum)
    for constant_name in (
        "AppID_SpectraTRHigh", "AppID_SpectraTRMed", "AppID_SpectraTRLow",
    ):
        add_range(packet_types, binding_id, constant_name, NPRODUCTS, Packet_TR_Spectrum)
    add_range(packet_types, binding_id, "AppID_RawADC", 4, Packet_Waveform)
    add_range(packet_types, binding_id, "AppID_FW_DirectSpectrum", 4, Packet_Unsupported)
    add_range(packet_types, binding_id, "AppID_Calibrator_Data", 3, Packet_Cal_Data)
    add_range(packet_types, binding_id, "AppID_Calibrator_RawPFB", 8, Packet_Cal_RawPFB)
    add_range(packet_types, binding_id, "AppID_Calibrator_Debug", 8, Packet_Cal_Debug)
    return packet_types


def reported_version_from_kwargs(kwargs):
    reported_version = kwargs.get("reported_version")
    version = kwargs.get("version")
    if reported_version is not None and version is not None and reported_version != version:
        raise SchemaConflictError("version and reported_version disagree")
    return reported_version if reported_version is not None else version


def bootstrap_schema(appid, blob, blob_fn, kwargs):
    # This runs before class dispatch, while only fixed wire prefixes are safe to read
    reported_version = reported_version_from_kwargs(kwargs)
    carries_version = appid in (0x206, 0x209, 0x20F, 0x280)
    needs_306_evidence = reported_version == 0x306 and appid in (0x206, 0x280)
    if not carries_version and not needs_306_evidence:
        return

    payload = blob
    if payload is None:
        with open(blob_fn, "rb") as source:
            payload = source.read()

    # Hello stores SW_version as uint32; metadata and HK use a uint16 prefix
    packet_version = None
    if appid == 0x209 and len(payload) >= 4:
        packet_version = struct.unpack_from("<I", payload, 0)[0]
    elif appid in (0x206, 0x20F, 0x280) and len(payload) >= 2:
        packet_version = struct.unpack_from("<H", payload, 0)[0]

    if packet_version is not None:
        if reported_version is not None and packet_version != reported_version:
            raise SchemaConflictError(
                f"Packet reports version 0x{packet_version:X}, "
                f"not session version 0x{reported_version:X}"
            )
        reported_version = packet_version
        kwargs["reported_version"] = reported_version

    if reported_version == 0x306 and appid in (0x206, 0x280):
        # A session binding cannot replace the current packet's ABI signature;
        # both must reach the resolver so early/final disagreements fail closed
        packet_evidence = evidence_from_packet(appid, payload)
        existing_evidence = kwargs.get("evidence")
        if existing_evidence is None:
            kwargs["evidence"] = packet_evidence
        elif isinstance(existing_evidence, SchemaEvidence):
            kwargs["evidence"] = (existing_evidence, packet_evidence)
        else:
            kwargs["evidence"] = (*existing_evidence, packet_evidence)


def dispatch_packet(appid, blob=None, blob_fn=None, **kwargs):
    if (blob is None) and (blob_fn is None):
        raise ValueError
    original_appid = appid
    appid = normalize_dcb_appid(appid)
    packet_kwargs = kwargs
    bootstrap_schema(appid, blob, blob_fn, packet_kwargs)

    schema = packet_kwargs.get("schema")
    if schema is None:
        resolution = resolve_wire_version(
            reported_version_from_kwargs(packet_kwargs),
            variant=packet_kwargs.get("schema_variant"),
            evidence=packet_kwargs.get("evidence"),
            diagnostic_override=packet_kwargs.get("diagnostic_override", False),
        )
        schema = resolution.binding
        packet_kwargs["schema"] = schema

    PacketType = packet_dict_for_binding(schema.binding_key).get(appid, PacketBase)
    packet_kwargs["original_appid"] = original_appid
    return PacketType(appid, blob=blob, blob_fn=blob_fn, **packet_kwargs)


__all__ = ["dispatch_packet"]
