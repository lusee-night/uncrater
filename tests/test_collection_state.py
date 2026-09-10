import importlib
import struct
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from uncrater import Collection
from uncrater.decode_status import DecodeStatus, PacketDecodeError
from uncrater.schema_registry import BINDINGS_BY_KEY


collection_module = importlib.import_module("uncrater.Collection")


class FakePacket:
    def __init__(self, appid, blob_fn, schema, strict=True, **kwargs):
        self.appid = appid
        self.original_appid = appid
        self.blob_fn = Path(blob_fn)
        self.schema = schema
        self.schema_id = schema.canonical_schema_id
        self.reported_version = kwargs.get("reported_version")
        self.schema_assumed = (
            self.reported_version is None
            or self.reported_version not in schema.accepted_reported_versions
        )
        self.strict = strict
        self.decode_status = DecodeStatus()
        self.is_read = False

    @property
    def desc(self):
        return type(self).__name__

    def read(self):
        self.is_read = True

    def fail(self, code, message):
        issue = self.decode_status.add(
            code,
            message,
            appid=self.appid,
            source=self.blob_fn.name,
            fatal=True,
        )
        self.is_read = True
        if self.strict:
            raise PacketDecodeError(issue, self.decode_status)

    def info(self):
        return self.desc

    def xxd(self):
        return self.blob_fn.read_bytes().hex()


class FakeMetadata(FakePacket):
    def read(self):
        super().read()
        if "malformed" in self.blob_fn.name:
            self.fail("bad_blob_length", "malformed synthetic metadata")
            return
        self.unique_packet_id = 1
        self.errormask = 0


class FakeHello(FakePacket):
    def read(self):
        super().read()
        self.SW_version = struct.unpack("<I", self.blob_fn.read_bytes()[:4])[0]


class FakeSpectrum(FakePacket):
    def set_meta(self, metadata):
        self.meta = metadata

    def read(self):
        if not hasattr(self, "meta"):
            self.fail("missing_metadata", "spectrum packet requires metadata")
            return
        super().read()
        self.product = self.appid & 0xF
        self.unique_packet_id = self.meta.unique_packet_id
        self.data = np.asarray([self.product], dtype=float)
        if "crc-mismatch" in self.blob_fn.name:
            self.decode_status.add(
                "crc_mismatch",
                "synthetic CRC mismatch",
                appid=self.appid,
                source=self.blob_fn.name,
            )


class FakeTRSpectrum(FakePacket):
    def set_meta(self, metadata):
        self.meta = metadata

    def read(self):
        if not hasattr(self, "meta"):
            self.fail("missing_metadata", "spectrum packet requires metadata")
            return
        super().read()
        self.product = self.appid & 0xF
        self.unique_packet_id = self.meta.unique_packet_id
        self.data = np.asarray([self.product], dtype=float)


class FakeWaveform(FakePacket):
    def read(self):
        super().read()
        if "malformed" in self.blob_fn.name:
            self.fail("bad_blob_length", "malformed synthetic waveform")
            return
        self.ch = (
            4
            if "invalid-channel" in self.blob_fn.name
            else self.appid - int(self.schema.appids.AppID_RawADC)
        )
        self.waveform = np.asarray([self.ch], dtype=np.int16)
        self.timestamp = -1
        self.meta = None


class FakeWaveformMeta(FakePacket):
    def read(self):
        super().read()
        self.timestamp = 1234
        self.unique_packet_id = self.packet_index
        self.time_32 = 16
        self.time_16 = 0

    def set_packets(self, packets):
        self.read()
        self.packets = list(packets)
        for packet in self.packets:
            if packet is not None:
                packet.timestamp = self.timestamp
                packet.meta = self


