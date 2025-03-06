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
        ### fully difference every channel
        for i in range(4):
            S.set_route (i,None,i)
        

        S.cal_set_avg(6,8)
        S.cal_set_drift_step(10)
        S.select_products(0b1111)
        S.set_ana_gain('MMMM')
        
        S.set_bitslice(0,10)
        for i in range(1,4):
            S.set_bitslice(i,20)    

        
        fstart = 17.0
        fend = +17.0
        S.awg_cal_on(fstart)
        #S.awg_cal_off()
        #S.wait(1)
        #S.waveform(4)
        #S.wait(3)

        S.cal_set_pfb_bin(1402)
        S.cal_antenna_enable(0b1111)
        
        S.cal_set_slicer(auto=False, powertop=11, sum1=17, sum2=17, prod1=19, prod2=22, delta_powerbot=2, sd2_slice=0)
        #S.cal_set_slicer(auto=False, powertop=12, sum1=19, sum2=26, prod1=19, prod2=22, delta_powerbot=0, sd2_slice=0)
        S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_RUN)  # ...RAW3
        
        #S.cal_enable(True)
        #S.cal_enable(enable=False)

        S.cal_SNRonff(70,2)
        sig, noise = np.loadtxt("session_calib_weights/calib_weights.dat").T

        weights = (sig/(noise)**1.5)
        weights /= weights.max()
        weights[weights<0.5]=0
        
        np.savetxt("d.txt",weights)
        S.cal_set_weights(weights)
        
        #S.cal_set_single_weight(350,128,zero_first=True)
        #S.cal_set_single_weight(470,128,zero_first=False)
        #S.cal_set_single_weight(390,128,zero_first=False)
        #S.cal_set_single_weight(400,128,zero_first=False)

        #S.wait(10)
        S.set_notch(4,disable_subtract=True) # plus 16 to disable subtraction
        S.start()
        #S.wait(20)
        #for d in np.linspace(fstart,fend,500):
        #    S.awg_cal_on(d)
        #    S.wait(0.3)
        
        #S.cdi_wait_spectra(85)
        S.cdi_wait_minutes(10)
        S.stop()
        
        S.request_eos()
        S.wait_eos()
        #wait for uart to clear
        #S.wait(10)
        
        #S.wait(3)
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
