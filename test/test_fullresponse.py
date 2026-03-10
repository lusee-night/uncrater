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


class Test_FullResponse(Test):

    name = "full_response"
    version = 0.1
    description = """ Test the response against input signal across the spectrometer band."""
    instructions = """ Connect a signal generator and use an --awg option. """
    default_options = {
        "amplitude" : "40",
        "gain": "M",
        "bitslice": 24,
        "channels" : "0",
        "routing": "default",
        "N": 10,
        "seed": 0
    } ## dictinary of options for the test
    options_help = {
        "amplitude" : "Amplitude of the signal",
        "gain": "Gain setting",
        "bitslice": "Bitslicer setting",
        "channels" : "Channel numbers (starting with 0).",
        "routing": "Routing option",
        "N": "Number of frequencies to test (0-4096 with >4 spacing saved into bins.dat)",
        "seed": "Random seed for reproducibility"
    } ## dictionary of help for the options


    def get_bins (self):
        np.random.seed(self.seed)
        bins = []
        b = np.random.randint(0,4096)
        for _ in range(self.N):
            c = b
            while abs(c-b) < 4:
                c = np.random.randint(0,4096)
            bins.append(c)
            b = c
        return bins

    def generate_script(self):
        """ Generates a script for the test """
        
        S = Scripter()
        S.awg_init()

        S.wait(1)
        S.reset()
        S.wait(3)

        prod =0 
        for c in self.channels:
            c=int(c)
            prod+=1<<c

        S.select_products(prod)
        if self.routing == 'default':
            pass
        elif self.routing == 'invert':
            for i in range(4):
                S.set_route(i,None,i)
        elif self.routing == 'alt':
            S.set_route(0,1,None)
            S.set_route(1,0,None)
            S.set_route(2,3,None)
            S.set_route(3,2,None)
        else:
            raise ValueError("Invalid routing option")
        
        S.set_Navg(14,2)
        for c in self.channels:
            c=int(c)
            S.set_bitslice(c,int(self.bitslice))
            S.set_ana_gain(self.gain*4)
        ctone = np.random.randint(0,4096)
        self.bins = self.get_bins()
        for b in self.bins:
            ## fix this when AWG is ready.
            S.awg_tone(1, b*0.025, self.amplitude)
            S.wait(0.5)
            S.start()
            S.cdi_wait_spectra(1)
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

        self.results['packets_received'] = len(C.cont)
        self.get_versions(C)

        bins = self.get_bins()
        np.savetxt(figures_dir+"/../../bins.dat", bins, fmt='%d', header='Bins used for testing')

        Ns = len(C.spectra)
        self.results['Ns'] = Ns
        self.results['Ns_expected'] = len(bins)
        self.results['Ns_ok'] = int(Ns == self.results['Ns_expected'])

        self.results['result'] = int(passed)
