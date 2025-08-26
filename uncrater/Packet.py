import os, sys

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

# now try to import pycoreloop
try:
    from pycoreloop import appId as id
    from pycoreloop import appId_from_value, value_from_appId
except ImportError:
    print("Can't import pycoreloop\n")
    print(
        "Please install the package or setup CORELOOP_DIR to point at CORELOOP repo. [Collection.py]"
    )
    sys.exit(1)


from .PacketBase import PacketBase
from .Packet_Hello import Packet_Hello
from .Packet_Heartbeat import Packet_Heartbeat
from .Packet_Housekeep import Packet_Housekeep
from .Packet_Spectrum import Packet_Spectrum, Packet_TR_Spectrum, Packet_Metadata
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
    id.AppID_Calibrator_MetaData: Packet_Cal_Metadata,
    id.AppID_Calibrator_Data: Packet_Cal_Data,
    id.AppID_Calibrator_Data+1: Packet_Cal_Data,
    id.AppID_Calibrator_Data+2: Packet_Cal_Data,
    id.AppID_Calibrator_Debug: Packet_Cal_Debug,
    id.AppID_ZoomSpectra: Packet_Cal_ZoomSpectra,
    id.AppID_RawADC_Meta: Packet_Waveform_Meta,
}

for i in range(16):
    PacketDict[id.AppID_SpectraHigh + i] = Packet_Spectrum
    PacketDict[id.AppID_SpectraMed + i] = Packet_Spectrum
    PacketDict[id.AppID_SpectraLow + i] = Packet_Spectrum

for i in range(16):
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
        (appid >= id.AppID_SpectraHigh and appid < id.AppID_SpectraHigh + 16)
        or (appid >= id.AppID_SpectraMed and appid < id.AppID_SpectraMed + 16)
        or (appid >= id.AppID_SpectraLow and appid < id.AppID_SpectraLow + 16)
    )


def appid_is_tr_spectrum(appid):
    return (
        (appid >= id.AppID_SpectraTRHigh and appid < id.AppID_SpectraTRHigh + 16)
        or (appid >= id.AppID_SpectraTRMed and appid < id.AppID_SpectraTRMed + 16)
        or (appid >= id.AppID_SpectraTRLow and appid < id.AppID_SpectraTRLow + 16)
    )

def appid_is_cal_any(appid):
    return (appid >= id.AppID_Calibrator_Data) and (appid < id.AppID_Calibrator_Data + 20)

def appid_is_cal_data(appid):
    return (appid >= id.AppID_Calibrator_Data) and (appid < id.AppID_Calibrator_Data + 3)

def appid_is_cal_data_start(appid):
    return (appid == id.AppID_Calibrator_Data) 


def  appid_is_rawPFB(appid):
    return (appid >= id.AppID_Calibrator_RawPFB) and (appid < id.AppID_Calibrator_RawPFB + 8)

def  appid_is_rawPFB_start(appid):
    return (appid == id.AppID_Calibrator_RawPFB)

def appid_is_cal_zoom(appid):
    return appid == id.AppID_ZoomSpectra

def appid_is_cal_debug(appid):
    return (appid >= id.AppID_Calibrator_Debug) and (appid < id.AppID_Calibrator_Debug + 8)

def appid_is_cal_debug_start(appid):
    return (appid == id.AppID_Calibrator_Debug)



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
