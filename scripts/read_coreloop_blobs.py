#!/usr/bin/env python
import sys
import numpy as np
import matplotlib.pyplot as plt
sys.path.append(".")

import glob
from tqdm import tqdm
import uncrater


dir = "../coreloop/data/cdi_output"

fnames =  glob.glob(dir+"/*bin")
fnames = sorted(fnames)
datastream = uncrater.DataStream() 
for fname in tqdm(fnames):
    appid = int(fname.replace('.bin','').split("_")[-1],16)
    with open(fname,'rb') as f:
        binary_blob = f.read()
        datastream.process(appid,binary_blob)

freq = 0.025*np.arange(2048)
freqavg = freq.reshape(-1,2).mean(axis=1)
for s in datastream.data:
    print(s.metadata)
    if s.metadata['seq']['Navgf'] == 1:
        plt.plot(freq,s.data[0])
    elif s.metadata['seq']['Navgf'] == 2:
        plt.plot(freqavg,s.data[0])
    else:
        raise ValueError("Unknown Navgf")
    
plt.show()
