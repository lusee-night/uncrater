"""Known-value regressions for delayed and incomplete RawADC streams."""

import ctypes

import numpy as np
import pytest

from uncrater import Collection
from uncrater.schema_registry import LATEST_BINDING as BINDING


def save(root, index, kind, *, uid=1, timestamp=2**63 + 17):
    if isinstance(kind, int):
        appid = BINDING.appids.AppID_RawADC + kind
        blob = np.full(16384, index + 1, dtype="<u2").tobytes()
    elif kind == "bad_waveform":
        appid = BINDING.appids.AppID_RawADC
        blob = b"\0\0"
    elif kind == "eos":
        appid = BINDING.appids.AppID_End_Of_Sequence
        blob = b""
    else:
        appid = BINDING.appids.AppID_RawADC_Meta
        value = BINDING.pystruct.waveform_metadata()
        value.unique_packet_id = uid
        value.time_32 = uid * 16
        value.time_16 = 0
        value.timestamp = timestamp
        blob = bytes(value)
        blob += b"\0" * (-ctypes.sizeof(value) % 4)
        if kind == "bad_metadata":
            blob = blob[:2]
    (root / f"{index:05d}_{appid:04x}.bin").write_bytes(blob)


def pairs(collection):
    return {
        packet.packet_index: group["meta"].unique_packet_id
        for group in collection.waveform_groups
        for packet in group["packets"].values()
    }


def test_delayed_metadata_matches_queued_groups(tmp_path):
    for index, kind in enumerate((0, 1, 2, 3, 0, 1, 2, 3, "metadata", "metadata")):
        save(tmp_path, index, kind, uid=index + 10)
    collection = Collection(tmp_path)
    assert pairs(collection) == {**dict.fromkeys(range(4), 18), **dict.fromkeys(range(4, 8), 19)}
    assert collection.decode_status.ok
    assert all(packet.timestamp == 2**63 + 17 for packet in collection.waveform_packets)


def test_rerun_resolves_a_previously_incomplete_tail(tmp_path):
    save(tmp_path, 0, 0)
    save(tmp_path, 1, "metadata", uid=100)
    save(tmp_path, 2, 0)
    first = Collection(tmp_path)
    assert pairs(first) == {}
    assert first.waveform_packets[1].meta is None
    save(tmp_path, 3, "metadata", uid=101)
    second = Collection(tmp_path)
    assert pairs(second) == {0: 100, 2: 101}
    assert second.decode_status.ok
    assert second.canonical_report() == Collection(tmp_path).canonical_report()


@pytest.mark.parametrize("kind", ["bad_metadata", "bad_waveform"])
def test_corruption_occupies_a_slot_without_shifting_later_matches(tmp_path, kind):
    save(tmp_path, 0, "bad_waveform" if kind == "bad_waveform" else 0)
    save(tmp_path, 1, "bad_metadata" if kind == "bad_metadata" else "metadata", uid=50)
    save(tmp_path, 2, 0)
    save(tmp_path, 3, "metadata", uid=51)
    collection = Collection(tmp_path)
    assert pairs(collection) == {2: 51}
    assert collection.waveform_packets[-1].meta.unique_packet_id == 51


def test_lost_metadata_leaves_the_remaining_block_ambiguous(tmp_path):
    for index, kind in enumerate((0, 0, "metadata", 0, "metadata")):
        save(tmp_path, index, kind, uid=index)
    collection = Collection(tmp_path)
    assert pairs(collection) == {}
    assert len(collection.waveform_packets) == 3
    assert all(packet.meta is None for packet in collection.waveform_packets)
    unresolved = collection.canonical_report()["unresolved_waveforms"]
    assert len(unresolved) == 5
    assert {row["reason"] for row in unresolved} == {"ambiguous"}
    assert [row["metadata"]["unique_packet_id"] for row in unresolved if row["metadata"]] == [2, 4]


