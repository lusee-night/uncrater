import os, sys

from .constants import NPRODUCTS
from .coreloop import pycoreloop
id = pycoreloop.appId
appId_from_value = pycoreloop.appId_from_value
value_from_appId = pycoreloop.value_from_appId
    

from .PacketBase import PacketBase
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
    PacketDict[id.AppID_RawADC + i] = Packet_Waveform
    
for i in range(8):
    PacketDict[id.AppID_Calibrator_RawPFB + i] = Packet_Cal_RawPFB
    PacketDict[id.AppID_Calibrator_Debug + i] = Packet_Cal_Debug

PacketDict[id.AppID_uC_Bootloader] = Packet_Bootloader


def Packet(appid, blob=None, blob_fn=None, **kwargs):
    if (blob is None) and (blob_fn is None):
        raise ValueError
    PacketType = PacketDict.get(appid, PacketBase)
    return PacketType(appid, blob=blob, blob_fn=blob_fn, **kwargs)


def appid_is_hello(appid):
    return appid == id.AppID_uC_Start


def appid_is_spectrum(appid):
    return (
          id.AppID_SpectraHigh <= appid < id.AppID_SpectraHigh + NPRODUCTS
        or id.AppID_SpectraMed <= appid < id.AppID_SpectraMed + NPRODUCTS
        or id.AppID_SpectraLow <= appid < id.AppID_SpectraLow + NPRODUCTS
    )


def appid_is_tr_spectrum(appid):
    return (
          id.AppID_SpectraTRHigh <= appid < id.AppID_SpectraTRHigh + NPRODUCTS
        or id.AppID_SpectraTRMed <= appid < id.AppID_SpectraTRMed + NPRODUCTS
        or id.AppID_SpectraTRLow <= appid < id.AppID_SpectraTRLow + NPRODUCTS
    )


def appid_is_raw_adc(appid: int) -> bool:
    return id.appId.AppID_RawADC <= appid < id.appId.AppID_RawADC + 4


def appid_is_zoom_spectrum(appid: int) -> bool:
    return appid == id.appId.AppID_ZoomSpectra


def appid_is_grimm_spectrum(appid: int) -> bool:
    return appid == id.appId.AppID_SpectraGrimm


def appid_is_cal_any(appid):
    return id.AppID_Calibrator_Data <=  appid < id.AppID_Calibrator_Data + 20


def appid_is_cal_data(appid):
    return id.AppID_Calibrator_Data <= appid < id.AppID_Calibrator_Data + 3


def appid_is_cal_data_start(appid):
    return appid == id.AppID_Calibrator_Data


def  appid_is_rawPFB(appid):
    return id.AppID_Calibrator_RawPFB <= appid < id.AppID_Calibrator_RawPFB + 8


def  appid_is_rawPFB_start(appid):
    return appid == id.AppID_Calibrator_RawPFB


def appid_is_cal_zoom(appid):
    return appid == id.AppID_ZoomSpectra


def appid_is_cal_debug(appid):
    return id.AppID_Calibrator_Debug <= appid < id.AppID_Calibrator_Debug + 8


def appid_is_cal_debug_start(appid):
    return appid == id.AppID_Calibrator_Debug


def appid_is_metadata(appid):
    return appid == id.AppID_MetaData


def appid_is_watchdog(appid):
    return appid == id.AppID_Watchdog


def appid_is_heartbeat(appid):
    return appid == id.AppID_uC_Heartbeat


def appid_is_housekeeping(appid):
    return appid == id.AppID_uC_Housekeeping


def appid_is_waveform(appid):
    return appid == id.AppId


def appid_to_str(appid):
    if appid == 0x4F0:
        appid = 0x2F0
    if appid > 0x210:
        appid = appid & 0xFFF0
    return appId_from_value[appid]
