import sys
import pickle
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os


import argparse
import numpy as np
from test_base import Test
from  lusee_script import Scripter
import uncrater as uc
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.interpolate import interp1d



class Test_Power(Test):

    name = "power"
    version = 0.1
    description = """ Puts the system in the mode that should maximize power consumption"""
    instructions = """ Connect AWG."""
    default_options = {
        'gains': 'HHHH',
        'bitslice': 16,
        'amplitude': 75,        
        'slow': False,
        'time_mins': 30, 
    } ## dictinary of options for the test
    options_help = {
        'gains' : 'List of gains used in the test.',
        'bitslice': 'Bitslice used in the test. ',
        'amplitude': 'Amplitude used in the test. ',
        'slow': 'Enable very slow operation: large interpacket distance and minimize the number of total packets by limiting to what we really need',
        'time_mins': 'Time in minutes to run the test',
    } ## dictionary of help for the options
    

    def generate_script(self):
        """ Generates a script for the test """

        # check if self.gain is a valid gain setting


        S = Scripter()
        S.awg_init()

        S.reset()
        S.wait(3)
        if (self.slow):
            S.set_cdi_delay(10)
        else:
            S.set_cdi_delay(2)
            S.set_dispatch_delay(6)
        
        for ch in range(4):
            S.awg_tone(ch, 10+11*ch, self.amplitude)
            S.set_bitslice(ch, self.bitslice)

        S.set_Navg(14,6)
        S.set_ana_gain(self.gains)
        S.start(no_flash=True)
        S.cdi_wait_minutes(self.time_mins)
        S.stop(no_flash=True)
        
        # request housekeeping to force the buffer to empty
        S.house_keeping(0)
        S.request_eos()
        S.wait_eos()
        S.awg_close()
        return S

    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True


        self.results['packets_received'] = len(C.cont)

        C.cut_to_hello()
        self.get_versions(C)

        def get_meta(name, C):
            return np.array([S['meta'][name] for S in C.spectra])

        adc_min = get_meta("adc_min",C).min(axis=0)
        adc_max = get_meta("adc_max",C).max(axis=0)

        self.results['adc_min'] = " ".join([f"{x:.2f}" for x in adc_min])
        self.results['adc_max'] = " ".join([f"{x:.2f}" for x in adc_max])
        print ("ADC MIN:", adc_min)
        print ("ADC MAX:", adc_max)

        # plot mean spectra
        fig, ax = plt.subplots(2,2,figsize=(12, 8))
        ax = ax.flatten()
        for ch in range(4):
            data = np.array([S[ch].data for S in C.spectra])
            data = data.mean(axis=0)
            freq = C.spectra[0]['meta'].frequency
            ax[ch].plot(freq, data)
            ax[ch].set_xlabel('Frequency [MHz]')
            ax[ch].set_ylabel('Power')
            ax[ch].set_title(f'Channel {ch}')

        fig.savefig(os.path.join(figures_dir, 'spectra.pdf'))

        self.results['result'] = 1
