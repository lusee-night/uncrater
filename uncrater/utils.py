# Various utils
from .Packet import id
from .Packet import appId_from_value

import numpy as np


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


def process_ADC_stats(ADC_stat):
    """Process the ADC stats from the housekeeping packet
    """
    minv = np.array([x.min-0x1fff for x in ADC_stat])
    maxv = np.array([x.max-0x1fff for x in ADC_stat])
    valid_count = np.array([x.valid_count for x in ADC_stat])
    invalid_count_max = np.array([x.invalid_count_max for x in ADC_stat])
    invalid_count_min = np.array([x.invalid_count_min for x in ADC_stat])
    sumx = np.array([x.sumv for x in ADC_stat])
    sumxx = np.array([x.sumv2 for x in ADC_stat])
    mean = sumx/valid_count-0x1fff
    var = sumxx/valid_count-(sumx/valid_count)**2
    mean[valid_count == 0] = 0 
    var[valid_count ==0 ] = 0
    total_count = valid_count+invalid_count_min+invalid_count_max
    rms = np.sqrt(var)

    toret = {'min':minv, 'max':maxv, 'valid_count':valid_count, 'invalid_count_max':invalid_count_max, 'invalid_count_min':invalid_count_min, 'total_count':total_count, 'mean':mean, 'rms':rms}
    return toret