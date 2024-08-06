
import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')

from test_base import Test
from  lusee_script import Scripter
from commander import Commander
import argparse
import numpy as np


class Test_CrossTalk(Test):
    
    name = "crosstalk"
    description = """ Measures cross-talk between two channels."""
    instructions = """Connect a noise source to the affected channel and a signal generator to the harassing channel. The signal generator should be set to sweep a frequency from 0-100MHz over 500s with amplitude 1Vpp (for medium gain)...."""
    default_options = {
        "channel_affected" : 0,
        "channel_harassing" : 1,
        "gain_affected": "M",
        "gain_harassing": "M",
    } ## dictinary of options for the test
    options_help = {
        "channel_affected" : "Channel for which the cross-talk is measured.",
        "channel_harassing" : "Channel which harasses the affected channel.",
        "gain_affected": "Gain setting for the affected channel.",
        "gain_harassing": "Gain setting for the harassing channel.",
    } ## dictionary of help for the options

    
    
    
    
    
    def do():
        channel_config = args.channel_config
        autorange = args.gain_autorange
        just_auto = args.just_auto
        Navg1, Navg2= args.Navg1, args.Navg2
        slice_config = args.slice_config
        slice_autorange = args.slice_autorange
        
        S = Scripter()
        S.reset()
        S.ana_gain("MMMM") # to prevent any auto
        cfg = channel_config.split(':')
        if len(cfg)!=4:
            print ('bad configuration\n')
            sys.exit(1)

        for i,c  in enumerate(cfg):
            c=c.strip()
            g=c[0]
            assert (g in 'LMHD')
            p = int(c[1])
            m =int (c[2])
            S.route(i,p,m,g)

        if autorange:
            S.ana_gain("AAAA") # sets everything to auto (except disabled)

        S.set_Navg(Navg1,Navg2)
        if just_auto:
            S.select_products(0b1111) # just auto
            
        if len(slice_config)>0:
            for i, val in enumerate(slice_config.split(':')):
                S.set_bitslice(i,int(val))
            
        if slice_autorange:
            S.set_bitslice_auto(10)
            
        S.start()

        S.exit(dt=args.time)    
        S.write_script("test_spec")
        C = Commander(session="session_test_spec", script='test_spec')
        C.run()
        
    def nbits (v):
        return int(np.log(v)/np.log(2)+1) if v>0 else 0
        
    def analyze():
        try:
            import uncrater
            from uncrater import Collection
        except:
            print ("No uncrater. Sorry.\n")
            sys.exit(1)
        import matplotlib.pyplot as plt
        
        C = Collection('session_test_spec/cdi_output')
        print (C.list())
        stat=None
        for p in C.cont:
            if type(p)==uncrater.Packet_Metadata:
                print (p.info()) 
        
        import matplotlib.pyplot as plt            
        fig, ax= plt.subplots(1,4,figsize=(12,6))
        freq=np.arange(2048)*0.025
        print (C.spectra[0][1].data)
        for sp in C.spectra:
            print ('--------------------------')
            for i in range(4):            
                data = sp[i].data
                ax[i].plot(freq,data)            
                ax[i].set_yscale('log')
                print (f"Range: {data.min()} - {data.max()} ; Bits: {nbits(data.min())} - {nbits(data.max())}")
        plt.show()
        