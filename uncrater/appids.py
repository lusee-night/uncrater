"""Latest-schema Application-ID predicates and stable display names.

The current public truth table follows the named AppIDs emitted by coreloop,
not the wider CDI routing bins. Historical packet dispatch belongs to the
selected schema binding rather than these latest-schema helpers.
"""

from __future__ import annotations

import warnings

from .schema_registry import LATEST_BINDING


id = LATEST_BINDING.appids
appid = id


def normalize_dcb_appid(value: int) -> int:
    """Return the canonical RFS AppID for a DCB-reported AppID."""
    # Only this RawADC value is rewritten by the DCB; adjacent IDs are not aliases
    if value == 0x4F0:
        return 0x2F0
    return value


def appid_is_hello(value: int) -> bool:
    return value == 0x209


def appid_is_metadata(value: int) -> bool:
    return value == 0x20F


def appid_is_housekeeping(value: int) -> bool:
    return value == 0x206


def appid_is_heartbeat(value: int) -> bool:
    return value == 0x20A


def appid_is_watchdog(value: int) -> bool:
    return value == 0x20C


def appid_is_fw_watchdog(value: int) -> bool:
    return value == 0x2FF


def appid_is_spectrum(value: int) -> bool:
    return 0x210 <= value <= 0x23F


def appid_is_tr_spectrum(value: int) -> bool:
    return 0x240 <= value <= 0x26F


def appid_is_zoom_spectrum(value: int) -> bool:
    return value == 0x270


def appid_is_grimm_spectrum(value: int) -> bool:
    return value == 0x2A0


def appid_is_cal_metadata(value: int) -> bool:
    return value == 0x280


def appid_is_cal_data(value: int) -> bool:
    return 0x281 <= value <= 0x283


def appid_is_cal_data_start(value: int) -> bool:
    return value == 0x281


def appid_is_cal_raw_pfb(value: int) -> bool:
    return 0x284 <= value <= 0x28B


def appid_is_cal_raw_pfb_start(value: int) -> bool:
    return value == 0x284


def appid_is_cal_debug(value: int) -> bool:
    return 0x28C <= value <= 0x293


def appid_is_cal_debug_start(value: int) -> bool:
    return value == 0x28C


def appid_is_cal_segmented_payload(value: int) -> bool:
    return 0x281 <= value <= 0x293


def appid_is_calibrator_product(value: int) -> bool:
    return value == 0x270 or 0x280 <= value <= 0x293


def appid_is_fw_direct_spectrum(value: int) -> bool:
    return 0x2E0 <= value <= 0x2E3


def appid_is_raw_adc(value: int) -> bool:
    return 0x2F0 <= value <= 0x2F3


def appid_is_waveform(value: int) -> bool:
    return appid_is_raw_adc(value)


def appid_is_raw_adc_metadata(value: int) -> bool:
    return value == 0x2FA


def appid_is_cal_any(value: int) -> bool:
    """Return whether an AppID is a deferred calibrator payload page."""
    # Historical callers use this to defer multipart payloads; metadata and
    # zoom packets must still be decoded immediately
    warnings.warn(
        "appid_is_cal_any() is deprecated; use "
        "appid_is_cal_segmented_payload()",
        DeprecationWarning,
        stacklevel=2,
    )
    return appid_is_cal_segmented_payload(value)


def appid_is_rawPFB(value: int) -> bool:
    return appid_is_cal_raw_pfb(value)


def appid_is_rawPFB_start(value: int) -> bool:
    return appid_is_cal_raw_pfb_start(value)


def appid_is_cal_zoom(value: int) -> bool:
    return appid_is_zoom_spectrum(value)


# Generated bindings name the first member of a family. Exact lookup must run
# before offset formatting so those established names remain unchanged
_EXACT_NAMES = {
    value: name
    for name, value in vars(id).items()
    if name.startswith("AppID_")
    and "Reserved" not in name
    and isinstance(value, int)
}

# These are the only gaps explicitly designated as reserved by the latest
# AppID source; other currently unused values remain unknown
_RESERVED_APPIDS = frozenset((0x20D, 0x20E, *range(0x294, 0x2A0)))


def _family_name(value: int) -> str | None:
    families = (
        (0x210, 0x21F, "AppID_SpectraHigh", "product"),
        (0x220, 0x22F, "AppID_SpectraMed", "product"),
        (0x230, 0x23F, "AppID_SpectraLow", "product"),
        (0x240, 0x24F, "AppID_SpectraTRHigh", "product"),
        (0x250, 0x25F, "AppID_SpectraTRMed", "product"),
        (0x260, 0x26F, "AppID_SpectraTRLow", "product"),
        (0x281, 0x283, "AppID_Calibrator_Data", "page"),
        (0x28C, 0x293, "AppID_Calibrator_Debug", "page"),
        (0x2E0, 0x2E3, "AppID_FW_DirectSpectrum", "channel"),
        (0x2F0, 0x2F3, "AppID_RawADC", "channel"),
    )
    for start, stop, name, offset_name in families:
        if start <= value <= stop:
            return f"{name}[{offset_name}={value - start}]"

    if 0x284 <= value <= 0x28B:
        offset = value - 0x284
        part = "real" if offset % 2 == 0 else "imag"
        return f"AppID_Calibrator_RawPFB[channel={offset // 2},part={part}]"
    return None


def _format_appid(value: int) -> str:
    if value < 0:
        return f"-0x{-value:X}"
    return f"0x{value:03X}"


def appid_to_str(value: int) -> str:
    """Return a stable exact, family, reserved, or unknown AppID name."""
    exact = _EXACT_NAMES.get(value)
    if exact is not None:
        return exact
    family = _family_name(value)
    if family is not None:
        return family
    if value in _RESERVED_APPIDS:
        return f"Reserved({_format_appid(value)})"
    return f"Unknown({_format_appid(value)})"


__all__ = [
    "id",
    "appid",
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
]
