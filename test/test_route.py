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



class Test_Route(Test):
    
    name = "route"
    version = 0.2
    description = """ Runs the spectrometer and iterates over routing combinations"""
    instructions = """ It will attempt to setup signals at 2 3 5 7 MHz across J4-J7 """
    default_options = {
        "auto_only" : True,
        "Navg2":  3,
        "Vpp": 30,
    } ## dictinary of options for the test
    options_help = {
        "auto_only" : "Only take the auto spectra",
        "Navg2": "Navg2 setting for the second stage",
        "Vpp": "Vpp for the tones"
    } ## dictionary of help for the options


    def get_route_list(self):
        out = []
        # first ground in ground everywhere
        out.append ( [(None,None), (None,None), (None,None), (None,None)] )
        for i in range (4):
            i1, i2, i3, i4 = i, (i+1)%4, (i+2)%4, (i+3)%4
            out.append ( [(i1,None), (i2,None), (i3,None), (i4,None)] )
            out.append ( [(None,i1), (None,i2), (None,i3), (None,i4)] )
            out.append(  [(i1,i1), (i2,i2), (i3,i3), (i4,i4)] )
            out.append(  [(i1,None), (i1,None), (i1,None), (i1,None)] )
            out.append(  [(i1,i2), (i2,i3), (i3,i4), (i4,i1)] )

        return out


    def get_tone_freqs(self):
        return np.array([5, 7, 11, 13])
    def generate_script(self):
        """ Generates a script for the test """


        S = Scripter()
        S.wait(1)
        S.reset()
        S.wait(3)
        S.set_dispatch_delay(6)
        S.awg_init()
        for i,f in enumerate(self.get_tone_freqs()):
            S.awg_tone(i, f, self.Vpp)
        
        ## these setting are appropriate for the SSL with no amplifiers -- fix later
        S.set_ana_gain('MMMM')
        S.set_Navg(14,self.Navg2)
        if self.auto_only:            
            S.select_products('auto_only')
            for i in range(4):
                S.set_bitslice(i,22)
        else:
            for i in range(16):
                S.set_bitslice(i,22)

        S.wait(1)

        route_list = self.get_route_list()
        wait_secs = 0.65536*(2**self.Navg2)+0.1
        wait_secs_int = int(wait_secs)
        wait_secs_ticks = int((wait_secs - wait_secs_int)*100)

        for route in route_list:
            for i,(plus,minus) in enumerate(route):
                S.set_route(i, plus, minus)
            

            S.start()
            S.cdi_wait_spectra(1)
            S.stop()
            S.wait (wait_secs+5)

        # force empty buffer with a HK request
        S.wait(1)
        S.house_keeping(0)
        # wait for the buffer to empty up
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
        
        ndx = self.get_tone_freqs()*40
        freqs= 0.25*np.arange(2048)

        route_list = self.get_route_list()
        self.results ['nspectra'] = len (C.spectra)
        self.results ['nspectra_ok'] = int(len(route_list)==len(C.spectra))

        plot_list = ""


        def rt2str (rt):
            toret = ""
            for i,(a,b) in enumerate(rt):
                a = "GND" if a is None else f"I{a}"
                b = "GND" if b is None else f"I{b}"
                toret += f" CH{i} = {a}-{b} "
            return toret

        route_ok = [True, True, True, True]        
        routing_table = np.ones((4,8))
        if self.results['nspectra_ok']:
            for k, (route, S) in enumerate(zip(route_list,C.spectra)):
                fig, ax = plt.subplots(1,4, figsize=(10,3))
                fig.suptitle(f"Route {rt2str(route)}")
                for i in range(4):
                    ax[i].plot(freqs,S[i].data,'b-')
                    for ti,n in enumerate(ndx):
                        tone_present =S[i].data[n]>1e7
                        tone_should_be_present = (ti in route[i]) and (not route[i]==(ti,ti))
                        if tone_present and tone_should_be_present:
                            clr = 'go'
                        elif (tone_present and not tone_should_be_present) or (not tone_present and tone_should_be_present):
                            clr = 'ro'
                            route_ok[i] = False
                            passed = False                            
                            if route[i][0] is None:
                                routing_table[route[i][1],2*i] = 0
                            if route[i][1] is None:
                                routing_table[route[i][0],2*i+1] = 0
                        else: 
                            clr = 'ko'
                        ax[i].plot(freqs[n],S[i].data[n],clr)
                #ax[i].set_xscale('log')
                    ax[i].set_yscale('log')
                    ax[i].axhline(1e7, color='r', linestyle='--')
                    ax[i].set_ylim(10,5e9)
                fig.tight_layout()
                fig.savefig(os.path.join(figures_dir,f"route_{k}.pdf"))
                plt.close(fig)
                plot_list += "\includegraphics[width=\linewidth]{Figures/route_"+f"{k}"+".pdf}\n"
                
                routing_table_tex = """
                \\begin{tabular}{|c||c|c||c|c||c|c||c|c|}
                \\hline
                Input & CH0(+) & CH0(-) & CH1(+) & CH1(-) & CH2(+) & CH2(-) & CH3(+) & CH3(-) \\\ 
                \\hline
                """
                for i in range(4):
                    routing_table_tex += f"I{i} "
                    for j in range(8):
                        routing_table_tex += " & \\bcheckmark{"+str(int(routing_table[i,j]))+"} "
                    routing_table_tex += "\\\\ \n"
                routing_table_tex += "\\hline \n"
                routing_table_tex += "\\end{tabular}"


        else:
            passed = False
        self.results['route0_ok'] = int(route_ok[0])
        self.results['route1_ok'] = int(route_ok[1])
        self.results['route2_ok'] = int(route_ok[2])
        self.results['route3_ok'] = int(route_ok[3])

        self.results['plot_list'] = plot_list
        self.results['routing_table'] = routing_table_tex
        self.results['result'] = int(passed)




