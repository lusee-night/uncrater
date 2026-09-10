"""Associate ordered RawADC streams without discarding unpaired samples."""

from dataclasses import dataclass, field

from .Packet_EOS import Packet_EOS
from .Packet_Hello import Packet_Hello
from .Packet_Waveform import Packet_Waveform, Packet_Waveform_Meta


@dataclass
class WaveformAssociations:
    """Validated groups and a serializable record of every unpaired packet."""

    groups: list = field(default_factory=list)
    unresolved: list = field(default_factory=list)


def associate_waveforms(packets, *, packet_context=None):
    """Associate only pairs shared by every intact grouping of an interval.

    Firmware sends one selected channel or the ordered quartet 0,1,2,3 per
    metadata packet. Quartet candidates cannot overlap. Counts constrain how
    many candidates are full captures; other packets are single-channel
    captures. Bounds on these choices identify unambiguous metadata ordinals
    in linear time, independently of interleaving between the two streams.

    Invalid payloads retain their slots. Unexplained counts, duplicate UIDs,
    and backward metadata times leave samples unresolved. Hello and EOS in
    the same source stream are hard boundaries. Reruns recompute from all accumulated input, including
    previously ambiguous tails. Without transport evidence, losses
    compatible with another capture grouping cannot be detected.

    Optional packet_context maps every packet index to original source order,
    source stream, and 14-bit start/last CCSDS sequence counts. These counts
    are provenance, not a per-APID continuity guarantee. An optional
    metadata_packet_index in every entry replays a complete-input association;
    null explicitly keeps a waveform unresolved, without local rematching.
    """
    result = WaveformAssociations()
    context = {} if packet_context is None else packet_context
    packets = list(packets)
    if context:
        if set(context) != {packet.packet_index for packet in packets}:
            raise ValueError("waveform packet context must cover every packet")
        orders = []
        for entry in context.values():
            if set(entry) not in (
                {"order", "stream", "start_sequence_count", "last_sequence_count"},
                {"order", "stream", "start_sequence_count", "last_sequence_count", "metadata_packet_index"},
            ):
                raise ValueError("invalid waveform packet context")
            if type(entry["order"]) is not int or entry["order"] < 0:
                raise ValueError("waveform source order must be a nonnegative integer")
            if not isinstance(entry["stream"], str):
                raise ValueError("waveform source stream must be a string")
            for name in ("start_sequence_count", "last_sequence_count"):
                if type(entry[name]) is not int or not 0 <= entry[name] < 16384:
                    raise ValueError("waveform sequence counts must be 14-bit integers")
            orders.append(entry["order"])
        if len(set(orders)) != len(orders):
            raise ValueError("waveform source order must be unique")
        packets.sort(key=lambda packet: context[packet.packet_index]["order"])

    def usable(packet):
        if any(issue.fatal for issue in packet.decode_status.issues):
            return False
        return not isinstance(packet, Packet_Waveform) or (
            0 <= packet.ch < 4
            and packet.ch == packet.appid - packet.schema.appids.AppID_RawADC
        )

    def keep_unresolved(packet, meta, reason):
        result.unresolved.append({
            "reason": reason,
            "waveform_packet_indices": {} if packet is None else {
                str(packet.ch): packet.packet_index
            },
            "metadata_packet_index": None if meta is None else meta.packet_index,
            "metadata": None if meta is None or not usable(meta) else {
                "unique_packet_id": meta.unique_packet_id,
                "time_32": meta.time_32,
                "time_16": meta.time_16,
                "timestamp": meta.timestamp,
            },
        })

    def match_interval(interval):
        waveforms = []
        metadata = []
        seen_uids = set()
        previous_time = None
        uncertain = False
        for packet in interval:
            if isinstance(packet, Packet_Waveform):
                if usable(packet):
                    packet.meta = None
                    packet.timestamp = 0xFFFFFFFFFFFFFFFF
                waveforms.append(packet)
            else:
                if usable(packet):
                    if packet.unique_packet_id in seen_uids:
                        uncertain = True
                    seen_uids.add(packet.unique_packet_id)
                    raw_time = (packet.time_16 << 32) + packet.time_32
                    if previous_time is not None and raw_time < previous_time:
                        uncertain = True
                    previous_time = raw_time
                metadata.append(packet)

        channels = [packet.appid - packet.schema.appids.AppID_RawADC for packet in waveforms]
        quartets = [i for i in range(len(channels) - 3) if channels[i:i + 4] == [0, 1, 2, 3]]
        extra = len(waveforms) - len(metadata)
        full_count = extra // 3
        if extra < 0 or extra % 3 or not 0 <= full_count <= len(quartets):
            uncertain = True
        if uncertain:
            for packet in waveforms:
                if usable(packet):
                    keep_unresolved(packet, None, "ambiguous" if metadata else "missing_metadata")
            for meta in metadata:
                keep_unresolved(None, meta, "ambiguous" if waveforms else "missing_waveforms")
            return

        # At most two alternatives per packet: its quartet is full or split
        # into singles. Prefix/suffix choice counts bound the metadata ordinal.
        grouped = {}
        quartet_index = 0
        for index, packet in enumerate(waveforms):
            while quartet_index < len(quartets) and index >= quartets[quartet_index] + 4:
                quartet_index += 1
            inside = quartet_index < len(quartets) and index >= quartets[quartet_index]
            bounds = []
            for selected in ((0, 1) if inside else (0,)):
                remaining = len(quartets) - quartet_index - int(inside)
                low = max(0, full_count - selected - remaining)
                high = min(quartet_index, full_count - selected)
                if low <= high:
                    start = quartets[quartet_index] if selected else index
                    bounds.append((start - 3 * high, start - 3 * low))
            minimum = min(low for low, high in bounds)
            maximum = max(high for low, high in bounds)
            if not usable(packet):
                continue
            if minimum != maximum:
                keep_unresolved(packet, None, "ambiguous")
            elif not usable(metadata[minimum]):
                keep_unresolved(packet, metadata[minimum], "invalid_metadata")
            else:
                grouped.setdefault(minimum, {})[packet.ch] = packet
        for index, meta in enumerate(metadata):
            valid = grouped.get(index)
            if not valid:
                keep_unresolved(None, meta, "missing_or_ambiguous_waveforms")
                continue
            meta.set_packets([valid.get(channel) for channel in range(4)])
            result.groups.append({
                "packets": dict(sorted(valid.items())),
                "meta": meta,
                "schema_binding": meta.schema.binding_key,
            })

    replay = ["metadata_packet_index" in entry for entry in context.values()]
    if any(replay):
        if not all(replay):
            raise ValueError("waveform replay must cover every packet")
        by_index = {packet.packet_index: packet for packet in packets}
        grouped = {}
        for packet in packets:
            target = context[packet.packet_index]["metadata_packet_index"]
            if target is not None and type(target) is not int:
                raise ValueError("waveform metadata reference must be an integer or null")
            if not isinstance(packet, Packet_Waveform):
                if target is not None:
                    raise ValueError("only waveforms may reference metadata")
                continue
            packet.meta = None
            packet.timestamp = 0xFFFFFFFFFFFFFFFF
            if target is None:
                if usable(packet):
                    keep_unresolved(packet, None, "missing_or_ambiguous_metadata")
                continue
            meta = by_index.get(target)
            if (not isinstance(meta, Packet_Waveform_Meta) or not usable(meta)
                    or not usable(packet)):
                raise ValueError("waveform replay references invalid packets")
            if context[target]["stream"] != context[packet.packet_index]["stream"]:
                raise ValueError("waveform replay crosses source streams")
            group = grouped.setdefault(target, {})
            if packet.ch in group:
                raise ValueError("waveform replay repeats a channel")
            group[packet.ch] = packet
        for packet in packets:
            if not isinstance(packet, Packet_Waveform_Meta):
                continue
            valid = grouped.get(packet.packet_index)
            if valid:
                packet.set_packets([valid.get(ch) for ch in range(4)])
                result.groups.append({"packets": dict(sorted(valid.items())),
                                      "meta": packet, "schema_binding": packet.schema.binding_key})
            else:
                keep_unresolved(None, packet, "missing_or_ambiguous_waveforms")
        return result

    intervals = {}
    for packet in packets:
        stream = context[packet.packet_index]["stream"] if context else ""
        interval = intervals.setdefault(stream, [])
        if isinstance(packet, (Packet_Hello, Packet_EOS)):
            match_interval(interval)
            interval.clear()
        elif isinstance(packet, (Packet_Waveform, Packet_Waveform_Meta)):
            interval.append(packet)
    for interval in intervals.values():
        match_interval(interval)
    return result
