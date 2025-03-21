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


class Test_Control(Test):

    name = "control"
    version = 0.1
    description = """ Tests control features (loops etc)"""
    instructions = """ Do not need to connect anything."""
    default_options = {
    } ## dictinary of options for the test
    options_help = {
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """


        S = Scripter()
        S.reset()
        ## this is the real wait
        S.wait(3)

        S.cdi_wait_seconds(1)
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

        self.results['packets_received'] = len(C.cont)

        if len(C.cont) == 0:
            print ("No packets received, aborting")
            self.results['result'] = 0
            return 

    


        self.results['result'] = int(passed)
