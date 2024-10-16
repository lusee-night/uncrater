import os, sys
import glob


from datetime import datetime

from .Packet import *


class Collection:

    def __init__(self, dir):
        self.dir = dir
        self.refresh()

    def refresh(self):
        self.cont = []
        self.time = []
        self.desc = []
        self.spectra = []
        self.tr_spectra = []
        flist = glob.glob(os.path.join(self.dir, "*.bin"))
        print(f"Ananlyzing {len(flist)} files from {self.dir}.")
        flist = sorted(flist, key=lambda x: int(x[x.rfind("/") + 1 :].split("_")[0]))
        for i, fn in enumerate(flist):
            # print ("reading ",fn)
            appid = int(fn.replace(".bin", "").split("_")[-1], 16)
            packet = Packet(appid, blob_fn=fn)
            if appid_is_metadata(appid):
                packet.read()
                meta_packet = packet
                self.spectra.append({"meta": packet})
                self.tr_spectra.append({"meta": packet})

            if appid_is_spectrum(appid):
                packet.set_meta(meta_packet)
                self.spectra[-1][appid & 0x0F] = packet

            if appid_is_tr_spectrum(appid):
                packet.set_meta(meta_packet)
                self.tr_spectra[-1][appid & 0x0F] = packet

            self.cont.append(packet)
            self.time.append(os.path.getmtime(fn))
            try:
                dt = self.time[-1] - self.time[0]
                self.desc.append(
                    f"{i:4d} : +{dt:4.1f}s : 0x{appid:0x} : {self.cont[-1].desc}"
                )
            except:
                pass

    def cut_to_hello(self):
        i = len(self.cont) - 1
        num_spectra = 0
        while i >= 0 and not isinstance(self.cont[i], Packet_Hello):
            if isinstance(self.cont[i], Packet_Metadata):
                num_spectra += 1
            i -= 1

        if i < 0:
            i = 0
        self.cont = self.cont[i:]
        self.time = self.time[i:]
        self.desc = self.desc[i:]
        self.spectra = self.spectra[-num_spectra:]

    def __len__(self):
        return len(self.cont)

    def list(self):
        return "\n".join(self.desc)

    def _intro(self, i):
        desc = f"Packet #{i}\n"
        received_time = datetime.fromtimestamp(self.time[i])
        dt = self.time[i] - self.time[0]
        desc += f"Received at {received_time}, dt = {dt}s\n\n"
        return desc

    def info(self, i, intro=False):
        if intro:
            return self._intro(i) + self.cont[i].info()
        return self.cont[i].info()

    def xxd(self, i, intro=False):
        if intro:
            return self._intro(i) + self.cont[i].xxd()
        return self.cont[i].xxd()
