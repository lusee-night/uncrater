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
        tr_spectra = []
        self.heartbeat_packets = []
        self.housekeeping_packets = []
        flist = glob.glob(os.path.join(self.dir, "*.bin"))
        print(f"Analyzing {len(flist)} files from {self.dir}.")
        flist = sorted(flist, key=lambda x: int(x[x.rfind("/") + 1 :].split("_")[0]))
        meta_packet = None
        for i, fn in enumerate(flist):
            # print ("reading ",fn)
            appid = int(fn.replace(".bin", "").split("_")[-1], 16)
            packet = Packet(appid, blob_fn=fn)
            if not (appid_is_spectrum(appid) or appid_is_tr_spectrum(appid)):
                packet.read()
            if appid_is_metadata(appid):
                meta_packet = packet
                self.spectra.append({"meta": packet})
                tr_spectra.append({"meta": packet})

            if appid_is_spectrum(appid):
                if meta_packet is not None:
                    packet.set_meta(meta_packet)
                    packet.read()
                    self.spectra[-1][appid & 0x0F] = packet

            if appid_is_tr_spectrum(appid):
                # print(f"TR appid = {appid}, from file {fn},  {fn.replace(".bin", "").split("_")[-1]}")
                if meta_packet is not None:
                    packet.set_meta(meta_packet)
                    packet.read()
                    tr_spectra[-1][appid & 0x0F] = packet

            if appid_is_heartbeat(appid):
                self.heartbeat_packets.append(packet)

            if appid_is_housekeeping(appid):
                self.housekeeping_packets.append(packet)

            self.cont.append(packet)
            self.time.append(os.path.getmtime(fn))
            try:
                dt = self.time[-1] - self.time[0]
                self.desc.append(
                    f"{i:4d} : +{dt:4.1f}s : 0x{appid:0x} : {self.cont[-1].desc}"
                )
            except:
                pass
        self.tr_spectra = [trs for trs in tr_spectra if len(trs) > 1]
        assert all(["meta" in trs for trs in tr_spectra])

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

    # return number of spectra packets received
    def num_spectra_packets(self) -> int:
        return len(self.spectra)

    # return number of time resolved spectra packets received
    def num_tr_spectra_packets(self) -> int:
        return len(self.tr_spectra)

    # return number of heartbeat packets received
    def num_heartbeats(self) -> int:
        return len(self.heartbeat_packets)

    # return number of housekeeping packets received
    def num_housekeeping_packets(self) -> int:
        return len(self.housekeeping_packets)

    # return 1, if all heartbeat packets are present (no gaps in packet_count sequence)
    def hearbeat_counter_ok(self) -> int:
        hb_counts = [p.packet_count for p in self.heartbeat_packets]
        correct_hb_counts = []
        for i, p in enumerate(self.heartbeat_packets):
            if i == 0:
                correct_hb_counts.append(p.packet_count)
            else:
                correct_hb_counts.append(correct_hb_counts[i - 1] + 1)

        if hb_counts != correct_hb_counts:
            print(f"Bad heartbeat counts! {hb_counts} != {correct_hb_counts}")
            return 0
        return 1

    # return maximal time difference between heartbeat packets
    def heartbeat_max_dt(self) -> int:
        hb_times = [p.time for p in self.heartbeat_packets]
        deltas = [t2 - t1 for t2, t1 in zip(hb_times[1:], hb_times[:-1])]
        return max(deltas)

    # return minimal time difference between heartbeat packets
    def heartbeat_min_dt(self) -> int:
        hb_times = [p.time for p in self.heartbeat_packets]
        deltas = [t2 - t1 for t2, t1 in zip(hb_times[1:], hb_times[:-1])]
        return min(deltas)

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

    # bcheckmark in TeX want an int 0/1 flag, not bool
    # return 1, if all 16 products are present
    def has_all_products(self) -> int:
        for s, prods in enumerate(self.spectra):
            for i in range(16):
                if i not in prods:
                    print(f"Product {i} missing in spectra {s}.")
                    return 0
        return 1

    # return 1, if all 16 time-resolved packets are present
    def has_all_tr_products(self) -> int:
        for s, trs in enumerate(self.tr_spectra):
            for i in range(16):
                if i not in trs:
                    print(f"Product {i} missing in TR spectra {s}.")
                    return 0
        return 1

    # return 1, if all spectra packets have correct CRC
    def all_spectra_crc_ok(self) -> int:
        for i, prods in enumerate(self.spectra):
            for k in range(16):
                if k in prods and prods[k].error_crc_mismatch:
                    print(f"Bad CRC in product {k} in spectra {i}.")
                    return 0
        return 1

    # return 1, if all time-resolved spectra packets have correct CRC
    def all_tr_spectra_crc_ok(self) -> int:
        for i, trs in enumerate(self.tr_spectra):
            for k in range(16):
                if k in trs and trs[k].error_crc_mismatch:
                    print(
                        f"Bad CRC in product {k} in TR spectra {i}, incorrect CRC: {trs[k].crc}."
                    )
                    return 0
        return 1

    def xxd(self, i, intro=False):
        if intro:
            return self._intro(i) + self.cont[i].xxd()
        return self.cont[i].xxd()
