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


class Test_Calib_Weights(Test):

    name = "calib_weights"
    version = 0.1
    description = """ Runs the WV calibrator EM with power on and off to determin the optimal weights """
    instructions = """ Connect the VW calibrator.  """
    default_options = {         
        'Ngo' : 10,
        'slow': False,
    } ## dictinary of options for the test
    options_help = {
        'Ngo': 'Number of repetitions',
        'slow': 'Run the test in slow mode',
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """


        S = Scripter()
            
        S.wait(1)
        S.reset()
        S.wait(3)

        if self.slow:
            S.set_dispatch_delay(120)
    
        S.enable_heartbeat(False)
        S.set_Navg(14,5)
        
        for i in range(4):
            S.set_route (i,None,i)
        
        S.select_products(0b1111)
        S.set_ana_gain('MMMM')
        
        S.set_bitslice(0,10)
        for i in range(1,4):
            S.set_bitslice(i,15)    
        
        fstart = 17.0
        fend = +17.0




        S.set_notch(0)
        for onoff in range(self.Ngo):
            S.awg_cal_off()
            S.wait(1)
            S.start()
            S.cdi_wait_spectra(2)
            S.stop()
            S.request_eos()
            S.wait_eos()
            
            S.awg_cal_on(fstart)
            S.wait(1)
            S.start()
            S.cdi_wait_spectra(2)
            S.stop()
            S.request_eos()
            S.wait_eos()

        
        return S



    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        C.cut_to_hello()
        self.results['packets_received'] = len(C.cont)
        self.get_versions(C)

        N = len(C.spectra)//4
        
        onndx = np.array([[4*i, 4*i+1] for i in range(N)]).flatten()
        offndx = np.array([[4*i+2, 4*i+3] for i in range(N)]).flatten()
        spectra_off = [C.spectra[i] for i in onndx]
        spectra_on = [C.spectra[i] for i in offndx]


        offpow = []
        onpow = []
        fig, ax = plt.subplots(2,2)
        ax = ax.flatten()
        for ch in range(4):
            off = np.array([off[ch].data for off in spectra_off])[:,2::4]
            on = np.array([on[ch].data for on in spectra_on])[:,2::4]
            offmean = off.mean(axis=0)
            offstd = off.std(axis=0)
            offpow.append(offmean)
            onmean = on.mean(axis=0)
            onstd = on.std(axis=0)
            onpow.append(onmean)

            ax[ch].plot(onmean-offmean,'b.')
            ax[ch].plot(offmean,'r.')
            ax[ch].semilogy()
            ax[ch].set_title(f"Channel {ch}")
            ax[ch].legend(["On-Off","Off"])
            #plt.plot(offstd/offmean)

        fig.savefig(os.path.join(figures_dir, "calib_power.png"))

        

        fig, ax= plt.subplots()
        for ch,(on, off) in enumerate(zip(onpow, offpow)):
            ax.plot((on-off)/(off), '.',label = f"CH{ch}")

        ont = np.sum(onpow,axis=0)
        offt = np.sum(offpow,axis=0)
        ax.plot((ont-offt)/offt, 'k-',label = "Total")

        ax.set_xlabel("Index")
        ax.set_ylabel("Weights")

        ax.legend()
        fig.savefig(os.path.join(figures_dir, "calib_weights.png"))

        # Combine ont and offt into a single array with two columns
        data = np.column_stack((ont-offt, offt))

        # Write the data to a file
        np.savetxt(figures_dir+"/../../calib_weights.dat", data, header="", comments='')

        self.results['result'] = int(passed)
