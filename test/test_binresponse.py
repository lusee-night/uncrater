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


class Test_BinResponse(Test):

    name = "bin_response"
    version = 0.1
    description = """ Test the response of a bin to a signal, tests notch filter."""
    instructions = """ Connect a signal generator and use an --awg option. """
    default_options = {
        "bin" : 100,
        "amplitude" : "40",
        "gain": "M",
        "bitslice": 31,
        "notch": False,
        "channel" : 0,
        "Df": 0.1,
        "Nf": 31,
    } ## dictinary of options for the test
    options_help = {

        "bin" : "Which spectral bin to test on",
        "amplitude" : "Amplitude of the signal",
        "gain": "Gain setting",
        "bitslice": "Bitslicer setting",
        "notch": "Enable notch filter",
        "channel" : "Channel number (starting with 0).",
        "Df": "+/- frequency deviation",
        "Nf": "Number of frequencies to test"
    } ## dictionary of help for the options

    def get_frequencies (self):
        return np.linspace(-self.Df,self.Df,self.Nf)

    def generate_script(self):
        """ Generates a script for the test """
        
        ch = self.channel
        S = Scripter()
        S.awg_init()

        S.wait(1)
        S.reset()
        S.wait(3)

        S.select_products(0b1111)#1<<ch)
        S.set_Navg(14,2)
        #S.set_bitslice(ch,int(self.bitslice))
        S.set_ana_gain(self.gain*4)
        delta_freq = self.get_frequencies()
        central_freq= 0.025*self.bin

        for i,df  in enumerate(delta_freq):
            S.awg_tone(ch, central_freq+df, self.amplitude)
            S.wait(0.5)
            S.start()
            S.wait(3)
            S.stop()
            S.wait(3)     
               
        S.wait(5)
        S.stop()

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

        Ns = len(C.spectra)
        self.results['Ns'] = Ns
        
        self.results['Ns_expected'] = self.Nf
        self.results['Ns_ok'] = int(self.Nf==Ns)

        
        if self.results['Ns_expected']:
            adc_min = C.spectra[0]['meta'].adc_min[self.channel]    
            adc_max = C.spectra[0]['meta'].adc_max[self.channel]    
            self.results['adc_min'] = adc_min
            self.results['adc_max'] = adc_max
            self.results['bitslicer'] = 'X'
            freqs = self.get_frequencies()
            values = [S[self.channel].data[self.bin] for S in C.spectra]
            fig, ax = plt.subplots(4,1, figsize=(10, 6))
            ax[0].plot(freqs,values)
            #ax[1].plot(freqs,values)
            for i in range(3):
                print (C.spectra[i][1].data)
                ax[1].plot(C.spectra[i][1].data)
                ax[2].plot(C.spectra[i][2].data)
                ax[3].plot(C.spectra[i][3].data)

            ax[1].set_yscale('log')
            ax[0].set_xlabel('Frequency deviation (MHz)')
            ax[0].set_ylabel('Response')
            ax[1].set_xlabel('Frequency deviation (MHz)')

        
            fig.tight_layout()
            fig.savefig(figures_dir + '/response.pdf')

        else:
            passed = False
            self.results['adc_min'] = 'X'
            self.results['adc_max'] = 'X'
            self.results['bitslicer'] = 'X'
        self.results['result'] = int(passed)
