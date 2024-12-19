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


class Test_Calibrator(Test):

    name = "calibrator"
    version = 0.1
    description = """ Runs the WV calibrator EM """
    instructions = """ Connect the VW calibrator.  """
    default_options = { 
        "preset": "debug",
        "slow": False
    } ## dictinary of options for the test
    options_help = {
        "preset" : "Type of present. Can be debug",
        "slow": "Run the test in slow mode for SSL"

    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """
        if self.preset not in ['debug']:
            raise ValueError ("Unknown preset.")


        S = Scripter()
            
        S.wait(1)
        S.reset()
        S.wait(3)

        if self.slow:
            S.set_dispatch_delay(120)
    
        S.enable_heartbeat(False)
        S.set_Navg(14,4)
        #for i in range(4):
        S.set_route (0,None,None)

        S.cal_set_avg(6,4)
        S.select_products(0b0000)
        S.set_ana_gain('MMMM')
        S.set_bitslice(0,16)        
        for i in range(1,4):
            S.set_bitslice(i,20)    
        
        fstart = 17.55
        fend = 17.55
        S.awg_cal_on(fstart)
        #S.wait(1)
        #S.waveform(4)
        #S.wait(3)

        S.cal_set_pfb_bin(1402)
        S.cal_antenna_enable(0b1111)
        #S.cal_set_single_weight(350,128,zero_first=True)
        #S.cal_set_single_weight(470,128,zero_first=False)
        #S.cal_set_single_weight(390,128,zero_first=False)
        #S.cal_set_single_weight(400,128,zero_first=False)

        #S.wait(10)
        S.set_notch(4)
        S.start()
        S.cal_enable(on = True, readout_mode=0b00, special_mode=0b00)
        S.wait(20)
        for d in np.linspace(fstart,fend,200):
            S.awg_cal_on(d)
            S.wait(0.1)
        S.wait(10)
        S.stop()
        #S.wait(20)
        #S.stop()
        #S.wait(4)

        
        
        
        #S.set_notch(4)
        #S.cal_on(-5.0)
        #S.wait(1)
        #S.start()
        #for i in np.linspace(17.5,17.7,500):
        #    S.cal_on(i)
        #    S.wait(0.1)
        #S.stop()
        
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


        self.results['result'] = int(passed)
