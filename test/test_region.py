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
from  lusee_script import Scripter, bl
import uncrater as uc
from collections import defaultdict


def hex_parse(str,bits):
    if str[:2]=='0x':
        val = int(str,16)
    else:
        val = int(str)
    if val<0 or (val>2**bits-1):
        raise ValueError(f"Value {val} is out of range for {bits} bits")
    return val

class Test_Region(Test):

    name = "region"
    version = 0.1
    description = """ Interacts with region capability inside the flight software"""
    instructions = """ No need to connect anything"""
    default_options = {
        "cmd": "check",
        "src": 0,
        "tgt": 0
    } ## dictinary of options for the test
    options_help = {
        "cmd" : r""" What to do. check = check the status of regions; copy = copy from src to tgt; enable = enable the tgt region; disable = disable the tgt region""",
        "src" : r""" Source region for copy command""",
        "tgt" : r""" Target region for copy, enable, disable commands"""    
    } ## dictionary of help for the options

    def __init__(self, options, analysis_options=None):
        super().__init__(options, analysis_options)
        self.need_cut_to_hello = False


    def generate_script(self):
        assert self.cmd in ['check','copy','enable','disable'], f"Unknown command {self.cmd}"
        if self.cmd in ['copy','enable','disable']:
            assert 1<=self.tgt<=6, f"Target region {self.tgt} is out of range"
            if self.cmd=='copy':
                assert self.src!=self.tgt, f"Source and target regions must be different for copy command"
                assert 1<=self.src<=6, f"Source region {self.src} is out of range"

        S = Scripter()
        S.wait(1)
        S.reset()
        S.wait(1)
        S.region_unlock()

        if self.cmd=='check':
            S.region_info()
        elif self.cmd=='copy':
            S.region_cpy (self.src,self.tgt)
            S.region_info()
        elif self.cmd=='enable':
            S.region_enable(self.tgt)
            S.region_info()
        elif self.cmd=='disable':
            S.region_disable(self.tgt)
            S.region_info()        
        
        S.region_unlock(False)
        S.request_eos()
        S.wait_eos()
        return S

    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['copy_report'] = "N/A"
        if self.cmd == "copy":
            status_desc = ["Bad arguments", "Bad checksum src", "Bad checksum tgt", "Success"]
            for P in C.cont:
                if (type(P) == uc.Packet_Housekeep) and P.hk_type == 101:
                    out = "\\begin{tabular}{p{6.5cm}p{6.5cm}}\n"
                    out += f" Source region : &  {P.report.region_1} \\\\"
                    out += f" Target region : &  {P.report.region_2} \\\\ \n"
                    out += f" Source size (bytes) : &  {P.report.size_1} \\\\ \n"
                    out += f" Target size (bytes) : &  {P.report.size_2} \\\\ \n"
                    out += f" Source metadata checksum : &  {P.report.checksum_1_meta} \\\\ \n"
                    out += f" Source data checksum : &  {P.report.checksum_1_data} \\\\ \n"
                    out += f" Target metadata checksum : &  {P.report.checksum_2_meta} \\\\ \n"
                    out += f" Target data checksum : &  {P.report.checksum_2_data} \\\\ \n"
                    out += f" Copy status : &  {status_desc[P.report.status]} \\\\ \n"
                    out += "\\end{tabular}\n"
                    self.results['copy_report'] = out
                    if P.report.status != 3:
                        passed = False 
                    break
            
                    
        for P in C.cont:
            if (type(P) == uc.Packet_Housekeep) and P.hk_type == 100:
                out = "\\begin{tabular}{p{2.5cm}p{2.5cm}p{2.5cm}p{2.5cm}p{2.5cm}}\n"
                out += f" Region & Enabled & Size (bytes) & Data checksum & Metadata checksum \\\\ \\hline \n"
                for i in range(6):
                    enabled = "Yes" if P.meta_valid[i] else "No"
                    size = P.size[i]
                    checksum_meta = P.checksum_meta[i]
                    checksum_data = P.checksum_data[i]

                    out += f" {i+1} & {enabled} & {size} & {checksum_data:0x} & {checksum_meta:0x} \\\\ \n"
                out += "\\end{tabular}\n"
                self.results['region_status'] = out
                break

        self.results['result'] = int(passed)
