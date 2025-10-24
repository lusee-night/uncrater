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
import binascii
import uncrater as uc
from collections import defaultdict


class Test_CalUpload(Test):

    name = "calupload"
    version = 0.1
    description = """ Upload and/or check calibration weights"""
    instructions = """ No need to connect anything"""
    default_options = {
        "cmd": "check",
        "slow": True,
        "slots": "0.1.2.3.4.5.6.7.8",
        "src_dir": "cal_weights/"
    } ## dictinary of options for the test
    options_help = {
        "cmd" : r" What to do. check = load weights and checks their CRCs. copy = copy weights (and then check)",
        "slow" : r" Whether to use slow mode (for SSL)",
        "slots" : r" Dot separated list of weight slots to consider",
        "src_dir" : r" Directory containing the calibration weights files"
    } ## dictionary of help for the options

    def __init__(self, options, analysis_options=None):
        super().__init__(options, analysis_options)
        self.need_cut_to_hello = False

    def load_weights(self):
        print('\n')
        slots = [int(s) for s in self.slots.split('.')]
        assert all([0<=s<10 for s in slots]), "Slots must <10"

        res = []
        for s in slots:
            fname = self.src_dir + f'/{s}.dat'
            try:
                weights = np.loadtxt(fname)
                weights = weights.astype(int)
            except:
                raise FileNotFoundError(f"Could not open weights file {fname}")
            if len(weights) != 512:
                raise ValueError(f"Weights file {fname} has incorrect length")
            weights[:90] = 0  # zero the first 90 weights
            weights[500:] = 0  # zero the last 11 weights
            weights = weights.astype(np.uint32)
            checksum = (weights[::2]<<16).sum()+weights[1::2].sum()
            csum = int(checksum) & 0xFFFFFFFF
            print(f"Slot {s}: Checksum = {csum:08x}")
            res.append( (s, weights, csum) )
        return res

    def generate_script(self):
        assert self.cmd in ['check','copy'], f"Unknown command {self.cmd}"
        
        todo = self.load_weights()
        S = Scripter()
        S.wait(1)
        S.reset()
        S.wait(1)
        if self.slow:
            S.set_dispatch_delay(120)
        if self.cmd == "copy":
            for (slot, weights, _) in todo:
                print(f"Uploading weights to slot {slot}")
                #print (weights)
                S.cal_set_weights(weights,raw=True)
                S.cal_weights_save(slot)
                S.wait(1)
        ## now load those weights
        for (slot, weights, _) in todo:
            print(f"Checking weights in slot {slot}")
            S.cal_set_single_weight(300,0xFF,zero_first=True, raw= True)
            S.cal_weights_load(slot)
            # get CRC report
            S.house_keeping(3)
            S.wait(1)

        S.request_eos()
        S.wait_eos()
        return S

    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        

        out = "\\begin{tabular}{p{1.5cm}p{1.5cm}p{1.5cm}p{1.5cm}p{1.5cm}p{1.5cm}p{1.5cm}}\n"
        out += "Slot & Expected  & Save & Load & Match? & Last index \\\\\n"
        load_csum = []
        load_index = []
        for P in C.cont:
            if (type(P) == uc.Packet_Housekeep) and P.hk_type == 3:
                load_csum.append(P.checksum)
                load_index.append(P.weight_ndx)
                
        
        todo = self.load_weights()
        if self.cmd=="copy":
            save_csum = load_csum[:len(todo)]
            load_csum = load_csum[len(todo):]  # only keep the load ones
            save_index = load_index[:len(todo)]
        else:
            save_csum = [0] * len(todo)
            load_csum = load_csum[:len(todo)] ## does nothing really
            save_index = [0] * len(todo)
        
        if (len(todo)!=len(load_csum)) or (len(todo)!=len(save_csum)):
            out += "Mismatch in number of csums reports and number of slots\\\\\n"
            passed = False
        else:
            for i, (slot, _ , csum) in enumerate(todo):
                match = (csum == load_csum[i]) 
                if self.cmd=='copy':
                    match = match and (csum == save_csum[i])
                if not match:
                    passed = False
                out += f"{slot} & {csum:08x} & {save_csum[i]:08x} & {load_csum[i]:08x} & {'Yes' if match else 'No'} & {save_index[i]} \\\\\n"

        out += "\\end{tabular}\n"
        self.results['csum_table'] = out
        self.results['result'] = int(passed)
