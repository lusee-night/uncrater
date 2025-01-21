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
        for sign in [+1, -1]:
            pred_val = wf[0]
            ok = True
            for next_val in wf[1:]:
                if sign>0:
                    pred_val = pred_val+1 if pred_val<8192 else -8191    
                else:
                    pred_val = pred_val-1 if pred_val>-8191 else 8192    
                if (next_val != pred_val):                    
                    ok = False
                    break
            if ok:
                return True
        return False

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
            if "__dict__" in dir(obj):
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
    version = 0.2
    description = """ Basic aliveness test of communication and spectral engine."""
    instructions = """ Do not need to connect anything."""
    default_options = {
        "waveform_type": "ramp",
        "cdi_delay": 1,
        "slow": False,
    } ## dictinary of options for the test
    options_help = {
        "waveform_type" : "Waveform to be generated. Can be 'ramp', 'zeros', 'ones', or 'input'",
        "cdi_delay": "Delay in units of 1.26ms for the CDI to space packets by (0=225ns)",
        "slow": "Snail mode for SSL"
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """
        if self.waveform_type == 'input':
            self.waveform_type = 'normal'
        if self.waveform_type not in ['ramp','zeros','ones','input']:
            print ("Unknown waveform type. ")
            sys.exit(1)


        S = Scripter()
        S.reset()
        ## this is the real wait
        S.wait(3)

        S.set_cdi_delay(int(self.cdi_delay))
        S.set_dispatch_delay(150 if self.slow else 6)
        S.house_keeping(0)
        S.ADC_special_mode(self.waveform_type)
        S.waveform(4)
                
        S.set_Navg(14,6 if self.slow else 3)
        S.start()        
        S.cdi_wait_spectra(4 if self.slow else 9)
        S.stop()
        
        S.house_keeping(0)
        S.ADC_special_mode('normal')
        S.request_eos()
        S.wait_eos()
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

        fig_wf, ax_wf= plt.subplots(1,1,figsize=(12,8))
        wf_ch=[False]*4
        wf_ch_ok = [False]*4

        for P in C.waveform_packets:
            ax_wf.plot(P.waveform, label=f"Channel {P.ch+1}")
            wf_ch[P.ch] = True
            wf_ch_ok[P.ch] = test_waveform(P.waveform, self.waveform_type)

        num_hb = C.num_heartbeats()
        num_sp = C.num_spectra_packets()
        num_wf = C.num_waveform_packets()
        num_hk = C.num_housekeeping_packets()
        hb_tmin = C.heartbeat_min_dt()
        hb_tmax = C.heartbeat_max_dt()
        hk_start = C.housekeeping_packets[0] if num_hk > 0 else None
        hk_end = C.housekeeping_packets[-1] if num_hk > 1 else None
        heartbeat_counter_ok = C.heartbeat_counter_ok()

        self.results['heartbeat_received'] = num_hb
        self.results['hearbeat_count'] = int(num_hb)
        self.results['heartbeat_not_missing'] = int(heartbeat_counter_ok)
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
            self.results['timer_ok'] = int ((delta_t>0)& (delta_t<10000)) ## let's be generous here
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
        if not (figures_dir is None):
            fig_wf.savefig(os.path.join(figures_dir,'waveforms.pdf'))
        fig_wf.tight_layout()
        for i in range(4):
            self.results[f'wf_ch{i+1}'] = int(wf_ch[i])
            self.results[f'wf_ch{i+1}_ok'] = int(wf_ch_ok[i])


        ## now plot spectra
        fig_sp, ax_sp = plt.subplots(4,4,figsize=(12,12))
        fig_sp2, ax_sp2 = plt.subplots(4,4,figsize=(12,12))
        freq = np.arange(1,2048)*0.025
        wfall=[[] for _ in range(16)]

        crc_ok = C.all_spectra_crc_ok()
        sp_all = C.has_all_products()

        pk_ok = True
        pk_weights_ok = True
        if int(self.results["FW_ID"][2:],16)>=0x22a:
            fname = "ramp_power_newwin.npy"
        else:
            fname = "ramp_power.npy"
        mean, std = np.load ('test/data/'+fname)
        #hack = []
        for i,S in enumerate(C.spectra):
            if S['meta'].base.weight_previous!=(64 if self.slow else 8):
                pk_weights_ok = False

            for c in range(16):
                if c in S and S[c].error_crc_mismatch:
                    print (f"BAD CRC in product {c}, spectral packet {i}!!")
                    # add zeros to wfall
                    nz = 2047 if c<4 else 400
                    wfall[c].append(np.zeros(nz))
                x,y = c//4, c%4

                if c<4:
                    data = S[c].data[1:]
                    #hack.append(data)
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
        #np.save('test/data/ramp_power_newwin', (np.mean(hack,axis=0),np.std(hack,axis=0)))
        for i in range(4):
            ax_sp[3][i].set_xlabel('frequency [MHz]')
            ax_sp[i][0].set_ylabel('power [uncalibrated]')

        if len(C.spectra)>0:
            self.results['sp_crc'] = int(crc_ok)
            self.results['sp_all'] = int(sp_all)
            self.results['sp_pk_ok'] = int(pk_ok)
            self.results['sp_num'] = len(C.spectra)
            self.results['sp_weights_ok'] = int(pk_weights_ok)
            self.results["meta_error_free"] = C.all_meta_error_free()
        else:
            self.results['sp_crc'] = 0
            self.results['sp_all'] = 0
            self.results['sp_pk_ok'] = 0
            self.results['sp_num'] = 0
            self.results['sp_weights_ok'] = 0
            self.results["meta_error_free"] = 0

        time, V1_0, V1_8, V2_5, T_FPGA = self.plot_telemetry(C.spectra, figures_dir)
        self.results['v1_0_min'] = f"{V1_0.min():3.2f}"
        self.results['v1_0_max'] = f"{V1_0.max():3.2f}"
        self.results['v1_8_min'] = f"{V1_8.min():3.2f}"
        self.results['v1_8_max'] = f"{V1_8.max():3.2f}"
        self.results['v2_5_min'] = f"{V2_5.min():3.2f}"
        self.results['v2_5_max'] = f"{V2_5.max():3.2f}"
        self.results['t_fpga_min'] = f"{T_FPGA.min():3.2f}"
        self.results['t_fpga_max'] = f"{T_FPGA.max():3.2f}"


        v_1_0_ok = (V1_0.min()>0.95) and (V1_0.max()<1.2)
        v_1_8_ok = (V1_8.min()>1.75) and (V1_8.max()<2.0)
        v_2_5_ok = (V2_5.min()>2.45) and (V2_5.max()<2.7)
        t_fpga_ok = (T_FPGA.min()>-10) and (T_FPGA.max()<80)


        self.results['v_1_0_ok'] = int(v_1_0_ok)
        self.results['v_1_8_ok'] = int(v_1_0_ok)
        self.results['v_2_5_ok'] = int(v_2_5_ok)
        self.results['t_fpga_ok'] = int(t_fpga_ok)

        passed = (passed and crc_ok and sp_all and pk_ok and pk_weights_ok and v_1_0_ok and v_1_8_ok and v_2_5_ok and t_fpga_ok and wf_ch_ok[0] and wf_ch_ok[1] and wf_ch_ok[2] and wf_ch_ok[3])
        passed = passed and self.results["meta_error_free"] and self.results['no_errors'] 

        fig_sp.tight_layout()
        if not (figures_dir is None):
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
        if not (figures_dir is None):
            fig_sp2.savefig(os.path.join(figures_dir,'spectra_wf.pdf'))
        self.results['result'] = int(passed)
