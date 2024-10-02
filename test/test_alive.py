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


def test_waveform(wf, type):
    if type == 'ramp':
        pred_val = wf[0]
        for next_val in wf[1:]:
            pred_val = pred_val+1 if pred_val<8192 else -8191
            if next_val != pred_val:        
                return False
        return True
    if type == 'zeros':
        return np.all(wf==0)
    if type == 'ones':
        return np.all(wf==8192)
    if type == 'input':
        return True # input is true since we don't know what to expect


class HKAnalyzer:
    def __init__(self, start: uc.Packet_Housekeep, end: uc.Packet_Housekeep):
        self.start = start
        self.end = end
        self.attr_dict: defaultdict[str: list[int | bool, int | bool]] = defaultdict(list)

        self.template = \
            '''
            \\begin{longtable}{p{7.5cm}p{3cm}p{3cm}}
            \\textbf{Field Name} & \\textbf{Start} & \\textbf{End} \\\\
            \\hline \\\\
            '''

    def _analyze_attr(self, attr_name: str, obj: object, full_attr_name: str) -> None:
        attr = getattr(obj, attr_name)
        full_attr_name += f'{attr_name}.'
        if isinstance(attr, object) and type(attr).__module__ != 'builtins':
            self._analyze_hk(attr, full_attr_name)
        else:
            self.attr_dict[full_attr_name.strip('.')].append(attr)

    def _analyze_hk(self, obj: object, full_attr_name='') -> None:
        # slotted classes generated in core_loop.py
        if hasattr(obj, '__slots__'):
            for slot in obj.__slots__:
                if slot[0] == '_':
                    continue
                self._analyze_attr(slot, obj, full_attr_name)
        # top level Packet class
        elif obj.__class__.__module__ != 'builtins':
            for attr_name in vars(obj):
                if attr_name[0] == '_':
                    continue
                self._analyze_attr(attr_name, obj, full_attr_name)

    def get_latex(self):
        self._analyze_hk(self.start)
        self._analyze_hk(self.end)
        for k, (v_start, v_end) in self.attr_dict.items():
            k = k.replace('_', '{\\_}')
            k = f'\\texttt{{{k}}}'
            if isinstance(v_start, bool):
                v_start = '\\checkmark' if v_start else 'X'
                v_end = '\\checkmark' if v_end else 'X'
                self.template += f"{k} & {v_start} & {v_end} \\\\"
            elif isinstance(v_start, int):
                self.template += f"{k} & 0x{v_start:X} & 0x{v_end:X} \\\\"
            else:
                self.template += f"{k} & {v_start} & {v_end} \\\\"
        self.template += '\\end{longtable}'
        return self.template


