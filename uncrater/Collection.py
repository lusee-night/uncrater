import os
import glob

from .Packet import Packet
from .Packet_Hello import Packet_Hello
from .Packet_Heartbeat import Packet_Heartbeat
from .Packet_Housekeep import Packet_Housekeep
from datetime import datetime

PacketDict = {0x206:Packet_Housekeep, 0x209:Packet_Hello, 0x20A:Packet_Heartbeat}


class Collection:

    def __init__ (self, dir):
        self.dir = dir
        self.refresh()

    def refresh(self):
        self.cont = []
        self.time = []
        self.desc = []
        for i,fn in enumerate(sorted(glob.glob(os.path.join(self.dir, '*.bin')))):
            appid = int(fn.replace('.bin','').split("_")[-1],16)
            _Packet = PacketDict.get(appid,Packet)
            self.cont.append(_Packet(appid, blob_fn = fn))
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