import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import matplotlib.pyplot as plt
import os


import argparse
import numpy as np
from test_base import Test
from  lusee_script import Scripter
import uncrater as uc
from collections import defaultdict


class Test_Science(Test):
    
    name = "science"
    version = 0.1
    description = """ Runs the spectrometer in close to the real science mode"""
    instructions = """ Connect anything you want."""
    default_options = {
        "preset": "simple",
        "time_mins" : 0
    } ## dictinary of options for the test
    options_help = {
        "preset" : "Type of science preset. Currently only 'simple' is supported (direct mapping of ADC to channels with automatic gains).",
        "time_mins" : "Total time to run the test in minutes (up to 100), zero for forever."
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """
        if self.preset not in ['simple']:
            print ("Unknown preset. Using 'simple'")
            self.preset = 'simple'
        if self.time_mins>100:
            print ("Use <100 mins or forever (0). Assuming 100.")
            self.time_mins = 100


        S = Scripter()
        S.reset()
        
        S.wait(1)
        S.set_Navg(14,6)
        for ch in range(4):
            S.set_route (ch,ch,None)
        S.set_bitslice_auto(8)
        S.set_ana_gain('AAAA')
        S.start()

        if self.time_mins>0:
            S.wait(self.time_mins*600)
        else:
            S.wait(-1)
        return S
    
    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test. 
            Returns true if test has passed.
        """
        self.results = {}
        passed = True
        
        self.results['packets_received'] = len(C.cont)
        
        C.cut_to_hello()
    
        if len(C)>0 and type(C.cont[0]) == uc.Packet_Hello:
            H = C.cont[0]
            H._read()
            self.results['hello'] = 1
            def h2v(h):
                v = f"{h:#0{6}x}"
                v = v[2:4]+'.'+v[4:6]
                return v
            def h2vs(h):
                v = f"{h:#0{10}x}"
                v = v[4:6]+'.'+v[6:8]+' r'+v[8:10]
                return v

            def h2d(h):
                v = f"{h:#0{10}x}"
                v = v[6:8]+'/'+v[8:10]+'/'+v[2:6]

                return v
            def h2t(h):
                v = f"{h:#0{10}x}"
                v = v[4:6]+':'+v[6:8]+'.'+v[8:10]
                return v
            
                
            self.results['SW_version'] = h2vs(H.SW_version)
            self.results['FW_version'] = h2v(H.FW_Version)
            self.results['FW_ID'] = f"0x{H.FW_ID:#0{4}}"
            self.results['FW_Date'] = h2d(C.cont[0].FW_Date)
            self.results['FW_Time'] = h2t(C.cont[0].FW_Time)
            if H.SW_version != self.coreloop_version():
                print ("WARNING!!! SW version in pycoreloop ({self.coreloop_version():x}) does not match SW version in coreloop ({H.SW_version:x})")                
        else:
            self.results['hello'] = 0
            self.results['SW_version'] = "N/A"
            self.results['FW_version'] = "N/A"
            self.results['FW_ID'] = "N/A"
            self.results['FW_Date'] = "N/A"
            self.results['FW_Time'] = "N/A"

        num_hb, num_sp = 0,0
        last_hb = None
        heartbeat_counter_ok = True
        sp_crc_ok = True
        hk_start = None
        hk_end = None
        hk_end = None
        last_hbtime = None
        hb_tmin = 0
        hb_tmax = 0
        for P in C.cont:
            if type(P) == uc.Packet_Heartbeat:
                P._read()
                num_hb += 1
                if last_hb is None:
                    last_hb = P.packet_count
                    last_hbtime = P.time
                    hb_tmin = 1e9
                else:
                    if P.packet_count != last_hb+1 or P.ok == False:
                        self.results['result'] = 'FAILED'
                        heartbeat_counter_ok = False
                        passed=False
                    else:
                        last_hb = P.packet_count
                    dt = P.time - last_hbtime
                    last_hbtime = P.time
                    hb_tmin = min(hb_tmin, dt)
                    hb_tmax = max(hb_tmax, dt)

            if type(P) == uc.Packet_Spectrum:
                num_sp += 1
                P._read()
                sp_crc_ok = (sp_crc_ok & (not P.error_crc_mismatch))

        if num_hb == 0:
            heartbeat_counter_ok = False
        
        self.results['heartbeat_received'] = num_hb
        self.results['hearbeat_count'] = int(num_hb)
        self.results['heartbeat_not_missing'] = int(heartbeat_counter_ok & (hb_tmax<11))
        self.results['heartbeat_mindt'] = f"{hb_tmin:.3f}"
        self.results['heartbeat_maxdt'] = f"{hb_tmax:.3f}"



        ## now plot spectra
        fig_sp, ax_sp = plt.subplots(4,4,figsize=(12,12))
        fig_sp2, ax_sp2 = plt.subplots(4,4,figsize=(12,12))
        freq = np.arange(1,2048)*0.025
        wfall=[[] for i in range(16)]
        
        
        crc_ok = True
        sp_all = True
        sp_rejections = 0

        mean, std = np.load ('test/data/ramp_power.npy')
        for i,S in enumerate(C.spectra):
            sp_rejections += 64-S['meta'].base.weight_previous
    
                
            for c in range(16):
                if c not in S:
                    sp_all = False
                    print (f"Product {c} missing in spectra{i}.")
                    continue
                if S[c].error_crc_mismatch:
                    print (f"BAD CRC in product {c}, spectral packet {i}!!")
                    # add zeros to wfall
                    nz = 2047 if c<4 else 400
                    wfall[c].append(np.zeros(nz))
                    crc_ok = False
                x,y = c//4, c%4
                
                if c<4:
                    data = S[c].data[1:]
                    w= np.where(std>100)
                    err = (np.abs(data-mean)[w]/std[w])
                    maxerr = np.max(err)
                    if not (maxerr<5):
                        pk_ok = False
                    
                    ax_sp[x][y].plot(freq, data, label=f"{i}")
                    wfall[c].append(data)
                    ax_sp[x][y].set_xscale('log')
                    ax_sp[x][y].set_yscale('log')
                else:
                    data= S[c].data[:400]*freq[:400]**2
                    ax_sp[x][y].plot(freq[:400], data)
                    wfall[c].append(data)
                #ax_sp[x][y].legend()
        for i in range(4):
            ax_sp[3][i].set_xlabel('frequency [MHz]')
            ax_sp[i][0].set_ylabel('power [uncalibrated]')

        if len(C.spectra)>0:
            self.results['sp_crc'] = int(crc_ok)
            self.results['sp_all'] = int(sp_all)
            self.results['sp_pk_ok'] = int(pk_ok)
            self.results['sp_num'] = len(C.spectra)
            self.results['sp_rejections'] = sp_rejections
        else:
            self.results['sp_crc'] = 0
            self.results['sp_all'] = 0
            self.results['sp_pk_ok'] = 0
            self.results['sp_num'] = 0
            self.results['sp_weights_ok'] = 0

        passed = (passed and crc_ok and sp_all and pk_ok and pk_weights_ok)

        fig_sp.tight_layout()
        fig_sp.savefig(os.path.join(figures_dir,'spectra.pdf'))
        for c in range(16):
            x,y = c//4, c%4
            data = np.array(wfall[c])
            if c<4:
                data=np.log10(data+1)
            if len(data)==0:
                data=[[0]]
            ax_sp2[x][y].imshow(data, origin='upper',aspect='auto', interpolation='nearest')

        fig_sp2.tight_layout()
        fig_sp2.savefig(os.path.join(figures_dir,'spectra_wf.pdf'))
        self.results['result'] = int(passed)




