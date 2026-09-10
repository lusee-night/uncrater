"""Deterministic, path-free reporting for decoded collections."""

import numpy as np

from .Packet_Calibrator import Packet_Cal_Metadata
from .Packet_Spectrum import Packet_Grimm
from .schema_registry import binding_for_key, schema_resolution_record


def canonical_report(collection):
    """Return a stable semantic snapshot without local paths or mtimes."""

    def spectrum_shapes(groups):
        return [
            {
                f"0x{product:02X}": list(group[product].data.shape)
                for product in sorted(
                    key for key in group if isinstance(key, int)
                )
            }
            for group in groups
        ]

    def spectrum_associations(groups):
        return [
            {
                "metadata_packet_index": group["meta"].packet_index,
                "metadata_uid": group["meta"].unique_packet_id,
                "products": {
                    f"0x{product:02X}": {
                        "packet_index": packet.packet_index,
                        "uid": packet.unique_packet_id,
                    }
                    for product, packet in sorted(
                        (key, value) for key, value in group.items()
                        if isinstance(key, int)
                    )
                },
            }
            for group in groups
        ]

    def multipart_associations(groups):
        return [
            {
                "unique_packet_id": group["unique_packet_id"],
                "page_packet_indices": [
                    packet.packet_index for packet in group["pages"]
                ],
                "schema_binding": group["schema_binding"],
            }
            for group in groups
        ]

    binding_provenance = []
    for binding_key in collection.selected_schema_bindings:
        binding = binding_for_key(binding_key)
        binding_provenance.append(
            {
                "binding_key": binding.binding_key,
                "schema_id": f"0x{binding.canonical_schema_id:03X}",
                "source_commit": binding.source_commit,
                "abi_fingerprint": binding.abi_fingerprint,
            }
        )
    aggregate_names = (
        "calib_data", "calib_gNacc", "calib_gphase", "calib_pfb",
        "cd_drift", "cd_have_lock", "cd_lock_ant", "cd_error_phaser",
        "cd_error_averager", "cd_error_process", "cd_error_stage3",
        "cd_powertop0", "cd_powertop1", "cd_powertop2", "cd_powertop3",
        "cd_powerbot0", "cd_powerbot1", "cd_powerbot2", "cd_powerbot3",
        "cd_fd0", "cd_fd1", "cd_fd2", "cd_fd3", "cd_sd0", "cd_sd1",
        "cd_sd2", "cd_sd3", "cd_fdx", "cd_sdx", "cd_snr0", "cd_snr1",
        "cd_snr2", "cd_snr3",
    )
    return {
        "report_schema_version": 1,
        **({"input_schema": schema_resolution_record(collection.schema_resolution)}
           if collection.schema_resolution is not None else {}),
        "reported_schema_ids": [
            f"0x{version:03X}" for version in collection.reported_schema_ids
        ],
        "selected_schema_ids": [
            f"0x{version:03X}" for version in collection.selected_schema_ids
        ],
        "selected_schema_bindings": list(collection.selected_schema_bindings),
        "schema_assumed": collection.schema_assumed,
        "binding_provenance": binding_provenance,
        "packet_count": len(collection.cont),
        "packet_counts_by_appid": {
            f"0x{appid:03X}": count
            for appid, count in sorted(collection.packet_counts_by_appid.items())
        },
        "invalid_counts_by_issue": dict(
            sorted(collection.invalid_counts_by_issue.items())
        ),
        "orphan_multipart_failures": collection.orphan_multipart_failures,
        "product_counts": {
            "science_metadata": len(collection.spectra),
            "normal_spectrum_packets": sum(
                sum(isinstance(key, int) for key in group)
                for group in collection.spectra
            ),
            "tr_spectrum_groups": len(collection.tr_spectra),
            "tr_spectrum_packets": sum(
                sum(isinstance(key, int) for key in group)
                for group in collection.tr_spectra
            ),
            "heartbeat_packets": len(collection.heartbeat_packets),
            "watchdog_packets": len(collection.watchdog_packets),
            "housekeeping_packets": len(collection.housekeeping_packets),
            "waveform_packets": len(collection.waveform_packets),
            "waveform_metadata_packets": len(collection.waveform_metadata_packets),
            "waveform_groups": len(collection.waveform_groups),
            "calibrator_metadata_packets": sum(
                isinstance(packet, Packet_Cal_Metadata)
                and collection._packet_usable(packet)
                for packet in collection.cont
            ),
            "calibrator_debug_metadata": len(collection.calibrator_debug_groups),
            "calibrator_data_groups": len(collection.calibrator_data_groups),
            "calibrator_pfb_groups": len(collection.calibrator_pfb_groups),
            "calibrator_debug_groups": len(collection.calibrator_debug_groups),
            "zoom_packets": len(collection.zoom_spectra_packets),
            "grimm_packets": sum(
                isinstance(packet, Packet_Grimm)
                and collection._packet_usable(packet)
                for packet in collection.cont
            ),
        },
        "shapes": {
            "spectra": spectrum_shapes(collection.spectra),
            "tr_spectra": spectrum_shapes(collection.tr_spectra),
            "waveforms": [
                {
                    str(channel): list(packet.waveform.shape)
                    for channel, packet in group["packets"].items()
                }
                for group in collection.waveform_groups
            ],
            "zoom": [
                {
                    name: list(getattr(packet, name).shape)
                    for name in ("AA", "BB", "ABR", "ABI")
                }
                for packet in collection.zoom_spectra_packets
            ],
            "calibrator_data": [
                list(group["data"].shape)
                for group in collection.calibrator_data_groups
            ],
            "calibrator_pfb": [
                list(group["data"].shape)
                for group in collection.calibrator_pfb_groups
            ],
            "calibrator_aggregates": {
                name: list(getattr(collection, name).shape)
                for name in aggregate_names
            },
            "grimm": (
                list(collection.grimm_spectra.shape)
                if isinstance(collection.grimm_spectra, np.ndarray) else []
            ),
        },
        "unresolved_waveforms": collection.unresolved_waveforms,
        "associations": {
            "science": spectrum_associations(collection.spectra),
            "tr_spectra": spectrum_associations(collection.tr_spectra),
            "waveforms": [
                {
                    "metadata_packet_index": group["meta"].packet_index,
                    "waveform_packet_indices": {
                        str(channel): packet.packet_index
                        for channel, packet in group["packets"].items()
                    },
                    "schema_binding": group["schema_binding"],
                }
                for group in collection.waveform_groups
            ],
            "calibrator_data": multipart_associations(
                collection.calibrator_data_groups
            ),
            "calibrator_pfb": multipart_associations(
                collection.calibrator_pfb_groups
            ),
            "calibrator_debug": multipart_associations(
                collection.calibrator_debug_groups
            ),
        },
    }


__all__ = ["canonical_report"]
