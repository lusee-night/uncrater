import os
import glob

from .Packet import Packet
from .Packet_Hello import Packet_Hello
from .Packet_Heartbeat import Packet_Heartbeat
from .Packet_Housekeep import Packet_Housekeep
from .Packet_Spectrum import Packet_Spectrum, Packet_Metadata
from .Packet_Waveform import Packet_Waveform

from datetime import datetime

if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

# now try to import pycoreloop
try:
    from pycoreloop import appId as id
except ImportError:
    print ("Can't import pycoreloop\n")
    print ("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo.")
    sys.exit(1)



PacketDict = {id.AppID_uC_Housekeeping:Packet_Housekeep, 
              id.AppID_uC_Start:Packet_Hello, 
              id.AppID_uC_Heartbeat:Packet_Heartbeat, 
              id.AppID_MetaData:Packet_Metadata}

for i in range(16):
    PacketDict[id.AppID_SpectraHigh+i] = Packet_Spectrum
    PacketDict[id.AppID_SpectraMed+i] = Packet_Spectrum
    PacketDict[id.AppID_SpectraLow+i] = Packet_Spectrum

for i in range(4):
    PacketDict[id.AppID_RawADC+i] = Packet_Waveform


PacketDict[0x4f0] = Packet_Waveform

class Collection:

    def __init__ (self, dir):
        self.dir = dir
        self.refresh()

    def refresh(self):
        self.cont = []
        self.time = []
        self.desc = []
        self.spectra = []
        flist = sorted(glob.glob(os.path.join(self.dir, '*.bin')))
        for i,fn in enumerate(flist):
            #print ("reading ",fn)
            appid = int(fn.replace('.bin','').split("_")[-1],16)
            _Packet = PacketDict.get(appid,Packet)
            packet = _Packet(appid, blob_fn = fn)
            if appid==0x20F:
                packet.read()
                format, expected_packet_id = packet.format, packet.packet_id
                self.spectra.append({'meta':packet})
                
            if ((appid>=id.AppID_SpectraHigh and appid<AppID_SpectraHigh+16) or
                (appid>=id.AppID_SpectraMed and appid<AppID_SpectraMed+16) or
                (appid>=id.AppID_SpectraLow and appid<AppID_SpectraLow+16)):
                    packet.set_expected(format, expected_packet_id)
                    self.spectra[-1][appid & 0x0F] = packet

            self.cont.append(packet)
            self.time.append(os.path.getmtime(fn))
            try:
                dt= self.time[-1]-self.time[0]
                self.desc.append(f"{i:4d} : +{dt:4.1f}s : 0x{appid:0x} : {self.cont[-1].desc}")
            except:
                pass

    def __len__(self):
        return len(self.cont)

    def list(self):
        return "\n".join(self.desc)
    
    def _intro(self,i):
        desc =  f"Packet #{i}\n"
        received_time = datetime.fromtimestamp(self.time[i])
        dt = self.time[i]-self.time[0]
        desc += f"Received at {received_time}, dt = {dt}s\n\n"
        return desc

    def info(self,i, intro=False):
        if intro:
            return self._intro(i) + self.cont[i].info()
        return self.cont[i].info()
    
    def xxd (self,i, intro=False):
        if intro:
            return self._intro(i) + self.cont[i].xxd()
        return self.cont[i].xxd()
    
    


