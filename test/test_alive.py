
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



class Test_Alive(Test):
    
    name = "alive"
    version = 0.1
    description = """ Basic aliveness test of communication and spectral engine."""
    instructions = """ Do not need to connect anything."""
    default_options = {
        "time" : 60
    } ## dictinary of options for the test
    options_help = {
        "time" : "Total time to run the test. 1/3 will be spent taking spectra. Need to be larger than 15s."
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """
        if self.time<15:
            print ("Time raised to 15 seconds.")
            self.time = 15
            
        S = Scripter()
        S.reset()
        S.wait(1)
        S.ADC_ramp(True)
        S.house_keeping(0)
        S.wait(1)
        for i in range(4):
            S.waveform(i)
            S.wait(1)
        S.set_Navg(14,3)
        #S.start()
        S.wait(self.time-S.total_time-1)
        #S.stop()
        S.house_keeping(0)
        S.wait(1)
        return S
    
    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test. 
            Returns true if test has passed.
        """
        self.results = {}
        passed = True
        
        self.results['packets_received'] = len(C.cont)
        
        C.cut_to_hello()
    
        if type(C.cont[0]) == uc.Packet_Hello:
            H = C.cont[0]
            H._read()
            self.results['hello'] = 1
            def h2v(h):
                v = f"{h:#0{6}x}"
                v = v[2:4]+'.'+v[4:6]
                return v
            def h2d(h):
                v = f"{h:#0{10}x}"
                v = v[6:8]+'/'+v[8:10]+'/'+v[2:6]

                return v
            def h2t(h):
                v = f"{h:#0{10}x}"
                v = v[4:6]+':'+v[6:8]+'.'+v[8:10]
                return v
            
                
            self.results['SW_version'] = h2v(H.SW_version)
            self.results['FW_version'] = h2v(H.FW_Version)
            self.results['FW_ID'] = f"0x{H.FW_ID:#0{4}}"
            self.results['FW_Date'] = h2d(C.cont[0].FW_Date)
            self.results['FW_Time'] = h2t(C.cont[0].FW_Time)
        else:
            self.results['hello'] = 0
            self.results['SW_version'] = "N/A"
            self.results['FW_version'] = "N/A"
            self.results['FW_ID'] = "N/A"
            self.results['FW_Date'] = "N/A"
            self.results['FW_Time'] = "N/A"

        num_hb, num_wf, num_sp = 0,0,0
        last_hb = None
        heartbeat_spacing = True
        fig_wf, ax_wf= plt.subplots(1,1,figsize=(12,8))
        wf_ch=[False]*4
        wf_ch_ok = [False]*4
        for P in C.cont:
            if type(P) == uc.Packet_Heartbeat:
                P._read()
                num_hb += 1
                if last_hb is None:
                    last_hb = P.count
                else:
                    if P.count != last_hb+1 or P.ok == False:
                        self.results['result'] = 'FAILED'
                        heartbeat_spacing = False
                        passed=False
            if type(P) == uc.Packet_Waveform:
                num_wf += 1
                P._read()
                ax_wf.plot(P.waveform, label=f"Channel {P.ch}")
                wf_ch[P.ch] = True
                wf_ch_ok[P.ch] = True ### FIXME: need to check the waveform
            if type(P) == uc.Packet_Spectrum:
                num_sp += 1
        if num_hb == 0:
            heartbeat_spacing = False
        
        self.results['heartbeat_received'] = num_hb
        self.results['heartbeat_spacing'] = num_hb
        self.results['wf_packets_received'] = num_wf
        self.results['sp_packets_received'] = num_sp

        
        ax_wf.set_ylabel("ADC Value")
        ax_wf.set_xlabel("Sample")
        ax_wf.legend()
        fig_wf.savefig(os.path.join(figures_dir,'waveforms.pdf'))
        fig_wf.tight_layout()
        for i in range(4):
            self.results[f'wf_ch{i+1}'] = int(wf_ch[i])
            self.results[f'wf_ch{i+1}_ok'] = int(wf_ch[i])

        self.results['result'] = int(passed)




