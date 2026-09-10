import os, sys
import glob
import ctypes
import re
import struct
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
from typing import Optional


from datetime import datetime

from .Packet import *

from .error_utils import *
from .constants import NPRODUCTS, NCHANNELS
from .decode_status import DecodeStatus, PacketDecodeError
from .schema_registry import SchemaEvidence, SchemaResolutionError, resolve_wire_version, resolve_packet_stream
from .waveform_association import associate_waveforms


# Packet filenames are the only source of acquisition order and the original
# AppID, so reject names that cannot provide both values unambiguously
PACKET_FILENAME_RE = re.compile(
    r"^(?P<packet_index>[0-9]+)(?:_[^/]*)?_(?P<appid>[0-9A-Fa-f]+)\.bin$"
)


# A discovered packet's parsed filename and filesystem metadata
@dataclass(frozen=True)
class _PacketRecord:
    path: Path
    basename: str
    packet_index: int
    original_appid: int
    appid: int
    mtime: float


# Pending pages and validation state for one calibrator product group
@dataclass
class _MultipartState:
    family: str
    page_count: int
    pages: dict[int, PacketBase] = field(default_factory=dict)
    unique_packet_id: Optional[int] = None
    valid: bool = True

    @property
    def active(self):
        return bool(self.pages)

    def clear(self):
        self.pages.clear()
        self.unique_packet_id = None
        self.valid = True


