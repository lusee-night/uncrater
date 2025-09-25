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


class Test_Grimm(Test):

    name = "grimm"
    version = 0.1
    description = """ Test the rover with the Grimm select frequencies  """
    instructions = """ Does not matter what you connect"""
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

        ### Main spectral engine
        for i in range(4):        
            S.set_route(i, None, i)
 
        S.set_ana_gain('MMMM')
        
        #S.loop_start(200)
        #S.waveform(1)
        #S.cdi_wait_ticks(50)
        #S.loop_next()
        
        
        S.set_Navg(14,6)

        S.set_bitslice_auto(10)
        S.set_avg_mode('40bit')
        for i in range(32):
            S.grimm_tales_weight(i,20+3*i)
        S.enable_grimm_tales()
        S.cal_set_zoom_ch(1,2)
        S.cal_set_zoom_navg(6)
        S.cal_set_pfb_bin(1172)
        S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_ZOOM)
        
        #for i in range(1172, 1193):
        #    S.cal_set_pfb_bin(i)
        S.start()
        S.cdi_wait_minutes(20)
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
        self.results['result'] = int(passed)