class FakeMultipart(FakePacket):
    base_name = ""

    def page(self):
        return self.appid - int(getattr(self.schema.appids, self.base_name))

    def set_meta_id(self, expected_id):
        self.expected_id = expected_id

    def uid(self):
        payload = self.blob_fn.read_bytes()
        return struct.unpack("<I", payload[:4].ljust(4, b"\0"))[0] or 1

    def check_start(self):
        if self.page() > 0 and not hasattr(self, "expected_id"):
            self.fail("orphan_multipart_page", "continuation without start")
            return False
        self.unique_packet_id = self.uid()
        if self.page() > 0 and self.unique_packet_id != self.expected_id:
            self.decode_status.add(
                "unique_packet_id_mismatch",
                "multipart UID mismatch",
                appid=self.appid,
            )
        return True


class FakeCalData(FakeMultipart):
    base_name = "AppID_Calibrator_Data"

    def read(self):
        if not self.check_start():
            return
        self.is_read = True
        self.data_page = self.page()
        if self.data_page < 2:
            self.data = np.full((4, 2), self.data_page + 1, dtype=np.int32)
        else:
            self.gNacc = 7
            self.gphase = np.asarray([8, 9], dtype=np.int32)
            self.data = (self.gNacc, self.gphase)


class FakeCalPFB(FakeMultipart):
    base_name = "AppID_Calibrator_RawPFB"

    def read(self):
        if not self.check_start():
            return
        self.is_read = True
        page = self.page()
        self.channel = page // 2
        self.part = page % 2
        self.data = np.asarray([page + 1], dtype=np.int32)


class FakeCalDebug(FakeMultipart):
    base_name = "AppID_Calibrator_Debug"

    def read(self):
        if not self.check_start():
            return
        self.is_read = True
        self.debug_page = self.page()
        one = np.asarray([self.debug_page], dtype=np.int32)
        if self.debug_page == 0:
            self.have_lock = one
            self.lock_ant = one
            self.powertop0 = one
            self.drift = one
            self.metadata = SimpleNamespace(
                from_debug=True,
                error_reg=SimpleNamespace(
                    cal_phaser_err=[0, 0],
                    averager_err=[0] * 16,
                    process_err=[0] * 8,
                    stage3_err=[0] * 4,
                ),
            )
        elif self.debug_page == 1:
            self.powertop1 = self.powertop2 = self.powertop3 = one
        elif self.debug_page == 2:
            self.powerbot0 = self.powerbot1 = self.powerbot2 = one
        elif self.debug_page == 3:
            self.powerbot3 = self.fd0 = self.fd1 = one
        elif self.debug_page == 4:
            self.fd2 = self.fd3 = self.sd0 = one
        elif self.debug_page == 5:
            self.sd1 = self.sd2 = self.sd3 = one
        elif self.debug_page == 6:
            self.fdx = self.sdx = self.snr0 = one
        else:
            self.snr1 = self.snr2 = self.snr3 = one


class FakeEOS(FakePacket):
    pass


class FakeHeartbeat(FakePacket):
    def read(self):
        super().read()
        self.packet_count = 0
        self.time = 0


class FakeHousekeeping(FakePacket):
    pass


class FakeWatchdog(FakePacket):
    pass


class FakeCalMetadata(FakePacket):
    def read(self):
        super().read()
        if "malformed" in self.blob_fn.name:
            self.fail("bad_blob_length", "malformed calibrator metadata")
            return
        self.drift = np.asarray([1], dtype=float)


