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



class Test_Reject(Test):
    
    name = "reject"
    version = 0.1
    description = """ Test ability of the engine to reject packets"""
    instructions = """ TBC"""
    default_options = {} 
    options_help = {} ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """

        S = Scripter()
        S.reset()
        S.wait(1)
        S.set_Navg(14,3)
        S.set_reject (128, 20)
        S.start()
        S.wait(5)
        ## inject 1000 outliers that are x2 in amplitude and type = 0 (spectrum independent)
        S.inject_outlier(num=1000,fact=2,type=0)
        S.wait(5)
        ## inject 1000 outliers that are x2 in amplitude and type = 1 (single bin)
        S.inject_outlier(num=1000,fact=2,type=1)
        S.wait(10)
        ## change the type of the spectrum -- see if it is going to accept new one after some time
        S.ADC_special_mode('ramp')
        S.wait(15)
        S.stop()
        S.ADC_special_mode('normal')
        S.wait(1)
        return S
    
    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test. 
            Returns true if test has passed.
        """
        self.results = {}
        passed = True
        
        self.results['packets_received'] = len(C.cont)
        
        C.cut_to_hello()
        self.inspect_hello_packet(C)    
        FIX_HERE()
        self.results['result'] = int(passed)




