# Various utils
from .Packet import id
from .Packet import appId_from_value
def Time2Time(time1, time2):
    """Converts the 2 16-bit time values to a single time expressed in seconds.
    Magic 244us is the tick time according to grande Jack.   
    """
    time = (((time2 & 0xFFFF) << 32)+time1)*244e-6/16
    return time


def appid_is_spectrum(appid):
    return ((appid>=id.AppID_SpectraHigh) and (appid<id.AppID_SpectraLow+16))

def appid_is_metadata(appid):
    return (appid==id.AppID_MetaData)

def appid_to_str(appid):
    if appid == 0x4f0:
        appid = 0x2f0
    if appid>0x210:
        appid = (appid & 0xFFF0)
    return appId_from_value[appid]