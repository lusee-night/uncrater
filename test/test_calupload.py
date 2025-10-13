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
        "slots": "0.1.2.3.4",
        "src_dir": "cal_weights/"
    } ## dictinary of options for the test
    options_help = {
        "cmd" : r" What to do. check = load weights and checks their CRCs. copy = copy weights (and then check)",
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
                weights = weights.astype(np.uint8)
            except:
                raise FileNotFoundError(f"Could not open weights file {fname}")
            if len(weights) != 512:
                raise ValueError(f"Weights file {fname} has incorrect length")
            intweights = (weights).astype(np.uint32)
            pweights = [((w2<<16)+w1) for w1,w2 in zip(intweights[0::2],intweights[1::2])]
            crc = binascii.crc32(np.array(pweights,dtype=np.uint32).tobytes())&0xffffffff
            print(f"Slot {s}: CRC32 = {crc:08x}")
            res.append( (s, weights, crc) )
        return res

    def generate_script(self):
        assert self.cmd in ['check','copy'], f"Unknown command {self.cmd}"
        
        todo = self.load_weights()
        S = Scripter()
        S.wait(1)
        S.reset()
        S.wait(1)
        if self.cmd == "copy":
            for (slot, weights, crc) in todo:
                print(f"Uploading weights to slot {slot}")
                S.cal_set_weights(weights)
                S.cal_weights_save(slot)
                S.wait(1)
        ## now load those weights
        for (slot, weights, crc) in todo:
            print(f"Checking weights in slot {slot}")
            S.cal_set_single_weight(300,0xFF,zero_first=True)
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

        

        out = "\\begin{tabular}{p{2.5cm}p{2.5cm}p{2.5cm}p{2.5cm}}\n"
        out += "Slot & Expected CRC & Reported CRC & Match? \\\\\n"
        load_crc = []
        for P in C.cont:
            if (type(P) == uc.Packet_Housekeep) and P.hk_type == 3:
                load_crc.append(P.crc)
        print("Found load CRCs:", load_crc)
        todo = self.load_weights()
        if len(todo)!=len(load_crc):
            out += "Mismatch in number of CRC reports and number of slots\\\\\n"
            passed = False
        else:
            for i, (slot, weights, crc) in enumerate(todo):
                match = (crc == load_crc[i])
                if not match:
                    passed = False
                out += f"{slot} & {crc:08x} & {load_crc[i]:08x} & {'Yes' if match else 'No'} \\\\\n"

        out += "\\end{tabular}\n"
        self.results['crc_table'] = out
        self.results['result'] = int(passed)
