"""Known-power zoom conversions without metadata or changes to raw packets."""

import struct

import numpy as np
import pytest

from uncrater import Collection, Packet_Cal_ZoomSpectra, normalize_zoom


def zoom_blob(uid=1):
    powers = np.asarray([1.0, 2.0, -0.5, 0.25])[:, None]
    expected = powers * np.ones((4, 64))
    native = (expected * (64 * 2**31)).astype("<f4")
    return struct.pack("<IH", uid, 23) + native.tobytes(), expected, native


@pytest.mark.parametrize("convention,scale", [("sdu", 1), ("pfb", 2**31)])
def test_packet_converts_all_components_without_metadata(convention, scale):
    blob, expected, native = zoom_blob()
    packet = Packet_Cal_ZoomSpectra(0x270, blob=blob)
    result = packet.normalized_zoom(convention=convention)
    np.testing.assert_array_equal(result, expected * scale)
    assert result.dtype == np.float64
    for row, name in enumerate(("AA", "BB", "ABR", "ABI")):
        np.testing.assert_array_equal(getattr(packet, name), native[row])
        assert not np.shares_memory(result, getattr(packet, name))
    result[:] = 0
    np.testing.assert_array_equal(
        packet.normalized_zoom(convention=convention), expected * scale,
    )
    assert packet.blob == blob


def test_collection_order_and_empty_result(tmp_path):
    empty = Collection(tmp_path)
    assert empty.normalized_zoom().shape == (0, 4, 64)
    with pytest.raises(ValueError, match="convention"):
        empty.normalized_zoom(convention="unknown")
    blob, expected, _ = zoom_blob(2)
    (tmp_path / "00002_0270.bin").write_bytes(blob)
    blob, _, _ = zoom_blob(1)
    (tmp_path / "00001_0270.bin").write_bytes(blob)
    collection = Collection(tmp_path)
    assert [p.unique_packet_id for p in collection.zoom_spectra_packets] == [1, 2]
    np.testing.assert_array_equal(
        collection.normalized_zoom(), np.stack([expected, expected]),
    )


def test_invalid_packet_cannot_be_normalized():
    packet = Packet_Cal_ZoomSpectra(0x270, blob=b"invalid", strict=False)
    with pytest.raises(ValueError, match="invalid zoom packet"):
        packet.normalized_zoom()


def test_array_conversion_retains_small_float32_values_and_missing_values():
    values = np.zeros((2, 4, 64), dtype=np.float32)
    values[0, 0, 0] = np.nextafter(np.float32(0), np.float32(1))
    values[1, 0, 0] = np.nan
    result = normalize_zoom(values)
    assert result[0, 0, 0] == 2.0**-186
    assert np.isnan(result[1, 0, 0])


@pytest.mark.parametrize("shape", [(64,), (4, 63), (64, 4)])
def test_array_rejects_wrong_axes(shape):
    with pytest.raises(ValueError, match="shape"):
        normalize_zoom(np.zeros(shape))


def test_array_rejects_complex_components_and_unknown_convention():
    with pytest.raises(TypeError, match="real numeric"):
        normalize_zoom(np.ones((4, 64), dtype=complex))
    with pytest.raises(ValueError, match="convention"):
        normalize_zoom(np.ones((4, 64)), convention="raw")
