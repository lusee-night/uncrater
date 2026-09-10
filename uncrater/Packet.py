import os, sys

from . import appids as appid_helpers
from .constants import NPRODUCTS
from .coreloop import pycoreloop
from .packet_dispatch import dispatch_packet
id = pycoreloop.appId
appid = id
appId_from_value = pycoreloop.appId_from_value
value_from_appId = pycoreloop.value_from_appId
    

from .PacketBase import PacketBase, Packet_Unsupported
from .Packet_Hello import Packet_Hello
from .Packet_Heartbeat import Packet_Heartbeat
from .Packet_Housekeep import Packet_Housekeep
from .Packet_Spectrum import Packet_Spectrum, Packet_TR_Spectrum, Packet_Metadata, Packet_Grimm
from .Packet_Waveform import Packet_Waveform, Packet_Waveform_Meta  
from .Packet_Bootloader import Packet_Bootloader
from .Packet_Calibrator import Packet_Cal_Metadata, Packet_Cal_Data, Packet_Cal_RawPFB, Packet_Cal_Debug, Packet_Cal_ZoomSpectra
from .Packet_EOS import Packet_EOS
from .Packet_Watchdog import Packet_Watchdog

PacketDict = {
    id.AppID_uC_Housekeeping: Packet_Housekeep,
    id.AppID_uC_Start: Packet_Hello,
    id.AppID_uC_Heartbeat: Packet_Heartbeat,
    id.AppID_Watchdog: Packet_Watchdog,
    id.AppID_FW_Watchdog: Packet_Watchdog,
    id.AppID_End_Of_Sequence: Packet_EOS,
    id.AppID_MetaData: Packet_Metadata,
    id.AppID_SpectraGrimm: Packet_Grimm, 
    id.AppID_Calibrator_MetaData: Packet_Cal_Metadata,
    id.AppID_Calibrator_Data: Packet_Cal_Data,
    id.AppID_Calibrator_Data+1: Packet_Cal_Data,
    id.AppID_Calibrator_Data+2: Packet_Cal_Data,
    id.AppID_Calibrator_Debug: Packet_Cal_Debug,
    id.AppID_ZoomSpectra: Packet_Cal_ZoomSpectra,
    id.AppID_RawADC_Meta: Packet_Waveform_Meta,
}

for i in range(NPRODUCTS):
    PacketDict[id.AppID_SpectraHigh + i] = Packet_Spectrum
    PacketDict[id.AppID_SpectraMed + i] = Packet_Spectrum
    PacketDict[id.AppID_SpectraLow + i] = Packet_Spectrum

for i in range(NPRODUCTS):
    PacketDict[id.AppID_SpectraTRHigh + i] = Packet_TR_Spectrum
    PacketDict[id.AppID_SpectraTRMed + i] = Packet_TR_Spectrum
    PacketDict[id.AppID_SpectraTRLow + i] = Packet_TR_Spectrum

for i in range(4):
    PacketDict[id.AppID_FW_DirectSpectrum + i] = Packet_Unsupported
    PacketDict[id.AppID_RawADC + i] = Packet_Waveform
    
for i in range(8):
    PacketDict[id.AppID_Calibrator_RawPFB + i] = Packet_Cal_RawPFB
    PacketDict[id.AppID_Calibrator_Debug + i] = Packet_Cal_Debug

PacketDict[id.AppID_uC_Bootloader] = Packet_Bootloader


def Packet(appid, blob=None, blob_fn=None, **kwargs):
    return dispatch_packet(appid, blob=blob, blob_fn=blob_fn, **kwargs)


def appid_is_hello(appid):
    return appid_helpers.appid_is_hello(appid)


def appid_is_spectrum(appid):
    return appid_helpers.appid_is_spectrum(appid)


def appid_is_tr_spectrum(appid):
    return appid_helpers.appid_is_tr_spectrum(appid)


def appid_is_raw_adc(appid: int) -> bool:
    return appid_helpers.appid_is_raw_adc(appid)


def appid_is_zoom_spectrum(appid: int) -> bool:
    return appid_helpers.appid_is_zoom_spectrum(appid)


def appid_is_grimm_spectrum(appid: int) -> bool:
    return appid_helpers.appid_is_grimm_spectrum(appid)


def appid_is_cal_any(appid):
    return appid_helpers.appid_is_cal_any(appid)


def appid_is_cal_data(appid):
    return appid_helpers.appid_is_cal_data(appid)


def appid_is_cal_data_start(appid):
    return appid_helpers.appid_is_cal_data_start(appid)


def  appid_is_rawPFB(appid):
    return appid_helpers.appid_is_rawPFB(appid)


def  appid_is_rawPFB_start(appid):
    return appid_helpers.appid_is_rawPFB_start(appid)


def appid_is_cal_zoom(appid):
    return appid_helpers.appid_is_cal_zoom(appid)


def appid_is_cal_debug(appid):
    return appid_helpers.appid_is_cal_debug(appid)


def appid_is_cal_debug_start(appid):
    return appid_helpers.appid_is_cal_debug_start(appid)


def appid_is_metadata(appid):
    return appid_helpers.appid_is_metadata(appid)


def appid_is_watchdog(appid):
    return appid_helpers.appid_is_watchdog(appid)


def appid_is_heartbeat(appid):
    return appid_helpers.appid_is_heartbeat(appid)


def appid_is_housekeeping(appid):
    return appid_helpers.appid_is_housekeeping(appid)


def appid_is_waveform(appid):
    return appid_helpers.appid_is_waveform(appid)


def appid_to_str(appid):
    return appid_helpers.appid_to_str(appid)


normalize_dcb_appid = appid_helpers.normalize_dcb_appid
appid_is_cal_metadata = appid_helpers.appid_is_cal_metadata
appid_is_cal_raw_pfb = appid_helpers.appid_is_cal_raw_pfb
appid_is_cal_raw_pfb_start = appid_helpers.appid_is_cal_raw_pfb_start
appid_is_cal_segmented_payload = appid_helpers.appid_is_cal_segmented_payload
appid_is_calibrator_product = appid_helpers.appid_is_calibrator_product
appid_is_fw_direct_spectrum = appid_helpers.appid_is_fw_direct_spectrum
appid_is_fw_watchdog = appid_helpers.appid_is_fw_watchdog
appid_is_raw_adc_metadata = appid_helpers.appid_is_raw_adc_metadata


__all__ = [
    "Packet",
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
    "appId_from_value",
    "value_from_appId",
    *appid_helpers.__all__,
]