def test_boundary_prevents_borrowing_metadata(tmp_path):
    save(tmp_path, 0, 0)
    save(tmp_path, 1, "eos")
    save(tmp_path, 2, "metadata", uid=44)
    collection = Collection(tmp_path)
    assert pairs(collection) == {}
    assert len(collection.waveform_packets) == 1
    assert len(collection.waveform_metadata_packets) == 1


@pytest.mark.parametrize("next_sequence", [0, 1])
def test_ccsds_spans_do_not_imply_per_apid_continuity(tmp_path, next_sequence):
    for index, kind in enumerate((0, "metadata", 0, "metadata")):
        save(tmp_path, index, kind, uid=index)
    context = {
        index: {
            "order": index, "stream": "b05",
            "start_sequence_count": seq, "last_sequence_count": seq,
        }
        for index, seq in enumerate((16383, 20, next_sequence, 21))
    }
    collection = Collection(tmp_path, waveform_packet_context=context)
    assert pairs(collection) == {0: 1, 2: 3}


def test_duplicate_metadata_uid_does_not_attach_to_another_waveform(tmp_path):
    for index, kind in enumerate((0, "metadata", 0, "metadata")):
        save(tmp_path, index, kind, uid=0)
    collection = Collection(tmp_path)
    assert pairs(collection) == {}
    assert collection.waveform_packets[1].meta is None


@pytest.mark.parametrize("stream", [
    (0, "metadata", 1, 2, 3, 0, "metadata", 1, 2, 3),
    (0, 1, "metadata", 0, "metadata", "metadata"),
])
def test_metadata_interleaving_does_not_split_captures(tmp_path, stream):
    metadata_number = 0
    expected = {}
    for index, kind in enumerate(stream):
        if kind == "metadata":
            metadata_number += 1
        save(tmp_path, index, kind, uid=metadata_number)
    context = {}
    counters = {}
    for index, kind in enumerate(stream):
        sequence = counters.get(kind, 0)
        context[index] = {"order": index, "stream": "bank",
                          "start_sequence_count": sequence, "last_sequence_count": sequence}
        counters[kind] = sequence + 1
    collection = Collection(tmp_path, waveform_packet_context=context)
    if len(stream) == 10:
        expected = {0: 1, 2: 1, 3: 1, 4: 1, 5: 2, 7: 2, 8: 2, 9: 2}
    else:
        expected = {0: 1, 1: 2, 3: 3}
    assert pairs(collection) == expected
    assert collection.decode_status.ok


def test_ambiguous_capture_mode_preserves_only_invariant_pairs(tmp_path):
    for index, channel in enumerate((0, 1, 2, 3, 0, 1, 2, 3)):
        save(tmp_path, index, channel)
    for index in range(5):
        save(tmp_path, index + 8, "metadata", uid=index)
    collection = Collection(tmp_path)
    assert pairs(collection) == {0: 0, 7: 4}
    assert len(collection.waveform_packets) == 8
    assert sum(packet.meta is None for packet in collection.waveform_packets) == 6


def test_backward_metadata_time_leaves_interval_unresolved(tmp_path):
    for index, kind in enumerate((0, "metadata", 0, "metadata")):
        save(tmp_path, index, kind, uid=10 - index)
    assert pairs(Collection(tmp_path)) == {}


@pytest.mark.parametrize("invalid", ["target", "bank", "duplicate_channel"])
def test_replayed_associations_validate_packets_and_channels(tmp_path, invalid):
    for index, kind in enumerate((0, 0, "metadata")):
        save(tmp_path, index, kind)
    context = {index: {"order": index, "stream": "b06",
                       "start_sequence_count": index, "last_sequence_count": index,
                       "metadata_packet_index": 2 if index == 0 else None}
               for index in range(3)}
    if invalid == "target":
        context[0]["metadata_packet_index"] = 1
    elif invalid == "bank":
        context[2]["stream"] = "b05"
    else:
        context[1]["metadata_packet_index"] = 2
    with pytest.raises(ValueError, match="waveform replay"):
        Collection(tmp_path, waveform_packet_context=context)
