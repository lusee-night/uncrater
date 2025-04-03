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


class Test_Reject(Test):

    name = "reject"
    version = 0.1
    description = """ Test the rejection algorithm  """
    instructions = """ Connect either the VW calibrator or the awg"""
    default_options = { 
        "mode": "none",
        "reject_frac": 10,
        "max_bad": 30,
        "slow": False
    } ## dictinary of options for the test
    options_help = {
        "mode" : "What GSE to use: cal or awg",
        "reject_frac": "Number to divide the power with to get maximum deviation per bin",
        "max_bad": "Maximum number of bad bins to still accept a sample",
        "slow" : "Enable for running at SSL"
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """

        S = Scripter()

        if (self.mode not in ["cal", "awg","none"]):
            raise ValueError("mode must be cal or awg or none")

        use_cal = self.mode=="cal"
            
        if use_cal:
            S.awg_cal_on(17)

        S.reset()

        if self.slow:
            S.set_dispatch_delay(120)
    
        S.set_Navg(14,4)

        ### Main spectral engine
        for i in range(4):        
            S.set_route(i, None, i)
        S.set_ana_gain('HHHH')
        S.set_bitslice(0,10)
        S.select_products(0b1111)
        for i in range(1,4):
            S.set_bitslice(i,19)   
        S.reject_enable(reject_frac=self.reject_frac, max_bad = self.max_bad) 
        

        S.start()
        S.cdi_wait_spectra(10)
        S.stop()
        S.request_eos()

        ## We are taking 10 spectra of 10.24 seconds each. 
        S.wait(24)
        ## reject one
        if use_cal: S.awg_cal_off()
        S.wait(1)
        if use_cal: S.awg_cal_on(17)
        # wait and then change baseline
        S.wait(30)        
        if use_cal: S.awg_cal_off()
                
        S.wait_eos()
        return S



    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)
        self.get_versions(C)


        self.results['result'] = int(passed)

        weights = C.get_meta("base.weight_previous")
        print (weights)
        
        time = C.get_meta("time")
        time = (time - time[0])/60

        fig,ax = plt.subplots()
        ax.plot(time, weights)
        ax.set_xlabel('time [mins]')
        ax.set_ylabel('weights')
        fig.savefig(os.path.join(figures_dir,'weights.pdf'))

        fig, ax = plt.subplots(2,2, figsize=(12,12))
        ax = ax.flatten()
        freq = C.spectra[0]['meta'].frequency
        freq = freq.reshape((-1,8)).mean(axis=1)
        for ch in range(4):
            for j, S in enumerate(C.spectra):
                print (S['meta'].base.weight_previous)
                data = S[ch].data
                data = data.reshape((-1,8)).mean(axis=1)
                ax[ch].plot(freq, data, label=str(j))
            ax[ch].set_title(f'Channel {ch}')
            ax[ch].legend()
            ax[ch].set_yscale('log')

        fig.savefig(os.path.join(figures_dir,'spectra.pdf'))