class Collection:

    def __init__(self, dir, verbose = False, cut_to_hello = False, *,
                 strict=False, diagnostic_override=False, schema_variant=None,
                 waveform_packet_context=None, schema_resolution=None):
        """Decode and assemble the packet files in a CDI directory.

        dir names the directory; verbose prints packet-level progress, and
        cut_to_hello discards everything before the last Hello packet.
        strict=False records fatal issues and skips invalid products; strict=True
        raises on the first fatal decode or assembly issue.
        diagnostic_override permits an unknown reported version to use the
        latest schema while recording that assumption. waveform_packet_context
        optionally supplies source ordering and CCSDS spans to the waveform
        associator; see associate_waveforms(). schema_resolution supplies
        validated full-input evidence for a subset, which must agree with all
        local version prefixes and structural evidence. schema_variant may be
        'early' or 'final' and must agree with structural 0x306 evidence.
        """
        self.verbose = verbose
        self.dir = dir
        self.cut_to_hello = cut_to_hello
        self.strict = strict
        self.diagnostic_override = diagnostic_override
        self.schema_variant = schema_variant
        self.waveform_packet_context = waveform_packet_context
        self.schema_resolution = schema_resolution
        self.refresh()

    # Initialize decoded products, compatibility arrays, and status summaries
    def _reset_outputs(self):
        self.cont = []
        self.time = []
        self.desc = []
        self.spectra = []
        self.calib = []
        self.heartbeat_packets = []
        self.watchdog_packets = []
        self.housekeeping_packets = []
        self.waveform_packets = []
        self.waveform_metadata_packets = []
        self.waveform_groups = []
        self.unresolved_waveforms = []
        self.zoom_spectra_packets = []
        self.calib_meta = []
        self.calib_debug = []
        self.calibrator_data_groups = []
        self.calibrator_pfb_groups = []
        self.calibrator_debug_groups = []
        self.calib_data = np.array([])
        self.calib_gNacc = np.array([])
        self.calib_gphase = np.array([])
        self.calib_pfb = np.array([])
        self.pfb = np.array([])
        self.grimm_spectra = []
        self.decode_status = DecodeStatus()
        self.packet_counts_by_appid = Counter()
        self.invalid_counts_by_issue = Counter()
        self.reported_schema_ids = ()
        self.selected_schema_ids = ()
        self.selected_schema_bindings = ()
        self.schema_assumed = False
        self.orphan_multipart_failures = 0
        self.cd_errors = []
        for name in (
            "cd_drift", "cd_have_lock", "cd_lock_ant", "cd_error_phaser",
            "cd_error_averager", "cd_error_process", "cd_error_stage3",
            "cd_powertop0", "cd_powertop1", "cd_powertop2", "cd_powertop3",
            "cd_powerbot0", "cd_powerbot1", "cd_powerbot2", "cd_powerbot3",
            "cd_fd0", "cd_fd1", "cd_fd2", "cd_fd3", "cd_sd0", "cd_sd1",
            "cd_sd2", "cd_sd3", "cd_fdx", "cd_sdx", "cd_snr0", "cd_snr1",
            "cd_snr2", "cd_snr3",
        ):
            setattr(self, name, np.array([]))

    # Parse and deterministically order packets, optionally trimming pre-Hello data
    def _discover(self):
        records = []
        for fn in glob.glob(os.path.join(self.dir, "*.bin")):
            path = Path(fn)
            match = PACKET_FILENAME_RE.fullmatch(path.name)
            if match is None:
                raise ValueError(f"invalid CDI packet filename {path.name!r}")
            original_appid = int(match.group("appid"), 16)
            records.append(
                _PacketRecord(
                    path=path,
                    basename=path.name,
                    packet_index=int(match.group("packet_index")),
                    original_appid=original_appid,
                    appid=normalize_dcb_appid(original_appid),
                    mtime=path.stat().st_mtime,
                )
            )
        records.sort(
            key=lambda record: (
                record.packet_index,
                record.appid,
                record.basename.casefold(),
                record.basename,
            )
        )
        if self.cut_to_hello:
            hello_indices = [
                i for i, record in enumerate(records)
                if appid_is_hello(record.appid)
            ]
            if hello_indices:
                records = records[hello_indices[-1]:]

        by_index = {}
        for record in records:
            by_index.setdefault(record.packet_index, []).append(record)
        for packet_index, tied in sorted(by_index.items()):
            if len(tied) > 1:
                self._issue(
                    "duplicate_numeric_index",
                    f"numeric packet index {packet_index} occurs {len(tied)} times; deterministic AppID/name ordering was used",
                    record=tied[0],
                    fatal=False,
                    details={
                        "packet_index": packet_index,
                        "filenames": [record.basename for record in tied],
                    },
                )
        return records

    # Read only the fixed header bytes needed during schema planning
    @staticmethod
    def _read_prefix(record, size):
        with record.path.open("rb") as source:
            return source.read(size)

    # Extract a fixed-position reported schema version when the packet has one
    def _reported_version(self, record):
        if appid_is_hello(record.appid):
            prefix = self._read_prefix(record, 4)
            return struct.unpack_from("<I", prefix, 0)[0] if len(prefix) == 4 else None
        if (appid_is_metadata(record.appid)
                or appid_is_housekeeping(record.appid)
                or appid_is_cal_metadata(record.appid)):
            prefix = self._read_prefix(record, 2)
            return struct.unpack_from("<H", prefix, 0)[0] if len(prefix) == 2 else None
        return None

    # Build ABI-discriminating evidence from packet kind, length, and subtype
    def _schema_evidence(self, record):
        if not (appid_is_housekeeping(record.appid)
                or appid_is_cal_metadata(record.appid)):
            return None
        prefix = self._read_prefix(record, 12)
        return SchemaEvidence(
            appid=record.appid,
            payload_length=record.path.stat().st_size,
            housekeeping_type=(
                struct.unpack_from("<H", prefix, 10)[0]
                if appid_is_housekeeping(record.appid) and len(prefix) >= 12
                else None
            ),
        )

    # Resolve one schema binding for the entire collection
    def _resolve_schema(self, records):
        first_hello = next(
            (record for record in records if appid_is_hello(record.appid)),
            None,
        )
        version_record = first_hello
        if version_record is None:
            # No-Hello captures retain the first fixed metadata/HK version
            version_record = next(
                (
                    record for record in records
                    if self._reported_version(record) is not None
                ),
                None,
            )
        reported_version = (
            None
            if version_record is None
            else self._reported_version(version_record)
        )
        self.reported_schema_ids = (
            () if reported_version is None else (reported_version,)
        )

        # The first Hello fixes the version, but 0x306 ABI evidence can occur
        # later in housekeeping or calibrator metadata.
        evidence = tuple(
            item
            for record in records
            if (item := self._schema_evidence(record)) is not None
        ) if reported_version == 0x306 else ()
        try:
            if self.schema_resolution is None:
                resolution = resolve_wire_version(
                    reported_version,
                    variant=(self.schema_variant if reported_version == 0x306 else None),
                    evidence=evidence,
                    diagnostic_override=self.diagnostic_override,
                )
            else:
                # Only schema-bearing packets are needed; spectra may be large
                resolution = resolve_packet_stream(
                    ((record.appid, record.path.read_bytes()) for record in records
                     if record.appid in (0x209, 0x206, 0x20F, 0x280)),
                    inherited=self.schema_resolution, variant=self.schema_variant,
                    diagnostic_override=self.diagnostic_override,
                )
        except SchemaResolutionError as exc:
            self._issue(
                exc.code,
                str(exc),
                record=version_record or (records[0] if records else None),
            )
            return None

        if self.schema_resolution is not None:
            # Versionless subsets inherit the validated input version too
            self.reported_schema_ids = (() if resolution.reported_version is None
                                        else (resolution.reported_version,))
        binding = resolution.binding
        self.selected_schema_ids = (binding.canonical_schema_id,)
        self.selected_schema_bindings = (binding.binding_key,)
        self.schema_assumed = resolution.schema_assumed
        return resolution

    # Map a calibrator AppID to its zero-based page within the pending group
    @staticmethod
    def _multipart_page(packet, state):
        if isinstance(packet, Packet_Cal_Data):
            return packet.appid - packet.schema.appids.AppID_Calibrator_Data
        if isinstance(packet, Packet_Cal_RawPFB):
            return packet.appid - packet.schema.appids.AppID_Calibrator_RawPFB
        if isinstance(packet, Packet_Cal_Debug):
            return packet.appid - packet.schema.appids.AppID_Calibrator_Debug
        raise TypeError(f"{state.family} received an incompatible packet")

    # Publish a complete valid calibrator group to structured and legacy outputs
    def _publish_multipart(self, state):
        pages = [state.pages[page] for page in range(state.page_count)]
        if not state.valid:
            state.clear()
            return
        if state.family == "calibrator_data":
            data = np.asarray(pages[0].data, dtype=complex)
            data += 1j * np.asarray(pages[1].data)
            self.calibrator_data_groups.append(
                {
                    "unique_packet_id": state.unique_packet_id,
                    "pages": tuple(pages),
                    "data": data,
                    "gNacc": pages[2].gNacc,
                    "gphase": pages[2].gphase,
                    "schema_binding": pages[0].schema.binding_key,
                }
            )
        elif state.family == "calibrator_raw_pfb":
            data = np.asarray(
                [
                    np.asarray(pages[2 * channel].data, dtype=complex)
                    + 1j * np.asarray(pages[2 * channel + 1].data)
                    for channel in range(4)
                ]
            )
            self.calibrator_pfb_groups.append(
                {
                    "unique_packet_id": state.unique_packet_id,
                    "pages": tuple(pages),
                    "data": data,
                    "schema_binding": pages[0].schema.binding_key,
                }
            )
        elif state.family == "calibrator_debug":
            self.calib_debug.append(pages)
            self.calibrator_debug_groups.append(
                {
                    "unique_packet_id": state.unique_packet_id,
                    "pages": tuple(pages),
                    "schema_binding": pages[0].schema.binding_key,
                }
            )
        state.clear()

    # Validate and accumulate one calibrator page, publishing on completion
    def _consume_multipart(self, packet, record, state):
        page = self._multipart_page(packet, state)
        if page == 0:
            packet.read()
            valid_start = self._packet_usable(packet)
            packet_uid = packet.unique_packet_id if valid_start else None
            if state.active and valid_start and state.unique_packet_id == packet_uid:
                state.valid = False
                self._issue(
                    "duplicate_multipart_page",
                    f"duplicate {state.family} page 0",
                    record=record,
                    details={"family": state.family, "page": 0},
                )
                return
            if state.active:
                self._flush_multipart(state, boundary="new start page", record=record)
            if not valid_start:
                return
            state.unique_packet_id = packet_uid
            state.pages[0] = packet
        else:
            if not state.active:
                packet.read()
                if not packet.decode_status.has("orphan_multipart_page"):
                    self._issue(
                        "orphan_multipart_page",
                        f"{state.family} continuation page {page} has no start page",
                        record=record,
                        details={"family": state.family, "page": page},
                    )
                return
            packet.set_meta_id(state.unique_packet_id)
            packet.read()
            if page in state.pages:
                state.valid = False
                self._issue(
                    "duplicate_multipart_page",
                    f"duplicate {state.family} page {page}",
                    record=record,
                    details={"family": state.family, "page": page},
                )
                return
            if (not self._packet_usable(packet)
                    or packet.decode_status.has("unique_packet_id_mismatch")):
                state.valid = False
            state.pages[page] = packet
        if len(state.pages) == state.page_count:
            self._publish_multipart(state)

    # Rebuild typed counters when older bindings expose raw error_regs bytes
    @staticmethod
    def _debug_error_register(packet):
        metadata = packet.metadata
        if packet.schema.binding_key in ("306-final", "307"):
            return metadata.error_reg
        if packet.schema.binding_key == "203":
            return None
        error = packet.schema.pystruct.calibrator_errors()
        ctypes.memmove(
            ctypes.addressof(error),
            metadata.error_regs,
            ctypes.sizeof(metadata.error_regs),
        )
        return error

    # Populate legacy arrays only from complete validated multipart groups
    def _finalize_compatibility_arrays(self):
        if self.calibrator_data_groups:
            self.calib_data = np.asarray(
                [group["data"] for group in self.calibrator_data_groups]
            )
            self.calib_gNacc = np.asarray(
                [group["gNacc"] for group in self.calibrator_data_groups]
            )
            self.calib_gphase = np.asarray(
                [group["gphase"] for group in self.calibrator_data_groups]
            )
        self.calib_pfb = (
            np.asarray([group["data"] for group in self.calibrator_pfb_groups])
            if self.calibrator_pfb_groups else np.array([])
        )
        self.pfb = self.calib_pfb

        complete_starts = {group[0] for group in self.calib_debug}
        self.calib_meta = [
            packet if isinstance(packet, Packet_Cal_Metadata) else packet.metadata
            for packet in self.cont
            if (
                isinstance(packet, Packet_Cal_Metadata) and self._packet_usable(packet)
            ) or (
                isinstance(packet, Packet_Cal_Debug)
                and packet in complete_starts
            )
        ]
        if self.calib_debug:
            dcalib = self.calib_debug
            self.cd_have_lock = np.hstack([c[0].have_lock for c in dcalib])
            self.cd_lock_ant = np.hstack([c[0].lock_ant for c in dcalib])
            self.cd_errors = [
                error for c in dcalib
                if (error := self._debug_error_register(c[0])) is not None
            ]
            if len(self.cd_errors) == len(dcalib):
                # phase errors are 8 bits over two counter
                def get_counters(num):
                    return [num&0xFF, (num>>8)&0xFF , (num>>16)&0xFF, (num>>24)&0xFF]

                self.cd_error_phaser = np.array([(get_counters(x.cal_phaser_err[0])+get_counters(x.cal_phaser_err[1])) for x in self.cd_errors])
                self.cd_error_averager = np.array([[get_counters(x.averager_err[r]) for r in range(16)] for x in self.cd_errors])
                self.cd_error_process = np.array([np.hstack([get_counters(x.process_err[r]) for r in range(8)]) for x in self.cd_errors])
                self.cd_error_stage3 = np.array([np.hstack([get_counters(x.stage3_err[r]) for r in range(4)]) for x in self.cd_errors])
            self.cd_powertop0 = np.hstack([c[0].powertop0 for c in dcalib])
            self.cd_powertop1 = np.hstack([c[1].powertop1 for c in dcalib])
            self.cd_powertop2 = np.hstack([c[1].powertop2 for c in dcalib])
            self.cd_powertop3 = np.hstack([c[1].powertop3 for c in dcalib])
            self.cd_powerbot0 = np.hstack([c[2].powerbot0 for c in dcalib])
            self.cd_powerbot1 = np.hstack([c[2].powerbot1 for c in dcalib])
            self.cd_powerbot2 = np.hstack([c[2].powerbot2 for c in dcalib])
            self.cd_powerbot3 = np.hstack([c[3].powerbot3 for c in dcalib])
            self.cd_fd0 = np.hstack([c[3].fd0 for c in dcalib])
            self.cd_fd1 = np.hstack([c[3].fd1 for c in dcalib])
            self.cd_fd2 = np.hstack([c[4].fd2 for c in dcalib])
            self.cd_fd3 = np.hstack([c[4].fd3 for c in dcalib])
            self.cd_sd0 = np.hstack([c[4].sd0 for c in dcalib])
            self.cd_sd1 = np.hstack([c[5].sd1 for c in dcalib])
            self.cd_sd2 = np.hstack([c[5].sd2 for c in dcalib])
            self.cd_sd3 = np.hstack([c[5].sd3 for c in dcalib])
            self.cd_fdx = np.hstack([c[6].fdx for c in dcalib])
            self.cd_sdx = np.hstack([c[6].sdx for c in dcalib])
            self.cd_snr0 = np.hstack([c[6].snr0 for c in dcalib])
            self.cd_snr1 = np.hstack([c[7].snr1 for c in dcalib])
            self.cd_snr2 = np.hstack([c[7].snr2 for c in dcalib])
            self.cd_snr3 = np.hstack([c[7].snr3 for c in dcalib])

        # Drift is the calibrator's tracked phase increment in radians, proportional
        # to frequency offset. Metadata is full in v203 and sampled every eighth
        # point in later schemas; page 0 of a complete debug group is always full.
        drift_packets = [
            packet for packet in self.cont
            if (
                isinstance(packet, Packet_Cal_Metadata)
                and self._packet_usable(packet)
            ) or (
                isinstance(packet, Packet_Cal_Debug)
                and packet in complete_starts
            )
        ]
        if drift_packets:
            self.cd_drift = np.hstack([packet.drift for packet in drift_packets])
        grimm = [
            packet.data for packet in self.cont
            if isinstance(packet, Packet_Grimm)
            and self._packet_usable(packet)
        ]
        self.grimm_spectra = np.vstack(grimm) if grimm else []

    # Append one decoded packet to the legacy packet/time/description arrays
    def _append_packet(self, packet, record, ordinal):
        self.cont.append(packet)
        self.time.append(record.mtime)
        dt = record.mtime - self.time[0]
        self.desc.append(
            f"{ordinal:4d} : +{dt:4.1f}s : 0x{record.original_appid:0x} : {packet.desc}"
        )

    def refresh(self, quiet=False):
        """Re-read the directory and rebuild every decoded collection product.

        quiet suppresses the initial file-count message.
        """

        self._reset_outputs()
        records = self._discover()
        self.packet_counts_by_appid.update(record.original_appid for record in records)
        if not quiet:
            print(f"Analyzing {len(records)} files from {self.dir}.")
        resolution = self._resolve_schema(records)
        meta_packet = None
        tr_spectra = []
        data_state = _MultipartState("calibrator_data", 3)
        pfb_state = _MultipartState("calibrator_raw_pfb", 8)
        debug_state = _MultipartState("calibrator_debug", 8)
        multipart_states = (data_state, pfb_state, debug_state)

        for i, record in enumerate(records if resolution is not None else ()):
            if self.verbose:
                print("Reading ", record.path)
            if appid_is_hello(record.appid):
                self._flush_boundaries(
                    multipart_states,
                    boundary="Hello",
                    record=record,
                )
                meta_packet = None

            packet = Packet(
                record.original_appid,
                blob_fn=record.path,
                schema=resolution.binding,
                reported_version=resolution.reported_version,
                evidence=resolution.evidence or None,
                diagnostic_override=self.diagnostic_override,
                strict=self.strict,
            )
            packet.packet_index = record.packet_index

            if isinstance(packet, Packet_Metadata):
                packet.read()
                meta_packet = None
                if self._packet_usable(packet):
                    meta_packet = packet
                    self.spectra.append({"meta": packet})
                    tr_spectra.append({"meta": packet})
            elif isinstance(packet, Packet_Spectrum):
                if meta_packet is not None:
                    packet.set_meta(meta_packet)
                packet.read()
                if self._packet_usable(packet) and meta_packet is not None:
                    self.spectra[-1][packet.product] = packet
            elif isinstance(packet, Packet_TR_Spectrum):
                if meta_packet is not None:
                    packet.set_meta(meta_packet)
                packet.read()
                if self._packet_usable(packet) and meta_packet is not None:
                    tr_spectra[-1][packet.product] = packet
            elif isinstance(packet, Packet_Cal_Data):
                self._consume_multipart(packet, record, data_state)
            elif isinstance(packet, Packet_Cal_RawPFB):
                self._consume_multipart(packet, record, pfb_state)
            elif isinstance(packet, Packet_Cal_Debug):
                self._consume_multipart(packet, record, debug_state)
            elif isinstance(packet, Packet_Cal_ZoomSpectra):
                packet.read()
                if self._packet_usable(packet):
                    self.zoom_spectra_packets.append(packet)
            elif isinstance(packet, Packet_Waveform):
                packet.read()
                if self._packet_usable(packet):
                    self.waveform_packets.append(packet)
            elif isinstance(packet, Packet_Waveform_Meta):
                packet.read()
                if self._packet_usable(packet):
                    self.waveform_metadata_packets.append(packet)
            else:
                packet.read()

            if isinstance(packet, Packet_Hello) and self.verbose and self._packet_usable(packet):
                print (f"Detected FW version: {packet.SW_version:X}")
            if isinstance(packet, Packet_Heartbeat) and self._packet_usable(packet):
                self.heartbeat_packets.append(packet)
            if isinstance(packet, Packet_Watchdog) and self._packet_usable(packet):
                self.watchdog_packets.append(packet)
            if isinstance(packet, Packet_Housekeep) and self._packet_usable(packet):
                self.housekeeping_packets.append(packet)
            self._warn_packet(packet, record)
            self._append_packet(packet, record, i)
            if isinstance(packet, Packet_EOS):
                self._flush_boundaries(
                    multipart_states,
                    boundary="EOS",
                    record=record,
                )
                meta_packet = None

        self._flush_boundaries(
            multipart_states,
            boundary="end of input",
            record=None,
        )
        # we don't always send TR spectra; if dict contains only metadata
        # packet but no actual data, we assume it's fine and don't include it into self.tr_spectra
        self.tr_spectra = [trs for trs in tr_spectra if len(trs) > 1]
        associations = associate_waveforms(
            self.cont,
            packet_context=self.waveform_packet_context if resolution is not None else None,
        )
        self.waveform_groups = associations.groups
        self.unresolved_waveforms = associations.unresolved
        for unresolved in self.unresolved_waveforms:
            self._issue(
                "unresolved_waveform_metadata",
                "RawADC samples and metadata retained without an inferred association",
                fatal=False,
                details=unresolved,
            )
        self._finalize_compatibility_arrays()
        self._update_summaries()
        if self.verbose:
            print('# of calib debug entries', len(self.calib_debug))

    def __len__(self):
        """Return the number of decoded packet records in the collection."""

        return len(self.cont)

    def num_spectra_packets(self) -> int:
        """Return the number of assembled normal-spectrum groups."""

        return len(self.spectra)

    def num_tr_spectra_packets(self) -> int:
        """Return the number of assembled time-resolved spectrum groups."""

        return len(self.tr_spectra)

    def num_heartbeats(self) -> int:
        """Return the number of usable heartbeat packets."""

        return len(self.heartbeat_packets)

    def num_housekeeping_packets(self) -> int:
        """Return the number of usable housekeeping packets."""

        return len(self.housekeeping_packets)

    def num_waveform_packets(self) -> int:
        """Return the number of usable RawADC waveform packets."""

        return len(self.waveform_packets)

    def heartbeat_counter_ok(self) -> int:
        """Return 1 when heartbeat counters have no unexplained gaps."""

        hb_counts = [p.packet_count for p in self.heartbeat_packets]
        if len(hb_counts) <= 1:
            return 1
        for i,j in zip(hb_counts[:-1], hb_counts[1:]):
            if j == i+1:
                ## great
                continue
            elif (j<i) or (i==0):
                # then we must have seen a re boot
                if j==0:
                    continue
            else:
                print(f"Missing heartbeat packet between count {i}-> {j}")
                return 0

        return 1

    def heartbeat_max_dt(self) -> int:
        """Return the largest heartbeat time gap, or -1 with fewer than two."""

        if len(self.heartbeat_packets) <= 1:
            return -1
        hb_times = [p.time for p in self.heartbeat_packets]
        deltas = [t2 - t1 for t2, t1 in zip(hb_times[1:], hb_times[:-1])]
        return max(deltas)

    def heartbeat_min_dt(self) -> int:
        """Return the smallest heartbeat time gap, or 1e12 with fewer than two."""

        if len(self.heartbeat_packets) <= 1:
            return int(1e12)
        hb_times = [p.time for p in self.heartbeat_packets]
        deltas = [t2 - t1 for t2, t1 in zip(hb_times[1:], hb_times[:-1])]
        return min(deltas)

    def list(self):
        """Return one receipt-time description line per decoded packet."""

        return "\n".join(self.desc)

    # Format receipt information for one packet
    def _intro(self, i):
        desc = f"Packet #{i}\n"
        received_time = datetime.fromtimestamp(self.time[i])
        dt = self.time[i] - self.time[0]
        desc += f"Received at {received_time}, dt = {dt}s\n\n"
        return desc

    def info(self, i, intro=False):
        """Return packet information, optionally prefixed with receipt details."""

        if intro:
            return self._intro(i) + self.cont[i].info()
        return self.cont[i].info()

    # bcheckmark in TeX want an int 0/1 flag, not bool
    def has_all_products(self) -> int:
        """Return 1 when every normal-spectrum group has all products."""

        for s, prods in enumerate(self.spectra):
            for i in range(NPRODUCTS):
                if i not in prods:
                    print(f"Product {i} missing in spectra {s}.")
                    return 0
        return 1

    def has_all_tr_products(self) -> int:
        """Return 1 when every time-resolved group has all products."""

        for s, trs in enumerate(self.tr_spectra):
            for i in range(NPRODUCTS):
                if i not in trs:
                    print(f"Product {i} missing in TR spectra {s}.")
                    return 0
        return 1

    def all_spectra_crc_ok(self) -> int:
        """Return 1 when every present normal-spectrum packet has a valid CRC."""

        for i, prods in enumerate(self.spectra):
            for k in range(NPRODUCTS):
                if k in prods and prods[k].error_crc_mismatch:
                    print(f"Bad CRC in product {k} in spectra {i}.")
                    return 0
        return 1

    def all_tr_spectra_crc_ok(self) -> int:
        """Return 1 when every present time-resolved packet has a valid CRC."""

        for i, trs in enumerate(self.tr_spectra):
            for k in range(NPRODUCTS):
                if k in trs and trs[k].error_crc_mismatch:
                    print(
                        f"Bad CRC in product {k} in TR spectra {i}, incorrect CRC: {trs[k].crc}."
                    )
                    return 0
        return 1


    def all_meta_error_free(self) -> int:
        """Return 1 when every normal-spectrum metadata error mask is clear."""

        result = 1
        for i, sp in enumerate(self.spectra):
            if sp["meta"].errormask:
                print(f"Errors in {i}: {error_mask_pretty_print(sp['meta'].errormask)}")
                result = 0
        return result

    def get_meta(self,name):
        """Return one named metadata value from each normal-spectrum group."""

        return np.array([S['meta'][name] for S in self.spectra])


    def xxd(self, i, intro=False):
        """Return a packet hex dump, optionally prefixed with receipt details."""

        if intro:
            return self._intro(i) + self.cont[i].xxd()
        return self.cont[i].xxd()

    def np_spectra(self, ndx=None, channel=None):
        """Return normal spectra, optionally selecting one group or channel."""

        if (ndx is None) and (channel is None):
            return np.array([[S[ch].data for ch in range(NPRODUCTS)] for S in self.spectra])

        if (ndx is not None) and (channel is None):
            S = self.spectra[ndx]
            return np.array([S[ch].data for ch in range(NPRODUCTS)])

        if (ndx is None) and (channel is not None):
            return np.array([S[channel].data for S in self.spectra])

        if (ndx is not None) and (channel is not None):
            S = self.spectra[ndx]
            return S[channel].data

        assert(False), "Should not reach here"

    def np_tr_spectra(self, ndx=None, product: Optional[int]=None, *, channel: Optional[int]=None):
        """Return time-resolved spectra, optionally selecting a group or product.

        channel is the legacy alias for product.
        """

        if product is not None and channel is not None:
            raise TypeError("product and channel are aliases; supply only one")
        if channel is not None:
            product = channel

        if len(self.tr_spectra)==0:
            return np.array([])

        if (ndx is None) and (product is None):
            return np.vstack([[S[prod].data for prod in range(NPRODUCTS)] for S in self.tr_spectra])

        if (ndx is not None) and (product is None):
            S = self.tr_spectra[ndx]
            return np.array([S[prod].data for prod in range(NPRODUCTS)])

        if (ndx is None) and (product is not None):
            return np.vstack([S[product].data for S in self.tr_spectra])

        if (ndx is not None) and (product is not None):
            S = self.tr_spectra[ndx]
            return S[product].data

        assert(False), "Should not reach here"

    def canonical_report(self):
        """Return a deterministic, path-free semantic snapshot."""

        from .collection_report import canonical_report
        return canonical_report(self)

    # -------------------------------------------------------------------------
    # Error handling and diagnostics
    # -------------------------------------------------------------------------

    # Record an assembly issue and apply the collection's strict-mode policy
    def _issue(self, code, message, *, record=None, fatal=True, details=None):
        # Assembly failures have no single owning packet, so this records them
        # on the collection and applies the same strict/non-strict policy.
        issue = self.decode_status.add(
            code,
            message,
            appid=None if record is None else record.original_appid,
            source=None if record is None else record.basename,
            fatal=fatal,
            details=details,
        )
        context = "" if issue.source is None else f" ({issue.source})"
        print(f"Warning: {issue.code}{context}: {issue.message}", file=sys.stderr)
        if fatal and self.strict:
            raise PacketDecodeError(issue, self.decode_status)

    # Accept packets with diagnostics, but not packets with fatal decode issues
    @staticmethod
    def _packet_usable(packet):
        # Diagnostic findings keep decoded fields available; only fatal issues
        # make a packet unsafe to assemble into a collection product.
        return not any(issue.fatal for issue in packet.decode_status.issues)

    # Print one concise warning for every packet carrying decode issues
    @staticmethod
    def _warn_packet(packet, record):
        if packet.decode_status.ok:
            return
        problems = "; ".join(
            f"{issue.code}: {issue.message}"
            for issue in packet.decode_status.issues
        )
        print(
            f"Warning: packet {record.basename} "
            f"(AppID 0x{record.original_appid:03X}): {problems}",
            file=sys.stderr,
        )

    # Reject a calibrator group left incomplete at a session boundary
    def _flush_multipart(self, state, *, boundary, record):
        if not state.active:
            return
        missing = sorted(set(range(state.page_count)) - set(state.pages))
        self._issue(
            "missing_multipart_page",
            f"incomplete {state.family} group at {boundary}; missing pages {missing}",
            record=record,
            details={"family": state.family, "missing_pages": missing},
        )
        state.clear()

    # Flush every pending multipart family at Hello, EOS, or end of input
    def _flush_boundaries(self, multipart_states, *, boundary, record):
        for state in multipart_states:
            self._flush_multipart(state, boundary=boundary, record=record)

    # Merge packet issues and update collection-level diagnostic counters
    def _update_summaries(self):
        for packet in self.cont:
            self.decode_status.extend(packet.decode_status.issues)
        self.invalid_counts_by_issue = Counter(self.decode_status.codes)
        boundary_codes = {
            "orphan_multipart_page", "missing_multipart_page",
            "duplicate_multipart_page", "orphan_waveform_group",
            "raw_adc_metadata_without_waveforms",
            "raw_adc_metadata_without_usable_waveforms",
        }
        self.orphan_multipart_failures = sum(
            count for code, count in self.invalid_counts_by_issue.items()
            if code in boundary_codes
        )
