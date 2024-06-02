import os
import glob

from .Packet import Packet
from .Packet_Hello import Packet_Hello
from .Packet_Heartbeat import Packet_Heartbeat
from .Packet_Housekeep import Packet_Housekeep
from .Packet_Spectrum import Packet_Spectrum, Packet_Metadata
from .Packet_Waveform import Packet_Waveform

from datetime import datetime

PacketDict = {0x206:Packet_Housekeep, 0x209:Packet_Hello, 0x20A:Packet_Heartbeat, 0X20F:Packet_Metadata}
for i in range(16):
    PacketDict[0x210+i] = Packet_Spectrum

for i in range(4):
    PacketDict[0x2f0+i] = Packet_Waveform


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
            appid = int(fn.replace('.bin','').split("_")[-1],16)
            _Packet = PacketDict.get(appid,Packet)
            packet = _Packet(appid, blob_fn = fn)
            if appid==0x20F:
                packet.read()
                format, expected_packet_id = packet.format, packet.packet_id
                cspectrum = {'meta':packet}
                
            if appid>=0x210 and appid<=0x21F:
                packet.set_expected(format, expected_packet_id)
                cspectrum[appid-0x210] = packet
                if appid==0x21F:
                    self.spectra.append(cspectrum)

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
    
    