def install_fake_packets(monkeypatch, call_log=None):
    replacements = {
        "Packet_Metadata": FakeMetadata,
        "Packet_Hello": FakeHello,
        "Packet_Spectrum": FakeSpectrum,
        "Packet_TR_Spectrum": FakeTRSpectrum,
        "Packet_Waveform": FakeWaveform,
        "Packet_Waveform_Meta": FakeWaveformMeta,
        "Packet_Cal_Data": FakeCalData,
        "Packet_Cal_RawPFB": FakeCalPFB,
        "Packet_Cal_Debug": FakeCalDebug,
        "Packet_EOS": FakeEOS,
        "Packet_Heartbeat": FakeHeartbeat,
        "Packet_Housekeep": FakeHousekeeping,
        "Packet_Watchdog": FakeWatchdog,
        "Packet_Cal_Metadata": FakeCalMetadata,
    }
    for name, packet_type in replacements.items():
        monkeypatch.setattr(collection_module, name, packet_type)
        waveform_module = importlib.import_module("uncrater.waveform_association")
        if hasattr(waveform_module, name):
            monkeypatch.setattr(waveform_module, name, packet_type)

    def factory(appid, blob_fn, schema, **kwargs):
        if appid == 0x20F:
            packet_type = FakeMetadata
        elif appid == 0x209:
            packet_type = FakeHello
        elif 0x210 <= appid <= 0x23F:
            packet_type = FakeSpectrum
        elif 0x240 <= appid <= 0x26F:
            packet_type = FakeTRSpectrum
        elif 0x2F0 <= appid <= 0x2F3:
            packet_type = FakeWaveform
        elif appid == 0x2FA:
            packet_type = FakeWaveformMeta
        elif 0x281 <= appid <= 0x283:
            packet_type = FakeCalData
        elif 0x284 <= appid <= 0x28B:
            packet_type = FakeCalPFB
        elif 0x28C <= appid <= 0x293:
            packet_type = FakeCalDebug
        elif appid == 0x207:
            packet_type = FakeEOS
        elif appid == 0x20A:
            packet_type = FakeHeartbeat
        elif appid == 0x206:
            packet_type = FakeHousekeeping
        elif appid == 0x280:
            packet_type = FakeCalMetadata
        elif appid in (0x20C, 0x2FF):
            packet_type = FakeWatchdog
        else:
            packet_type = FakePacket
        packet = packet_type(appid, blob_fn, schema, **kwargs)
        if call_log is not None:
            call_log.append(
                {
                    "appid": appid,
                    "binding": schema.binding_key,
                    "reported_version": packet.reported_version,
                    "schema_assumed": packet.schema_assumed,
                }
            )
        if packet.schema_assumed and packet.reported_version is not None:
            packet.decode_status.add(
                "unknown_schema",
                "synthetic diagnostic schema override",
                appid=appid,
            )
        return packet

    monkeypatch.setattr(collection_module, "Packet", factory)


def write_packet(root, index, appid, payload=b"", label=None):
    middle = "" if label is None else f"_{label}"
    path = root / f"{index:04d}{middle}_{appid:04X}.bin"
    path.write_bytes(payload)
    return path


def test_tied_indices_use_stable_order_and_partial_group_remains_ambiguous(monkeypatch, tmp_path):
    calls = []
    install_fake_packets(monkeypatch, calls)
    write_packet(tmp_path, 10, 0x2F1)
    write_packet(tmp_path, 10, 0x2F0)
    write_packet(tmp_path, 11, 0x2FA)

    collection = Collection(tmp_path)

    assert [call["appid"] for call in calls] == [0x2F0, 0x2F1, 0x2FA]
    assert collection.invalid_counts_by_issue == {"duplicate_numeric_index": 1, "unresolved_waveform_metadata": 3}
    assert collection.waveform_groups == []
    assert all(packet.meta is None for packet in collection.waveform_packets)


