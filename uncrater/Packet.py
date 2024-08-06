import os, sys


if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

# now try to import pycoreloop
try:
    from pycoreloop import appId as id
except ImportError:
    print ("Can't import pycoreloop\n")
    print ("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo. [Collection.py]")
    sys.exit(1)


from .PacketBase import PacketBase
from .Packet_Hello import Packet_Hello
from .Packet_Heartbeat import Packet_Heartbeat
from .Packet_Housekeep import Packet_Housekeep
from .Packet_Spectrum import Packet_Spectrum, Packet_Metadata
from .Packet_Waveform import Packet_Waveform

PacketDict = {id.AppID_uC_Housekeeping:Packet_Housekeep, 
              id.AppID_uC_Start:Packet_Hello, 
              id.AppID_uC_Heartbeat:Packet_Heartbeat, 
              id.AppID_MetaData:Packet_Metadata
              }

for i in range(16):
    PacketDict[id.AppID_SpectraHigh+i] = Packet_Spectrum
    PacketDict[id.AppID_SpectraMed+i] = Packet_Spectrum
    PacketDict[id.AppID_SpectraLow+i] = Packet_Spectrum

for i in range(4):
    PacketDict[id.AppID_RawADC+i] = Packet_Waveform
## workaround for FW bug
PacketDict[0x4f0] = Packet_Waveform


def Packet(appid, blob=None, blob_fn=None):
    if (blob is None) and (blob_fn is None):
        raise ValueError
    PacketType = PacketDict.get(appid,PacketBase)
    return PacketType(appid, blob=blob, blob_fn = blob_fn)