class Test_Alive(Test):
    
    name = "alive"
    version = 0.1
    description = """ Basic aliveness test of communication and spectral engine."""
    instructions = """ Do not need to connect anything."""
    default_options = {
        "waveform_type": "ramp",
        "time" : 60
    } ## dictinary of options for the test
    options_help = {
        "waveform_type" : "Waveform to be generated. Can be 'ramp', 'zeros', 'ones', or 'input'",
        "time" : "Total time to run the test. 1/3 will be spent taking spectra. Need to be larger than 15s."
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """
        if self.time<15:
            print ("Time raised to 15 seconds.")
            self.time = 15
        if self.waveform_type == 'input':
            self.waveform_type = 'normal'
        if self.waveform_type not in ['ramp','zeros','ones','input']:
            print ("Unknown waveform type. ")
            sys.exit(1)

        S = Scripter()
        S.reset()
        ## this is the real wait
        S.wait(1)
        S.house_keeping(0)
        S.ADC_special_mode(self.waveform_type)
        S.cdi_wait_ticks(20)
        for i in [0,1,2,3]:
            S.waveform(i)
            S.cdi_wait_ticks(10)
        #S.waveform(5)
        S.set_Navg(14,3)
        S.start()
        S.cdi_wait_seconds(self.time-S.total_time-3)
        S.stop()
        S.cdi_wait_seconds(2)
        S.house_keeping(0)
        S.ADC_special_mode('normal')
        S.wait(self.time+7)
        return S
    
    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test. 
            Returns true if test has passed.
        """
        self.results = {}
        passed = True
        
        self.results['packets_received'] = len(C.cont)
        
        C.cut_to_hello()
        self.get_versions(C)

        num_hb, num_wf, num_sp, num_hk = 0,0,0,0
        last_hb = None
        heartbeat_counter_ok = True
        fig_wf, ax_wf= plt.subplots(1,1,figsize=(12,8))
        wf_ch=[False]*4
        wf_ch_ok = [False]*4
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

            if type(P) == uc.Packet_Waveform:
                num_wf += 1
                P._read()
                ax_wf.plot(P.waveform, label=f"Channel {P.ch+1}")
                wf_ch[P.ch] = True
                wf_ch_ok[P.ch] = test_waveform(P.waveform, self.waveform_type)
            if type(P) == uc.Packet_Spectrum:
                num_sp += 1
                P._read()
                sp_crc_ok = (sp_crc_ok & (not P.error_crc_mismatch))
            if type(P) == uc.Packet_Housekeep:
                num_hk += 1
                P._read()
                if hk_start is None:
                    hk_start = P
                else:
                    hk_end = P
        if num_hb == 0:
            heartbeat_counter_ok = False
        
        self.results['heartbeat_received'] = num_hb
        self.results['hearbeat_count'] = int(num_hb)
        self.results['heartbeat_not_missing'] = int(heartbeat_counter_ok & (hb_tmax<11))
        self.results['heartbeat_mindt'] = f"{hb_tmin:.3f}"
        self.results['heartbeat_maxdt'] = f"{hb_tmax:.3f}"
        self.results['wf_packets_received'] = num_wf
        self.results['sp_packets_received'] = num_sp
        self.results['hk_packets_received'] = num_hk
        self.results['wf_right'] = int(num_wf==4)
        self.results['hk_right'] = int(num_hk==2)
        if num_hk == 2:
            self.results['hk_results'] = HKAnalyzer(hk_start, hk_end).get_latex()

        if (hk_start is not None) and (hk_end is not None):
            delta_t = hk_end.time - hk_start.time
            self.results['timer_ok'] = int ((delta_t>55) and (delta_t<65))
            self.results['no_errors'] =  int(hk_start.core_state.base.errors == 0 and hk_end.core_state.base.errors == 0)
        else:
            self.results['timer_ok'] = 0
            self.results['no_errors'] = 0

        if num_wf<4:
            passed = False
        if num_sp<1:
            passed = False
        if num_hk<2:
            passed = False

        ax_wf.set_ylabel("ADC Value")
        ax_wf.set_xlabel("Sample")
        ax_wf.legend()
        fig_wf.savefig(os.path.join(figures_dir,'waveforms.pdf'))
        fig_wf.tight_layout()
        for i in range(4):
            self.results[f'wf_ch{i+1}'] = int(wf_ch[i])
            self.results[f'wf_ch{i+1}_ok'] = int(wf_ch_ok[i])


        ## now plot spectra
        fig_sp, ax_sp = plt.subplots(4,4,figsize=(12,12))
        fig_sp2, ax_sp2 = plt.subplots(4,4,figsize=(12,12))
        freq = np.arange(1,2048)*0.025
        wfall=[[] for i in range(16)]
        
        
        crc_ok = True
        sp_all = True
        pk_ok = True
        pk_weights_ok = True

        mean, std = np.load ('test/data/ramp_power.npy')
        for i,S in enumerate(C.spectra):
            if S['meta'].base.weight_previous!=8:
                pk_weights_ok = False
                
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
            self.results['sp_weights_ok'] = int(pk_weights_ok)
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