def test_repeated_waveforms_are_retained_without_ambiguous_metadata(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    for index in range(5):
        write_packet(tmp_path, index, 0x2F0)
    write_packet(tmp_path, 5, 0x2FA)

    collection = Collection(tmp_path, strict=False)

    assert collection.invalid_counts_by_issue == {"unresolved_waveform_metadata": 6}
    assert len(collection.waveform_packets) == 5
    assert collection.waveform_groups == []
    assert all(packet.meta is None for packet in collection.waveform_packets)
    assert all(packet.timestamp == 0xFFFFFFFFFFFFFFFF for packet in collection.waveform_packets)


def test_malformed_waveform_preserves_valid_siblings(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x2F0, label="malformed")
    write_packet(tmp_path, 1, 0x2F1)
    write_packet(tmp_path, 2, 0x2F2)
    write_packet(tmp_path, 3, 0x2F3)
    write_packet(tmp_path, 4, 0x2FA)

    collection = Collection(tmp_path, strict=False)

    assert collection.invalid_counts_by_issue == {"bad_blob_length": 1}
    assert list(collection.waveform_groups[0]["packets"]) == [1, 2, 3]


def test_default_nonstrict_warns_and_skips_bad_calibrator_metadata(
    monkeypatch, tmp_path, capsys
):
    install_fake_packets(monkeypatch)
    path = write_packet(
        tmp_path,
        0,
        0x280,
        struct.pack("<H", 0x307),
        label="malformed",
    )

    collection = Collection(tmp_path)

    warning = capsys.readouterr().err
    assert warning.count("Warning: packet") == 1
    assert path.name in warning
    assert "bad_blob_length" in warning
    assert collection.invalid_counts_by_issue == {"bad_blob_length": 1}
    assert len(collection.cont) == 1
    assert collection.calib_meta == []
    assert collection.cd_drift.size == 0


def test_collection_warns_but_keeps_crc_mismatched_spectrum(
    monkeypatch, tmp_path, capsys
):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x20F, struct.pack("<H", 0x307))
    path = write_packet(tmp_path, 1, 0x210, label="crc-mismatch")

    collection = Collection(tmp_path)

    warning = capsys.readouterr().err
    assert warning.count("Warning: packet") == 1
    assert path.name in warning
    assert "crc_mismatch" in warning
    assert collection.invalid_counts_by_issue == {"crc_mismatch": 1}
    assert 0 in collection.spectra[0]


def test_strict_collection_still_raises_for_bad_packet(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x2F0, label="malformed")

    with pytest.raises(PacketDecodeError, match="bad_blob_length"):
        Collection(tmp_path, strict=True)


def test_metadata_after_invalid_only_waveforms_is_reported(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x2F0, label="invalid-channel")
    write_packet(tmp_path, 1, 0x2FA)

    collection = Collection(tmp_path, strict=False)

    assert collection.invalid_counts_by_issue == {
        "unresolved_waveform_metadata": 1,
    }
    assert collection.waveform_groups == []


def test_eos_and_end_flush_orphan_waveform_groups(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x2F0)
    write_packet(tmp_path, 1, 0x207)
    write_packet(tmp_path, 2, 0x2F1)

    collection = Collection(tmp_path, strict=False)

    assert collection.invalid_counts_by_issue == {"unresolved_waveform_metadata": 2}
    assert collection.orphan_multipart_failures == 0


def test_hello_resets_science_waveform_and_multipart_state(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x20F, struct.pack("<H", 0x307))
    write_packet(tmp_path, 1, 0x281, struct.pack("<I", 7))
    write_packet(tmp_path, 2, 0x2F0)
    write_packet(tmp_path, 3, 0x209, struct.pack("<I", 0x307))
    write_packet(tmp_path, 4, 0x210)

    collection = Collection(tmp_path, strict=False)

    assert collection.invalid_counts_by_issue == {
        "missing_metadata": 1,
        "missing_multipart_page": 1,
        "unresolved_waveform_metadata": 1,
    }
    assert len(collection.spectra) == 1
    assert list(collection.spectra[0]) == ["meta"]


@pytest.mark.parametrize(
    ("start", "count", "attribute"),
    [
        (0x281, 3, "calibrator_data_groups"),
        (0x284, 8, "calibrator_pfb_groups"),
        (0x28C, 8, "calibrator_debug_groups"),
    ],
)
def test_each_calibrator_family_publishes_only_complete_groups(
    monkeypatch, tmp_path, start, count, attribute
):
    install_fake_packets(monkeypatch)
    for page in range(count):
        write_packet(tmp_path, page, start + page, struct.pack("<I", 17))

    collection = Collection(tmp_path)

    assert len(getattr(collection, attribute)) == 1
    assert collection.invalid_counts_by_issue == {}


