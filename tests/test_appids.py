import pytest

import uncrater.appids as appids


@pytest.mark.parametrize(
    ("predicate_name", "expected"),
    [
        ("appid_is_hello", {0x209}),
        ("appid_is_metadata", {0x20F}),
        ("appid_is_housekeeping", {0x206}),
        ("appid_is_heartbeat", {0x20A}),
        ("appid_is_watchdog", {0x20C}),
        ("appid_is_fw_watchdog", {0x2FF}),
        ("appid_is_spectrum", set(range(0x210, 0x240))),
        ("appid_is_tr_spectrum", set(range(0x240, 0x270))),
        ("appid_is_zoom_spectrum", {0x270}),
        ("appid_is_grimm_spectrum", {0x2A0}),
        ("appid_is_cal_metadata", {0x280}),
        ("appid_is_cal_data", set(range(0x281, 0x284))),
        ("appid_is_cal_data_start", {0x281}),
        ("appid_is_cal_raw_pfb", set(range(0x284, 0x28C))),
        ("appid_is_cal_raw_pfb_start", {0x284}),
        ("appid_is_cal_debug", set(range(0x28C, 0x294))),
        ("appid_is_cal_debug_start", {0x28C}),
        ("appid_is_cal_segmented_payload", set(range(0x281, 0x294))),
        (
            "appid_is_calibrator_product",
            {0x270, *range(0x280, 0x294)},
        ),
        ("appid_is_fw_direct_spectrum", set(range(0x2E0, 0x2E4))),
        ("appid_is_raw_adc", set(range(0x2F0, 0x2F4))),
        ("appid_is_waveform", set(range(0x2F0, 0x2F4))),
        ("appid_is_raw_adc_metadata", {0x2FA}),
    ],
)
def test_latest_predicate_truth_tables(predicate_name, expected):
    predicate = getattr(appids, predicate_name)
    # Check the complete current telemetry region so reserved gaps cannot be
    # accepted accidentally by an overly broad family range
    actual = {value for value in range(0x1FF, 0x301) if predicate(value)}
    assert actual == expected


def test_compatibility_predicates_forward_to_canonical_meanings():
    for value in range(0x1FF, 0x301):
        assert appids.appid_is_rawPFB(value) == appids.appid_is_cal_raw_pfb(value)
        assert (
            appids.appid_is_rawPFB_start(value)
            == appids.appid_is_cal_raw_pfb_start(value)
        )
        assert appids.appid_is_cal_zoom(value) == appids.appid_is_zoom_spectrum(value)

    with pytest.warns(DeprecationWarning, match="segmented"):
        assert appids.appid_is_cal_any(0x281)
    with pytest.warns(DeprecationWarning):
        assert not appids.appid_is_cal_any(0x280)
    with pytest.warns(DeprecationWarning):
        assert not appids.appid_is_cal_any(0x294)


def test_dcb_normalization_is_explicit_and_narrow():
    assert appids.normalize_dcb_appid(0x4F0) == 0x2F0
    assert appids.normalize_dcb_appid(0x4F1) == 0x4F1
    assert appids.normalize_dcb_appid(0x2F0) == 0x2F0
    assert not appids.appid_is_raw_adc(0x4F0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0x200, "AppID_Read_Response"),
        (0x210, "AppID_SpectraHigh"),
        (0x211, "AppID_SpectraHigh[product=1]"),
        (0x21F, "AppID_SpectraHigh[product=15]"),
        (0x220, "AppID_SpectraMed"),
        (0x24F, "AppID_SpectraTRHigh[product=15]"),
        (0x270, "AppID_ZoomSpectra"),
        (0x281, "AppID_Calibrator_Data"),
        (0x282, "AppID_Calibrator_Data[page=1]"),
        (0x284, "AppID_Calibrator_RawPFB"),
        (0x285, "AppID_Calibrator_RawPFB[channel=0,part=imag]"),
        (0x28A, "AppID_Calibrator_RawPFB[channel=3,part=real]"),
        (0x28C, "AppID_Calibrator_Debug"),
        (0x28F, "AppID_Calibrator_Debug[page=3]"),
        (0x2A0, "AppID_SpectraGrimm"),
        (0x2E0, "AppID_FW_DirectSpectrum"),
        (0x2E3, "AppID_FW_DirectSpectrum[channel=3]"),
        (0x2F0, "AppID_RawADC"),
        (0x2F3, "AppID_RawADC[channel=3]"),
        (0x2FA, "AppID_RawADC_Meta"),
        (0x2FF, "AppID_FW_Watchdog"),
        (0x20D, "Reserved(0x20D)"),
        (0x20E, "Reserved(0x20E)"),
        (0x294, "Reserved(0x294)"),
        (0x29F, "Reserved(0x29F)"),
        (0x271, "Unknown(0x271)"),
        (0x2A1, "Unknown(0x2A1)"),
        (0x2E4, "Unknown(0x2E4)"),
        (0x2F4, "Unknown(0x2F4)"),
        (0x2FB, "Unknown(0x2FB)"),
        (0x4F0, "Unknown(0x4F0)"),
        (-1, "Unknown(-0x1)"),
    ],
)
def test_appid_to_str_is_stable(value, expected):
    assert appids.appid_to_str(value) == expected


def test_appid_to_str_never_raises_for_integer_appids():
    for value in range(-1, 0x1000):
        result = appids.appid_to_str(value)
        assert isinstance(result, str)
        assert result


def test_dcb_normalization_can_be_composed_with_appid_naming():
    normalized = appids.normalize_dcb_appid(0x4F0)
    assert appids.appid_to_str(normalized) == "AppID_RawADC"


def test_utils_preserves_lazy_direct_import_compatibility():
    from uncrater.utils import appid_is_spectrum, appid_to_str

    assert appid_is_spectrum is appids.appid_is_spectrum
    assert appid_to_str is appids.appid_to_str
