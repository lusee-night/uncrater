import os, sys
import glob
import numpy as np


from datetime import datetime

from .Packet import *

from .error_utils import *


class Collection:

    def __init__(self, dir, verbose = False, cut_to_hello = False):
        self.verbose = verbose
        self.dir = dir
        self.cut_to_hello = cut_to_hello
        self.refresh()
        
    def refresh(self):
        self.cont = []
        self.time = []
        self.desc = []
        self.spectra = []
        tr_spectra = []
        self.calib = []
        self.heartbeat_packets = []
        self.watchdog_packets = []
        self.housekeeping_packets = []
        self.waveform_packets = []
        flist = glob.glob(os.path.join(self.dir, "*.bin"))
        print(f"Analyzing {len(flist)} files from {self.dir}.")
        flist = sorted(flist, key=lambda x: int(x[x.rfind("/") + 1 :].split("_")[0]))
        meta_packet = None

        self.calib_meta = []
        self.calib_data = []
        self.calib_gNacc = []
        self.calib_gphase = []
        self.calib_pfb = []
        self.calib_debug = []
        waveforms = [None,None,None,None]
        def fn2appid(fn):
            return int(fn.replace(".bin", "").split("_")[-1], 16)
        if self.cut_to_hello:
            appids = [fn2appid(fn) for fn in flist]
            for i in range(len(appids)-1,0,-1):
                if appid_is_hello(appids[i]):
                    flist = flist[i:]
                    break

        for i, fn in enumerate(flist):
            if self.verbose:
                print ("Reading ",fn)
            appid = fn2appid(fn)

            ## sometimes there is initial garbage to throw out
            if appid_is_spectrum(appid) and meta_packet is None:
                continue
            if appid_is_tr_spectrum(appid) and meta_packet is None:
                continue
            
            packet = Packet(appid, blob_fn=fn)

            # spectral/TR spectral packets must be read only after we set their metadata packet
            # all other packets: read immediately
            if not (appid_is_spectrum(appid) or appid_is_tr_spectrum(appid) or appid_is_cal_any(appid)):
                packet.read()
            if appid_is_watchdog(appid):
                packet.read()


            if isinstance(packet, Packet_Metadata):
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

            if isinstance(packet, Packet_Cal_Metadata):
                self.calib_meta.append(packet)

            if appid_is_cal_data(appid):
                def to_cplx(a,b):
                    return np.array(a,complex) + 1j*np.array(b)
                if appid_is_cal_data_start(appid):
                    packet.read()
                    cal_packet_id = packet.unique_packet_id
                    self.calib_data.append([np.array(data,complex) for data in packet.data])
                else:
                    packet.set_meta_id(cal_packet_id)
                    packet.read()
                    if packet.data_page == 1:
                        for a, img_part  in zip(self.calib_data[-1], packet.data):
                            a+= 1j*np.array(img_part)
                    else:
                        self.calib_gNacc.append(packet.gNacc)
                        self.calib_gphase.append(packet.gphase)

                
            if appid_is_rawPFB(appid):
                if appid_is_rawPFB_start(appid):
                    packet.read()
                    cal_packet_id = packet.unique_packet_id
                    self.calib_pfb.append([np.array(packet.data,complex),None,None,None])
                else:
                    packet.set_meta_id(cal_packet_id)
                    packet.read()
                    ch = packet.channel
                    part = packet.part
                    if (part==0): # real part, comes first
                        self.calib_pfb[-1][packet.channel] = np.array(packet.data, complex)
                    else:
                        self.calib_pfb[-1][packet.channel] += 1j*np.array(packet.data, complex)                    
                    
            if appid_is_cal_debug(appid):
                if appid_is_cal_debug_start(appid):
                    packet.read()
                    cal_packet_id = packet.unique_packet_id
                    self.calib_debug.append([packet]+7*[None])
                else:
                    packet.set_meta_id(cal_packet_id)
                    packet.read()
                    self.calib_debug[-1][packet.debug_page]= packet

            if isinstance(packet, Packet_Heartbeat):
                self.heartbeat_packets.append(packet)

            if isinstance(packet, Packet_Watchdog):
                self.watchdog_packets.append(packet)

            if isinstance(packet, Packet_Housekeep):
                self.housekeeping_packets.append(packet)

            if isinstance(packet, Packet_Waveform):
                self.waveform_packets.append(packet)
                waveforms[packet.ch] = packet
                
            if isinstance(packet, Packet_Waveform_Meta):
                packet.set_packets(waveforms)
                packet.read()
                waveforms=[None,None,None,None]

            self.cont.append(packet)
            self.time.append(os.path.getmtime(fn))
            try:
                dt = self.time[-1] - self.time[0]
                self.desc.append(
                    f"{i:4d} : +{dt:4.1f}s : 0x{appid:0x} : {self.cont[-1].desc}"
                )
            except:
                pass
        pfb = [[],[],[],[]]
        for c in self.calib:
            if (c['pfb'][0] is not None) and (c['pfb'][1] is not None) and (c['pfb'][2] is not None) and (c['pfb'][3] is not None):
                for i in range(4):
                    pfb[i].append(c['pfb'][i])
        if len(pfb[0])>0:
            self.pfb = np.array([np.hstack(p) for p in self.pfb])
        
    
        self.calib_gphase = np.array(self.calib_gphase)
        self.calib_data = np.array(self.calib_data)
        
        if len(self.calib_gNacc)>0:
            self.calib_gNacc = np.hstack(self.calib_gNacc)
        dcalib = [c for c in self.calib_debug if None not in c]
        if self.verbose:
            print ('# of calib debug entries', len(dcalib))
        if len(dcalib)>0:
            self.cd_have_lock = np.hstack([c[0].have_lock for c in dcalib])
            self.cd_lock_ant = np.hstack([c[0].lock_ant for c in dcalib])
            self.cd_errors = [c[0].errors for c in dcalib]
            # phase errors are 8 bits over two counter
            def get_counters(num):
                return [num&0xFF, (num>>8)&0xFF , (num>>16)&0xFF, (num>>24)&0xFF] 

            self.cd_error_phaser = np.array([(get_counters(x.cal_phaser_err[0])+get_counters(x.cal_phaser_err[1])) for x in self.cd_errors])
            self.cd_error_averager = np.array([[get_counters(x.averager_err[r]) for r in range(16)] for x in self.cd_errors])
            self.cd_error_process = np.array([np.hstack([get_counters(x.averager_err[r]) for r in range(8)]) for x in self.cd_errors])
            self.cd_error_stage3 = np.array([np.hstack([get_counters(x.stage3_err[r]) for r in range(4)]) for x in self.cd_errors])
            

            self.cd_drift = np.hstack([c[0].drift for c in dcalib])
            self.cd_powertop0 = np.hstack([c[0].powertop0 for c in dcalib])
            self.cd_powertop1 = np.hstack([c[1].powertop1 for c in dcalib])
            self.cd_powertop2 = np.hstack([c[1].powertop2 for c in dcalib])
            self.cd_powertop3 = np.hstack([c[1].powertop3 for c in dcalib])
            self.cd_powerbot0 = np.hstack([c[2].powerbot0 for c in dcalib])
            self.cd_powerbot1 = np.hstack([c[2].powerbot1 for c in dcalib])
            self.cd_powerbot2 = np.hstack([c[2].powerbot2 for c in dcalib])
            self.cd_powerbot3 = np.hstack([c[3].powerbot3 for c in dcalib])
            self.cd_fd0 = np.hstack([c[3].fd0 for c in dcalib])
            self.cd_fd1 = np.hstack([c[3].fd1 for c in dcalib])
            self.cd_fd2 = np.hstack([c[4].fd2 for c in dcalib])
            self.cd_fd3 = np.hstack([c[4].fd3 for c in dcalib])
            self.cd_sd0 = np.hstack([c[4].sd0 for c in dcalib])
            self.cd_sd1 = np.hstack([c[5].sd1 for c in dcalib])
            self.cd_sd2 = np.hstack([c[5].sd2 for c in dcalib])
            self.cd_sd3 = np.hstack([c[5].sd3 for c in dcalib])
            self.cd_fdx = np.hstack([c[6].fdx for c in dcalib])
            self.cd_sdx = np.hstack([c[6].sdx for c in dcalib])
            self.cd_snr0 = np.hstack([c[6].snr0 for c in dcalib])
            self.cd_snr1 = np.hstack([c[7].snr1 for c in dcalib])
            self.cd_snr2 = np.hstack([c[7].snr2 for c in dcalib])
            self.cd_snr3 = np.hstack([c[7].snr3 for c in dcalib])





        # we don't always send TR spectra; if dict contains only metadata
        # packet but no actual data, we assume it's fine and don't include it into self.tr_spectra
        self.tr_spectra = [trs for trs in tr_spectra if len(trs) > 1]
        assert all(["meta" in trs for trs in tr_spectra])

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

    # return number of waveform packets received
    def num_waveform_packets(self) -> int:
        return len(self.waveform_packets)

    # return 1, if all heartbeat packets are present (no gaps in packet_count sequence)
    def heartbeat_counter_ok(self) -> int:
        hb_counts = [p.packet_count for p in self.heartbeat_packets]
        if len(hb_counts) <= 1:
            return 1
        for i,j in zip(hb_counts[:-1], hb_counts[1:]):
            if j == i+1:
                ## great
                continue
            elif (j<i) or (i==0):
                # then we must have seen a re boot  
                if j==0:
                    continue
            else:
                print(f"Missing heartbeat packet between count {i}-> {j}")
                return 0

        return 1

    # return maximal time difference between heartbeat packets
    # return -1, if there is at 0 or 1 heartbeat
    def heartbeat_max_dt(self) -> int:
        if len(self.heartbeat_packets) <= 1:
            return -1
        hb_times = [p.time for p in self.heartbeat_packets]
        deltas = [t2 - t1 for t2, t1 in zip(hb_times[1:], hb_times[:-1])]
        return max(deltas)

    # return minimal time difference between heartbeat packets
    # return 1e12, if there is 0 or 1 heartbeat
    def heartbeat_min_dt(self) -> int:
        if len(self.heartbeat_packets) <= 1:
            return int(1e12)
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


    def all_meta_error_free(self) -> int:
        result = 1
        for i, sp in enumerate(self.spectra):
            if sp["meta"].errormask:
                print(f"Errors in {i}: {error_mask_pretty_print(sp['meta'].errormask)}")
                result = 0
        return result

    def get_meta(self,name):
        return np.array([S['meta'][name] for S in self.spectra])


    def xxd(self, i, intro=False):
        if intro:
            return self._intro(i) + self.cont[i].xxd()
        return self.cont[i].xxd()