def test_calibrator_families_keep_independent_interleaved_state(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    index = 0
    for page in range(8):
        if page < 3:
            write_packet(tmp_path, index, 0x281 + page, struct.pack("<I", 11))
            index += 1
        write_packet(tmp_path, index, 0x284 + page, struct.pack("<I", 22))
        index += 1

    collection = Collection(tmp_path)

    assert len(collection.calibrator_data_groups) == 1
    assert len(collection.calibrator_pfb_groups) == 1
    assert collection.calibrator_data_groups[0]["unique_packet_id"] == 11
    assert collection.calibrator_pfb_groups[0]["unique_packet_id"] == 22


def test_calibrator_orphan_duplicate_and_boundary_missing_are_reported(
    monkeypatch, tmp_path
):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x282, struct.pack("<I", 1))
    write_packet(tmp_path, 1, 0x281, struct.pack("<I", 2))
    write_packet(tmp_path, 2, 0x282, struct.pack("<I", 2))
    write_packet(tmp_path, 3, 0x282, struct.pack("<I", 2), label="duplicate")
    write_packet(tmp_path, 4, 0x283, struct.pack("<I", 2))
    write_packet(tmp_path, 5, 0x284, struct.pack("<I", 3))
    write_packet(tmp_path, 6, 0x207)

    collection = Collection(tmp_path, strict=False)

    assert collection.invalid_counts_by_issue == {
        "duplicate_multipart_page": 1,
        "missing_multipart_page": 1,
        "orphan_multipart_page": 1,
    }
    assert collection.calibrator_data_groups == []
    assert collection.calibrator_pfb_groups == []


def test_new_start_flushes_missing_pages_before_starting_next_group(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x281, struct.pack("<I", 1))
    write_packet(tmp_path, 1, 0x281, struct.pack("<I", 2))
    write_packet(tmp_path, 2, 0x282, struct.pack("<I", 2))
    write_packet(tmp_path, 3, 0x283, struct.pack("<I", 2))

    collection = Collection(tmp_path, strict=False)

    assert collection.invalid_counts_by_issue == {"missing_multipart_page": 1}
    assert len(collection.calibrator_data_groups) == 1
    assert collection.calibrator_data_groups[0]["unique_packet_id"] == 2


def test_306_uses_collection_wide_rounded_housekeeping_evidence(monkeypatch, tmp_path):
    calls = []
    install_fake_packets(monkeypatch, calls)
    write_packet(tmp_path, 0, 0x209, struct.pack("<I", 0x306))
    housekeeping = bytearray(2572)
    struct.pack_into("<H", housekeeping, 0, 0x306)
    struct.pack_into("<H", housekeeping, 10, 0)
    write_packet(tmp_path, 1, 0x206, housekeeping)

    collection = Collection(tmp_path)

    assert collection.reported_schema_ids == (0x306,)
    assert collection.selected_schema_bindings == ("306-early",)
    assert not collection.schema_assumed
    assert {call["binding"] for call in calls} == {"306-early"}


def test_metadata_prefix_bootstraps_a_collection_without_hello(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x20F, struct.pack("<H", 0x305))

    collection = Collection(tmp_path)

    assert collection.reported_schema_ids == (0x305,)
    assert collection.selected_schema_bindings == ("305",)
    assert collection.cont[0].schema.binding_key == "305"
    assert not collection.schema_assumed


def test_conflicting_306_evidence_rejects_the_whole_collection(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x209, struct.pack("<I", 0x306))
    early = bytearray(2572)
    struct.pack_into("<H", early, 0, 0x306)
    struct.pack_into("<H", early, 10, 0)
    write_packet(tmp_path, 1, 0x206, early)
    final = bytearray(600)
    struct.pack_into("<H", final, 0, 0x306)
    write_packet(tmp_path, 2, 0x280, final)

    collection = Collection(tmp_path, strict=False)

    assert collection.cont == []
    assert collection.invalid_counts_by_issue == {"schema_conflict": 1}
    assert collection.packet_counts_by_appid == {0x209: 1, 0x206: 1, 0x280: 1}


