import sys
import matplotlib.pyplot as plt
import os


import argparse
import numpy as np
from test_base import Test
from  scripter.lusee_script import Scripter
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

        scripter = Scripter()
        scripter.reset()
        scripter.wait(1)
        scripter.set_Navg(14,3)
        scripter.set_reject(128, 20)
        scripter.start()
        scripter.wait(5)
        ## inject 1000 outliers that are x2 in amplitude and type = 0 (spectrum independent)
        scripter.inject_outlier(num=1000,fact=2,type=0)
        scripter.wait(5)
        ## inject 1000 outliers that are x2 in amplitude and type = 1 (single bin)
        scripter.inject_outlier(num=1000,fact=2,type=1)
        scripter.wait(10)
        ## change the type of the spectrum -- see if it is going to accept new one after some time
        scripter.ADC_special_mode('ramp')
        scripter.wait(15)
        scripter.stop()
        scripter.ADC_special_mode('normal')
        scripter.wait(1)
        return scripter
    
    def analyze(self, collection: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test. 
            Returns true if test has passed.
        """
        self.results = {}
        passed = True
        
        self.results['packets_received'] = len(collection.cont)
        
        collection.cut_to_hello()
        self.inspect_hello_packet(collection)
        # FIXME
        self.results['result'] = int(passed)




