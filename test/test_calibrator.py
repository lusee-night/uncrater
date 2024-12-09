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
    
        S.set_Navg(14,2)
        S.select_products('auto_only')
        S.set_ana_gain('MMMM')
        S.cal_off()
        S.start()
        S.wait(5)
        S.cal_on(0.0)
        S.wait(5)
        S.cal_off()
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


        self.results['result'] = int(passed)
