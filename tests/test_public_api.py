import importlib
import inspect
from types import SimpleNamespace

import numpy as np
import pytest

import uncrater
import uncrater.appids as appids
import uncrater.utils as utils


EXPECTED_PUBLIC_NAMES = {
    "Packet",
    "Collection",
    "PacketBase",
    "Packet_Bootloader",
    "Packet_Cal_Data",
    "Packet_Cal_Debug",
    "Packet_Cal_Metadata",
    "Packet_Cal_RawPFB",
    "Packet_Cal_ZoomSpectra",
    "Packet_EOS",
    "Packet_Grimm",
    "Packet_Heartbeat",
    "Packet_Hello",
    "Packet_Housekeep",
    "Packet_Metadata",
    "Packet_Spectrum",
    "Packet_TR_Spectrum",
    "Packet_Watchdog",
    "Packet_Waveform",
    "Packet_Waveform_Meta",
    "id",
    "appid",
    "appId_from_value",
    "value_from_appId",
    "NCHANNELS",
    "NPRODUCTS",
    "Time2Time",
    "process_ADC_stats",
    "process_telemetry",
    "cordic2rad",
    "rad2cordic",
    "cordic_add",
    "rle_decode",
    "normalize_dcb_appid",
    "appid_to_str",
    "appid_is_hello",
    "appid_is_metadata",
    "appid_is_housekeeping",
    "appid_is_heartbeat",
    "appid_is_watchdog",
    "appid_is_fw_watchdog",
    "appid_is_spectrum",
    "appid_is_tr_spectrum",
    "appid_is_zoom_spectrum",
    "appid_is_grimm_spectrum",
    "appid_is_cal_metadata",
    "appid_is_cal_data",
    "appid_is_cal_data_start",
    "appid_is_cal_raw_pfb",
    "appid_is_cal_raw_pfb_start",
    "appid_is_cal_debug",
    "appid_is_cal_debug_start",
    "appid_is_cal_segmented_payload",
    "appid_is_calibrator_product",
    "appid_is_fw_direct_spectrum",
    "appid_is_raw_adc",
    "appid_is_waveform",
    "appid_is_raw_adc_metadata",
    "appid_is_cal_any",
    "appid_is_rawPFB",
    "appid_is_rawPFB_start",
    "appid_is_cal_zoom",
}


def test_top_level_all_is_explicit_and_stable():
    assert set(uncrater.__all__) == EXPECTED_PUBLIC_NAMES
    assert len(uncrater.__all__) == len(EXPECTED_PUBLIC_NAMES)
    assert all(hasattr(uncrater, name) for name in uncrater.__all__)
    assert uncrater.__version__ == "1.0.0"


def test_star_import_contains_only_declared_public_names():
    namespace = {}
    exec("from uncrater import *", {}, namespace)
    assert set(namespace) == EXPECTED_PUBLIC_NAMES


def test_compatibility_ids_and_mappings_are_preserved():
    assert uncrater.appid is uncrater.id
    assert uncrater.id.AppID_RawADC == 0x2F0
    assert uncrater.appId_from_value[0x2F0] == "AppID_RawADC"
    assert uncrater.value_from_appId["AppID_RawADC"] == 0x2F0


def test_implementation_details_are_not_public_exports():
    packet_module = importlib.import_module("uncrater.Packet")

    for name in (
        "os",
        "sys",
        "np",
        "pycoreloop",
        "PacketDict",
        "Packet_Unsupported",
    ):
        assert name not in uncrater.__all__
        assert name not in packet_module.__all__


def test_utils_appid_compatibility_wrappers_forward_lazily():
    wrapper_names = set(appids.__all__) - {"id", "appid"}
    assert wrapper_names <= set(utils.__all__)

    for name in wrapper_names:
        wrapper = getattr(utils, name)
        implementation = getattr(appids, name)
        if name == "appid_is_cal_any":
            continue
        assert wrapper(0x2F0) == implementation(0x2F0)


def test_existing_packet_classes_and_utilities_remain_importable():
    assert uncrater.Packet_Hello.__name__ == "Packet_Hello"
    assert uncrater.Packet_Spectrum.__name__ == "Packet_Spectrum"
    assert uncrater.Packet_Waveform.__name__ == "Packet_Waveform"
    assert callable(uncrater.Time2Time)
    assert callable(uncrater.process_ADC_stats)
    assert callable(uncrater.rle_decode)


def make_tr_collection():
    collection = uncrater.Collection.__new__(uncrater.Collection)
    collection.tr_spectra = [
        {
            product: SimpleNamespace(
                data=np.array([sample, product], dtype=np.int64)
            )
            for product in range(uncrater.NPRODUCTS)
        }
        for sample in range(2)
    ]
    return collection


def test_np_tr_spectra_channel_is_a_keyword_only_product_alias():
    signature = inspect.signature(uncrater.Collection.np_tr_spectra)
    assert signature.parameters["channel"].kind is inspect.Parameter.KEYWORD_ONLY

    collection = make_tr_collection()
    expected = collection.np_tr_spectra(None, product=3)
    np.testing.assert_array_equal(
        collection.np_tr_spectra(None, channel=3),
        expected,
    )
    np.testing.assert_array_equal(collection.np_tr_spectra(None, 3), expected)
    np.testing.assert_array_equal(
        collection.np_tr_spectra(1, channel=3),
        collection.np_tr_spectra(1, product=3),
    )


def test_np_tr_spectra_rejects_both_aliases_before_selection():
    collection = make_tr_collection()
    with pytest.raises(TypeError, match="aliases"):
        collection.np_tr_spectra(product=3, channel=3)

    collection.tr_spectra = []
    with pytest.raises(TypeError, match="aliases"):
        collection.np_tr_spectra(product=3, channel=3)