def test_first_hello_selects_one_binding_for_the_whole_collection(
    monkeypatch, tmp_path
):
    calls = []
    install_fake_packets(monkeypatch, calls)
    write_packet(tmp_path, 0, 0x20A)
    write_packet(tmp_path, 1, 0x209, struct.pack("<I", 0x305))
    write_packet(tmp_path, 2, 0x209, struct.pack("<I", 0x305))

    collection = Collection(tmp_path)

    assert collection.reported_schema_ids == (0x305,)
    assert collection.selected_schema_bindings == ("305",)
    assert not collection.schema_assumed
    assert {call["binding"] for call in calls} == {"305"}
    assert {call["reported_version"] for call in calls} == {0x305}


def test_306_variant_hint_is_ignored_when_first_hello_is_307(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x20A)
    write_packet(tmp_path, 1, 0x209, struct.pack("<I", 0x307))

    collection = Collection(tmp_path, schema_variant="306-early")

    assert len(collection.cont) == 2
    assert collection.selected_schema_bindings == ("307",)
    assert not collection.schema_assumed
    assert collection.invalid_counts_by_issue == {}


def test_duplicate_spectrum_products_preserve_legacy_last_wins(monkeypatch, tmp_path):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x20F, struct.pack("<H", 0x307))
    normal_first = write_packet(tmp_path, 1, 0x210)
    normal_last = write_packet(tmp_path, 2, 0x210, label="last")
    tr_first = write_packet(tmp_path, 3, 0x240)
    tr_last = write_packet(tmp_path, 4, 0x240, label="last")

    collection = Collection(tmp_path)

    assert collection.spectra[0][0].blob_fn == normal_last
    assert collection.spectra[0][0].blob_fn != normal_first
    assert collection.tr_spectra[0][0].blob_fn == tr_last
    assert collection.tr_spectra[0][0].blob_fn != tr_first


def test_verbose_collection_preserves_valid_hello_version_message(
    monkeypatch, tmp_path, capsys
):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x209, struct.pack("<I", 0x307))

    Collection(tmp_path, verbose=True)

    assert "Detected FW version: 307" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("version", "issue_code"),
    [(0x306, "ambiguous_schema"), (0x300, "unsupported_schema")],
)
def test_nonstrict_unsafe_schema_records_issue_and_skips_collection(
    monkeypatch, tmp_path, version, issue_code
):
    install_fake_packets(monkeypatch)
    write_packet(tmp_path, 0, 0x209, struct.pack("<I", version))

    collection = Collection(tmp_path, strict=False)

    assert collection.cont == []
    assert collection.packet_counts_by_appid == {0x209: 1}
    assert collection.invalid_counts_by_issue == {issue_code: 1}


def test_306_evidence_after_a_later_hello_applies_to_the_whole_collection(
    monkeypatch, tmp_path
):
    calls = []
    install_fake_packets(monkeypatch, calls)
    write_packet(tmp_path, 0, 0x209, struct.pack("<I", 0x306))
    write_packet(tmp_path, 1, 0x209, struct.pack("<I", 0x306))
    final = bytearray(2692)
    struct.pack_into("<H", final, 0, 0x306)
    struct.pack_into("<H", final, 10, 0)
    write_packet(tmp_path, 2, 0x206, final)

    collection = Collection(tmp_path)

    assert collection.selected_schema_bindings == ("306-final",)
    assert {call["binding"] for call in calls} == {"306-final"}


def test_diagnostic_resolution_provenance_reaches_every_packet(monkeypatch, tmp_path):
    calls = []
    install_fake_packets(monkeypatch, calls)
    write_packet(tmp_path, 0, 0x209, struct.pack("<I", 0x40A))
    write_packet(tmp_path, 1, 0x2F0)
    write_packet(tmp_path, 2, 0x2FA)

    collection = Collection(tmp_path, diagnostic_override=True)

    assert collection.selected_schema_bindings == ("307",)
    assert collection.schema_assumed
    assert all(call["binding"] == "307" for call in calls)
    assert all(call["reported_version"] == 0x40A for call in calls)
    assert all(call["schema_assumed"] for call in calls)
    assert collection.invalid_counts_by_issue == {"unknown_schema": 3}
    assert len(collection.waveform_packets) == 1
    assert len(collection.waveform_metadata_packets) == 1
    assert len(collection.waveform_groups) == 1
