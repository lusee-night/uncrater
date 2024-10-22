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
from .Packet_Waveform import Packet_Waveform

PacketDict = {
    id.AppID_uC_Housekeeping: Packet_Housekeep,
    id.AppID_uC_Start: Packet_Hello,
    id.AppID_uC_Heartbeat: Packet_Heartbeat,
    id.AppID_MetaData: Packet_Metadata,
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
## workaround for FW bug
PacketDict[0x4F0] = Packet_Waveform


def Packet(appid, blob=None, blob_fn=None, **kwargs):
    if (blob is None) and (blob_fn is None):
        raise ValueError
    PacketType = PacketDict.get(appid, PacketBase)
    return PacketType(appid, blob=blob, blob_fn=blob_fn, **kwargs)


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


def appid_is_metadata(appid):
    return appid == id.AppID_MetaData


def appid_to_str(appid):
    if appid == 0x4F0:
        appid = 0x2F0
    if appid > 0x210:
        appid = appid & 0xFFF0
    return appId_from_value[appid]
