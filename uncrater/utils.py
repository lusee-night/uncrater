# Various utils


def Time2Time(time1, time2):
    """Converts the 2 16-bit time values to a single time expressed in seconds.
    Magic 244us is the tick time according to grande Jack.   
    """
    time = (((time2 & 0xFFFF) << 32)+time1)*244e-6/16
    return time