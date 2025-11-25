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


class Test_Transit(Test):

    name = "transit"
    version = 0.2
    description = """ Script to be run during transit, derived alive 0.1"""
    instructions = """ """
    default_options = {
    } ## dictinary of options for the test
    options_help = {
    } ## dictionary of help for the options


    def generate_script(self):

        S = Scripter()
        S.reset()
        S.wait(0.5)
        S.seq_begin()
        S.set_cdi_delay(1)
        S.set_dispatch_delay(100)
        S.enable_watchdogs(2) ## just the clock watchdog

        # first ramp mode
        S.ADC_special_mode('ramp')
        S.waveform(4)          
        S.cdi_wait_seconds(10)               
        S.ADC_special_mode('normal')

        # next waveforms in all gains
        S.set_ana_gain('LLLL')
        S.cdi_wait_ticks(30)
        S.waveform(4)               
        S.cdi_wait_seconds(10) 
        S.set_ana_gain('MMMM')
        S.cdi_wait_ticks(30)
        S.waveform(4)          
        S.cdi_wait_seconds(10)       
        S.set_ana_gain('HHHH')
        S.cdi_wait_ticks(30)
        S.waveform(4)          
        S.cdi_wait_seconds(10)       

        # next some spectra with automatic gain and everything
        S.set_Navg(14,6)
        S.set_ana_gain('AAAA')
        S.set_avg_mode('40bit')        
        S.adc_range()
        S.set_bitslice_auto(12)        
        S.start()        
        S.cdi_wait_spectra(5)
        S.stop()
        S.set_notch(4)
        S.start()        
        S.cdi_wait_spectra(5)
        S.stop()
        S.set_notch(6)
        S.start()        
        S.cdi_wait_spectra(5)
        S.stop()
        S.reject_enable(reject_frac=10, max_bad = 100) 
        S.start()        
        S.cdi_wait_spectra(5)
        S.stop()

    
        # check stored calibrator weights CRCs
        for i in range(9):
            S.cal_weights_load(i)
            S.house_keeping(3)
            S.cdi_wait_seconds(1)
    
        S.region_unlock()
        S.region_info()
        S.region_unlock(False)
        # take region info 
        # general HK
        S.house_keeping(0)
        S.request_eos()
        S.seq_end()

        S.wait_eos()
        return S

    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)

        if len(C.cont) == 0:
            print ("No packets received, aborting")
            self.results['result'] = 0
            return 

        self.get_versions(C)

        self.results['result'] = int(passed)
        