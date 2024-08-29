# Various utils
from .Packet import id
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
