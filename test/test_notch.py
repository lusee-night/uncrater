import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import matplotlib.pyplot as plt
import os


import argparse
import numpy as np
from test_base import Test
from test_base import pycoreloop as cl
from  lusee_script import Scripter
import uncrater as uc
from collections import defaultdict


class Test_Notch(Test):

    name = "notch"
    version = 0.1
    description = """ Test the notch functionality (to debug notch in xcorr)  """
    instructions = """ Does not matter what you connect. """
    default_options = { 
        "slow": False
    } ## dictinary of options for the test
    options_help = {
        "slow" : "Enable for running at SSL"
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """

        S = Scripter()

        S.reset()
        S.seq_begin()
        
        if self.slow:
            S.set_dispatch_delay(120)

        S.set_bitslice('all',22)
        S.ADC_special_mode('ramp')

        S.start()
        S.cdi_wait_spectra(1)
        S.stop()

        
        S.cdi_wait_seconds(10)
        S.set_notch(4)
        S.start()
        S.cdi_wait_spectra(1)
        S.stop()

        S.request_eos()
        S.seq_end()
        S.wait_eos()
        return S



    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        fig_sp, ax_sp = plt.subplots(4,4,figsize=(12,12))
        Nstart = 2
        Nend = 100
        for i,S in enumerate(C.spectra):
            freq=np.arange(Nstart,Nend)*0.025
            for c in range(16):
                x,y = c//4, c%4
                data = S[c].data[Nstart:Nend]*freq**2
                #if c<4:
                #    ax_sp[x][y].set_xscale('log')
                #    ax_sp[x][y].set_yscale('log')

                ax_sp[x][y].plot(freq, data, label=f'{i}')

        ax_sp[0][0].set_title('Spectra Analysis')
        
        ax_sp[0][0].legend()
        
        for i in range(4):
            ax_sp[3][i].set_xlabel('frequency [MHz]')
            ax_sp[i][0].set_ylabel('power [uncalibrated]')

        fig_sp.tight_layout()
        if not (figures_dir is None):
            fig_sp.savefig(os.path.join(figures_dir,'spectra.pdf'))

        passed = True
        self.results['result'] = int(passed)
