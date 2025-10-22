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



class Test_Live(Test):

    name = "live"
    version = 0.1
    description = """ Take data that can be displayed with display_live.py."""
    instructions = """ Connect anything you want."""
    default_options = {
        "mode": "adc",
        "gain": "MMMM",
        "slicer": -4,
        "Navg2" : 3,
        "cdi_delay": 1,
        "slow": True,
        "sleep": 1
    } ## dictinary of options for the test
    options_help = {
        "mode": "adc = for adc stats, spectra for live spectra",
        "gain": "Gain settings",
        "slicer": "spectral bitslicer (0-31) or negative number for auto (will take abs for keep bits)",
        "Navg2": "Number of averages for spectra (default 3)",
        "cdi_delay": "Delay in units of 1.26ms for the CDI to space packets by (0=225ns)",
        "slow": "Snail mode for SSL",
        "sleep": "Sleep time between ADC packet request in seconds (default 1)"
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """
        if self.mode not in ['adc','spectra']:
            print ("Unknown waveform type. ")
            sys.exit(1)


        S = Scripter()
        S.reset()
        ## this is the real wait
        S.wait(3)

        for i in range(4):        
            S.set_route(i, None, i)

        S.set_cdi_delay(int(self.cdi_delay))
        S.set_dispatch_delay(100 if self.slow else 6)
        S.set_ana_gain(self.gain)
        S.set_Navg(14,self.Navg2)
        S.select_products('auto_only')
        S.set_avg_mode('40bit')        

        if self.slicer>0:
            S.set_bitslice('all', self.slicer)
        else:
            S.set_bitslice_auto(-self.slicer)

        if self.mode == 'adc':
            for i in range(3600):
                S.adc_range()
                S.wait(self.sleep)
        else:
            S.start()
            S.wait(3600)
            S.stop()

        return S

    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['result'] = int(passed)
