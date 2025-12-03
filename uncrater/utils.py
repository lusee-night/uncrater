# Various utils
from .Packet import id
from .Packet import appId_from_value

import numpy as np

NPRODUCTS = 16          # number of spectral products
NCHANNELS = 2048        # number of channels in each spectral product
N_WF_PACKETS = 4        # number of waveform packets (raw ADC)
N_CAL_DEBUG_MODES = 8   # number of calibrator debug modes


def Time2Time(time1, time2):
    """Converts the the two time values to a single time expressed in seconds.
    Magic 244us is the tick time according to grande Jack.   
    """
    time = ((((time2 & 0xFFFF) << 32)+time1)>>4)*1/4096
    return time


def appid_is_spectrum(appid):
    return appid >= id.AppID_SpectraHigh and appid < id.AppID_SpectraLow+NPRODUCTS


def appid_is_metadata(appid: int):
    return appid == id.AppID_MetaData


def appid_is_tr_spectrum(appid: int):
    if id.AppID_SpectraTRHigh <= appid < id.AppID_SpectraTRHigh + NPRODUCTS:
        return True
    if id.AppID_SpectraTRMed <= appid < id.AppID_SpectraTRMed + NPRODUCTS:
        return True
    if id.AppID_SpectraTRLow <= appid < id.AppID_SpectraTRLow + NPRODUCTS:
        return True
    return False


def appid_is_zoom_spectrum(appid: int):
    return id.AppID_ZoomSpectra <= appid < id.AppID_ZoomSpectra + NPRODUCTS


def appid_is_grimm_spectrum(appid: int):
    return id.AppID_SpectraGrimm == appid


# Waveform packet
def appid_is_raw_adc(appid):
    return id.AppID_RawADC <= appid < id.AppID_RawADC + N_WF_PACKETS


# we have 8 different calibrator debug modes,
# according to lusee_appids
def appid_is_cal_debug(appid: int) -> bool:
    return id.AppID_Calibrator_Debug <= appid < id.AppID_Calibrator_Debug + N_CAL_DEBUG_MODES


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
    w = np.where(valid_count>0)
    mean = np.zeros(4)
    var = np.zeros(4)
    mean[w] = sumx[w]/valid_count[w]-0x1fff
    var[w] = sumxx[w]/valid_count[w]-(sumx[w]/valid_count[w])**2
    mean[valid_count == 0] = 0 
    var[valid_count ==0 ] = 0
    total_count = valid_count+invalid_count_min+invalid_count_max
    var[var<0] = 0
    rms = np.sqrt(var)

    toret = {'min':minv, 'max':maxv, 'valid_count':valid_count, 'invalid_count_max':invalid_count_max, 'invalid_count_min':invalid_count_min, 'total_count':total_count, 'mean':mean, 'rms':rms}
    return toret

def process_telemetry(TVS_sensors):
    """Process the telemetry from the housekeeping packet
    """
    toret = {}
    def bits2volts (val):
        return (val/16000)
        
    def bits2celsius (val):        
        return val/128-273.15
    
    toret['V1_0'] = bits2volts(TVS_sensors[0])    
    toret['V1_8'] = bits2volts(TVS_sensors[1])    
    toret['V2_5'] = bits2volts(TVS_sensors[2])    
    toret['T_FPGA'] = bits2celsius(TVS_sensors[3])
    return toret


def cordic2rad (val):
    b30 = (1<<30)
    b31 = (1<<31)
    b32 = (1<<32)
    sign = (val & b31) >> 30
    val = val & (b31-1)
    if type(val)==int:
        if (val>b30):
            val = val-b31
        assert (val<=b31)    
    else:
        val[val>b30] = val[val>b30]-b31
        assert (np.all(val<=b31))
    
    rad =  val/(b30)*np.pi  * (-1)**sign

    return rad

def rad2cordic(val):
    b30 = (1<<30)
    b32 = (1<<32)
    if (val>np.pi):
        val = val-2*np.pi
    if (val<-np.pi):
        val = val+2*np.pi
    return round(abs(val/np.pi*b30))+(b32*(val<0))

def cordic_add (val1,val2):
    val = (val1+val2)
    topbits = (val>>30)
    val = val & 0x3FFFFFFF
    if topbits == 0b01:
        val = 0b11<<30 | val
    elif topbits == 0b10:
        val = 0b01<<30 | val

    return val
