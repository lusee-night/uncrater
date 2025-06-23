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



class Test_ChCheck(Test):
    
    name = "chcheck"
    version = 0.1
    description = """ Runs minimal spectrometer code to check channel throughput"""
    instructions = """ It will attempt to setup signals at bins 201, 203, 205, 207 """
    default_options = {
        "auto_only" : True,
        "Navg2":  2,
        "Vpp": 30,
    } ## dictinary of options for the test
    options_help = {
        "auto_only" : "Only take the auto spectra",
        "Navg2": "Navg2 setting for the second stage",
        "Vpp": "Vpp for the tones"
    } ## dictionary of help for the options




    def get_bin_list(self):
        """ Returns the list of bins to check """
        return np.array([201, 203, 205, 207])

    def get_tone_freqs(self):
        return self.get_bin_list()*0.025
    
    def generate_script(self):
        """ Generates a script for the test """


        S = Scripter()
        S.wait(1)
        S.reset()
        S.wait(3)
        S.set_dispatch_delay(6)
        S.awg_init()
        for i,f in enumerate(self.get_tone_freqs()):
            S.awg_tone(i, f, self.Vpp)
        
        ## these setting are appropriate for the SSL with no amplifiers -- fix later
        S.set_ana_gain('MMMM')
        S.set_Navg(14,self.Navg2)
        if self.auto_only:            
            S.select_products('auto_only')
            for i in range(4):
                S.set_bitslice(i,22)
        else:
            for i in range(16):
                S.set_bitslice(i,22)

        S.wait(1)

        S.start()
        S.cdi_wait_spectra(1)
        S.stop()

        S.request_eos()
        S.wait_eos()

        return S
    
    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test. 
            Returns true if test has passed.
        """
        self.results = {}
        passed = True
        
        C.cut_to_hello()
        self.get_versions(C)
        
        dbres = []
        for i,n in enumerate(self.get_bin_list()):
            try:
                pwr = C.spectra[0][i].data[n]
                db = np.log10(pwr/1e9) * 10 
            except:
                db = np.nan
            dbres.append(db)
            print ("TONE ON CHANNEL %d: %.2f dB" % (i, db))
        
        self.results['db_0'] = dbres[0]
        self.results['db_1'] = dbres[1]
        self.results['db_2'] = dbres[2]
        self.results['db_3'] = dbres[3]
            
        passed= np.all(db > 0)
        self.results['result'] = int(passed)




