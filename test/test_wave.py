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



class Test_Wave(Test):

    name = "wave"
    version = 0.1
    description = """ Collects waveform data and checks the waveform statistics."""
    instructions = """ Connect anything you want."""
    default_options = {
        'gain': 'MMMM'
    } ## dictinary of options for the test
    options_help = {
        'gain': 'Gain setting for the test. Default is MMMM.'
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """

        # check if self.gain is a valid gain setting
        gain_ok = True
        if len(self.gain)!=4:
            gain_ok = False
        for v in self.gain:
            if v not in 'LMHA':
                gain_ok = False
        if not gain_ok:
            print (f"Invalid gain setting {self.gain}. Will assume MMMM")
            self.gain = 'MMMM'

        S = Scripter()
        S.reset()

        S.wait(1)

        S.set_ana_gain(self.gain)
        S.wait(0.1)
        S.adc_range()
        S.wait(1)
        #S.waveform(4)
        for i in [0,1,2,3]:
            S.waveform(i)
            S.wait(5)
        S.house_keeping(0)
        S.wait(5)        
        return S

    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)

        self.get_versions(C)

        # extract data

        waveforms = [None,None,None,None]
        hk = None
        num_wf =C.num_waveform_packets()
        num_hk = C.num_housekeeping_packets()
        for wf_packet in C.waveform_packets:
            waveforms[wf_packet.ch] = wf_packet.waveform

        for hk_packet in C.housekeeping_packets:
            if hk_packet.hk_type == 1:
                hk = hk_packet

        if (num_wf !=4 ) or num_hk < 1:
            print ("ERROR: Missing waveforms or housekeeping packets.")
            passed = False

        self.results['num_wf'] = num_wf
        self.results['num_hk'] = num_hk
        self.results['num_wf_ok'] = int(num_wf == 4)
        self.results['num_hk_ok'] = int(num_hk == 1)

        for ch in range(4):
            fig = plt.figure(figsize=(12, 6))
            gs = fig.add_gridspec(1, 3)
            ax1 = fig.add_subplot(gs[0,:2])
            ax2 = fig.add_subplot(gs[0,2])
            ax1.plot(waveforms[ch])
            ax1.set_title(f"Waveform {ch+1}")
            ax2.hist(waveforms[ch], bins=100)
            ax2.axvline(hk.min[ch], color='r', ls='-',lw=2)
            ax2.axvline(hk.max[ch], color='r', ls='-',lw=2)
            ax2.axvline(hk.mean[ch], color='b', ls='-',lw=2)
            ax2.axvline(hk.mean[ch]+hk.rms[ch], color='y', ls='-',lw=2)
            ax2.axvline(hk.mean[ch]-hk.rms[ch], color='y', ls='-',lw=2)
            ax2.set_title(f"Waveform {ch+1} Histogram")
            fig.savefig(os.path.join(figures_dir,f'wave_{ch+1}.pdf'))

        self.results['min'] = " ".join(f"{x:5}" for x in hk['min'])
        self.results['max'] = " ".join(f"{x:5}" for x in hk['max'])
        self.results['mean'] = " ".join(f"{x:4.1f}" for x in hk['mean'])
        self.results['rms'] = " ".join(f"{x:4.1f}" for x in hk['rms'])
        self.results['valid_count'] = " ".join(f"{x:5}" for x in hk['valid_count'])
        self.results['invalid_count_max'] = " ".join(f"{x:5}" for x in hk['invalid_count_max'])
        self.results['invalid_count_min'] = " ".join(f"{x:5}" for x in hk['invalid_count_min'])
        self.results['total_count'] = " ".join(f"{x:5}" for x in hk['total_count'])
        self.results['actual_gain'] = " ".join(hk['actual_gain'])

        self.results['result'] = int(passed)
