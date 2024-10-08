import sys
import pickle
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os


import argparse
import numpy as np
from test_base import Test
from  lusee_script import Scripter
import uncrater as uc
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.interpolate import interp1d



class Test_CPTShort(Test):
    
    name = "cpt-short"
    version = 0.1
    description = """ Comprehensive Performance Test - Short Version."""
    instructions = """ Connect AWG."""
    default_options = {
        'channels': '1234',
        'gains': 'LMH',
        'freqs': '0.1',
        'amplitudes': '400 200 100 0',
        'bitslices': '28 26 23 16',
        'amplitude_fact': '5'
    } ## dictinary of options for the test
    options_help = {
        'channels': 'List of channels used in test. 1234 will loop over channels 1 by 1, all_same will do all the same time, all_robin will round-robin frequncies.', 
        'gains' : 'List of gains used in the test.',
        'freqs': 'Frequencies used in the test. They are staggered by input channel.',
        'amplitudes': 'Amplitudes used in the test. ',
        'bitslices' : 'List of bitslices to use for the test. Must the same size as amplitudes. If empty, will assume 31 throughout.',
        'amplitude_fact': 'Factor to multiply the amplitude by for L gain and divide by for H gain.'
    } ## dictionary of help for the options


    def prepare_list(self):
        """ Prepares a list of tests based on options"""
        gain_ok = True
        for v in self.gains:
            if v not in 'LMH':
                gain_ok = False
        if not gain_ok:
            raise ValueError (f"Invalid gains seettings.")
            

        try:
            self.freqs = [float(x) for x in self.freqs.split()]
        except:
            raise ValueError ("Invalid frequencies settings")
        
        try:
            self.amplitudes = [float(x) for x in self.amplitudes.split()]
        except:
            raise ValueError ("Invalid amplitudes settings.")
            

        try:
            self.bitslices = [int(x) for x in self.bitslices.split()]
        except:
            raise ValueError ("Invalid bitslices settings.")

        if len(self.bitslices) == 0:
            self.bitslices = [31]*len(self.amplitudes)
        elif len(self.bitslices) != len(self.amplitudes):
            raise ValueError ("Invalid bitslices settings.")

        try:
            self.amplitude_fact = float(self.amplitude_fact)
        except:
            raise ValueError ("Invalid amplitude_factor setting.")
            
        
        if self.channels == 'all_same':
            channels = [0]
            all = "same"
        elif self.channels == 'all_robin':
            channels = [0]
            freq0 = self.freqs
            freq1 = self.freqs[1:] + [self.freqs[0]]
            freq2 = self.freqs[2:] + self.freqs[:2]
            freq3 = self.freqs[3:] + self.freqs[:3]
            all = "robin"
        else:
            try:
                channels = [int(x) for x in self.channels]
                for v in channels:
                    if v < 1 or v > 4:
                        raise ValueError ("Invalid channel settings.")
            except:
                raise ValueError ("Invalid channels settings.")
            all = "separate"
        self.channels = channels
        


        todo = []
        for gain in self.gains:
            for ch in self.channels:
                for i,f in enumerate(self.freqs):
                    if all == "robin":
                        freq_set = (freq0[i],freq1[i],freq2[i],freq3[i])    
                    else:
                        freq_set = (f,f,f,f)
                    for a,s in zip(self.amplitudes, self.bitslices):
                        if gain == "L":
                            a = a*self.amplitude_fact
                        elif gain == "H":
                            a = a/self.amplitude_fact
                        if ch==0:
                            ampl_set = (a,a,a,a)
                            bitslice_set = (s,s,s,s)
                        else:
                            ampl_set = [0,0,0,0]
                            bitslice_set = [31,31,31,31]
                            ampl_set[ch-1] = a
                            bitslice_set[ch-1] = s
                        todo.append((gain, ch, freq_set,ampl_set,bitslice_set))
        self.todo_list = todo





    def generate_script(self):
        """ Generates a script for the test """

        # check if self.gain is a valid gain setting
        
        self.prepare_list()

        S = Scripter()
        S.awg_init()

        S.reset()
        S.wait(3)
        S.set_Navg(14,2)
        S.select_products('auto_only')
        old_gain = None
        for gain, _, freq, ampl, bslice in self.todo_list:
            if gain != old_gain:
                gain_set = f'{gain}{gain}{gain}{gain}'
                S.set_ana_gain(gain_set)
                S.wait(0.2) # settle
                old_gain = gain
            for i,(f,a,s) in enumerate(zip(freq,ampl,bslice)):      
                S.awg_tone(i,f,a)
                S.set_bitslice(i,s)
            S.wait(0.1)
            S.waveform(4)
            S.wait(1.0)
            #for i in [0,1,2,3]:
            #    S.waveform(i)
            #    S.wait(1.0)
            S.start(no_flash=True)
            S.wait(4.0)
            S.stop(no_flash=True)
            #S.wait()
                
        S.awg_close()
        return S
    
    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test. 
            Returns true if test has passed.
        """
        self.results = {}
        passed = True
        
        self.results['packets_received'] = len(C.cont)
        
        C.cut_to_hello()
        self.get_versions(C)     

        # extract data

        waveforms = [[],[],[],[]]
        hk = None
        num_wf =0 

        self.prepare_list()
        num_sp_expected = len(self.todo_list)
        num_wf_expected = num_sp_expected*4
        
        for P in C.cont:

            if type(P) == uc.Packet_Waveform:
                num_wf += 1
                P._read()
                waveforms[P.ch].append(P.waveform)

        num_sp = len(C.spectra)
        

        if (num_wf!=num_wf_expected):
            print ("ERROR: Missing waveforms or housekeeping packets.")
            passed = False
        if (num_sp!=num_sp_expected):
            print ("ERROR: Missing spectra.")
            passed = False

        self.results['num_wf'] = num_wf
        self.results['num_wf_expected'] = num_wf_expected
        self.results['num_wf_ok'] = int(num_wf == num_wf_expected)
        self.results['num_sp'] = num_sp
        self.results['num_sp_expected'] = num_sp_expected
        self.results['num_sp_ok'] = int(num_sp == num_sp_expected)

        sp_freq = C.spectra[0]['meta'].frequency

        freq0 = self.freqs
        freq1 = self.freqs[1:] + [self.freqs[0]]
        freq2 = self.freqs[2:] + self.freqs[:2]
        freq3 = self.freqs[3:] + self.freqs[:3]


        figlist = []

        results_list = []
        power_out = {}
        power_in = {}
        power_zero = {}

        data_plots = True
     
        print ("... collecting and perhaps plotting...")
        for cc, sp in enumerate(C.spectra):
            g, ch, freq_set, ampl_set, bitslic = self.todo_list[cc]
 

            if data_plots:
            
                fig = plt.figure(figsize=(12, 8))
                title = f"Gain {g}" + " ({0:.1f} {1:.1f} {2:.1f} {3:.1f})MHz".format(*freq_set)+ " ({0:.1f} {1:.1f} {2:.1f} {3:.1f})mVpp".format(*ampl_set)
                fig.suptitle(title)

                gs = gridspec.GridSpec(2, 2, height_ratios=[2, 1])
                ax_large = fig.add_subplot(gs[0, :])
                ax_left = fig.add_subplot(gs[1, 0])
                ax_right = fig.add_subplot(gs[1, 1])

                # Plot waveforms in the large plot
                for ch in range(4):
                    ax_large.plot(waveforms[ch][cc], label=f'Channel {ch+1}')
                ax_large.set_title('Waveforms')
                ax_large.legend(loc='upper right')

                # Plot spectra in the left plot (linear scale)
                for ch in range(4):
                    sp[ch]._read()    
                    ax_left.plot(sp_freq, sp[ch].data, label=f'Channel {ch+1}')
                ax_left.set_title('Spectra (Linear Scale)')
                ax_left.set_xlabel('Frequency')
                ax_left.set_ylabel('Amplitude')

                # Plot spectra in the right plot (logarithmic scale)
                for ch in range(4):
                    ax_right.plot(sp_freq, sp[ch].data, label=f'Channel {ch+1}')
                ax_right.set_title('Spectra (Logarithmic Scale)')
                ax_right.set_xlabel('Frequency')
                ax_right.set_ylabel('Amplitude')
                ax_right.set_yscale('log')

                plt.tight_layout(rect=[0, 0, 1, 0.96])
                plt.savefig(os.path.join(figures_dir, f'data_{cc}.png'))
                plt.close()
                
                figlist.append("\n\includegraphics[width=0.8\\textwidth]{Figures/data_%d.png}\n"%cc)

            waveforms_out = [waveforms[i][cc] for i in range(4)]
            [sp[i]._read() for i in range(4)]
            spectra_out = [sp[i].data for i in range(4)]
            results_list.append(list(self.todo_list[cc])+[waveforms_out, spectra_out])          

            if ch>0:
                chlist = [ch]
            else:
                chlist = [1,2,3,4]


            for ch in chlist:
                cfreq = freq_set[ch-1]
                key = (ch,g,cfreq)
                # now we need to isolate the power
                bin = int(cfreq/0.025+1e-3)
                if bin>2048:
                    bin = 2048-bin # aliasing


                if key not in power_out:
                    power_out[key] = []
                    power_in[key] = []
                    
                sppow = sp[ch-1].data* (2**(bitslic[ch-1]-31))
                #print (cfreq,sppow[bin-1],sppow[bin],sppow[bin+1])

                power_out[key].append(sppow[bin])
                ## we have *1000 to get from mV to V, *1e-4 to account for 40dB attenuation, *(1e9)**2 to get from V^2 to nV^2, /25e3 to get from 25kHz bandwidth to get to nV^2/Hz
                power_in[key].append((ampl_set[ch-1]/1000)**2*1e-4 *(1e9)**2 /25e3)  
                #print ('here',ch, ampl_set, power_in[key][-1], power_out[key][-1])

                if ampl_set[ch-1] == 0:
                    if (ch,g) not in power_zero:
                        power_zero[(ch,g)] = []
                    power_zero[(ch,g)].append(sppow)

        pickle.dump(results_list, open(os.path.join(figures_dir, '../../data.pickle'), 'wb'))
        self.results['data_plots'] = "".join(figlist)

        print ('... plotting telemetry ...')

        self.plot_telemetry(C.spectra, figures_dir)

        


        print ("... fitting straight lines ...")
        fig, ax  = plt.subplots(len(self.freqs), 3, figsize=(12,1*len(self.freqs)))
        if len(self.freqs) == 1:
            ax = [ax]

        clr = "rgby"
        gain_ndx = {'L':0, 'M':1, 'H':2}
        power_zero_fit = {}
        conversion = {}
        for key in power_out:
            c,g,f = key
            fi = self.freqs.index(f)
            #print (key, power_out[key], power_in[key])
            slope, offset = np.polyfit(power_in[key],power_out[key],1, w = 1/np.sqrt(power_out[key]))
            #print (key, slope, offset, power_zero[key])
            power_zero_fit[key] = offset
            conversion[key] = slope
            ax[fi][gain_ndx[g]].plot(power_in[key], power_out[key], 'o', color=clr[ch-1])
            ax[fi][gain_ndx[g]].plot(power_in[key], np.array(power_in[key])*slope+offset,'-', color=clr[ch-1])
            ax[fi][0].set_ylabel(f"{f} MHz")
            #ax[fi][c-1].set_yscale('log')
            #ax[fi][c-1].set_xscale('log')
        ax[0][0].set_title('L Gain')
        ax[0][1].set_title('M Gain')
        ax[0][2].set_title('H Gain')
        fig.savefig(os.path.join(figures_dir, 'power_fits.pdf'))

        print ("... plotting gain / noise curves...")
        figlist_res = []
        if 0 in self.channels:
            chlist = [1,2,3,4]
        else:
            chlist = self.channels
        
        for ch in chlist:
            for g in self.gains:
                pzero_fit = np.array([power_zero_fit[(ch,g,f)] for f in self.freqs])
                conv = np.array([conversion[(ch,g,f)] for f in self.freqs])
                conv_fit = interp1d(self.freqs, conv, kind='linear', fill_value='extrapolate')
                fig, ax = plt.subplots(1,2, figsize=(12,6))
                ffreq=np.arange(2048)*0.025
                pzero = np.array(power_zero[(ch,g)])    
                pzero = pzero.mean(axis=0)
                self.freqs=np.array(self.freqs)
                ax[0].plot(ffreq,np.sqrt(pzero/conv_fit(ffreq)) , 'b-')
                ax[0].plot(self.freqs[self.freqs<51.2], np.sqrt(pzero_fit/conv)[self.freqs<51.2],'ro' )
                ax[1].plot(ffreq,conv_fit(ffreq), 'b-')
                ax[1].plot(self.freqs, conv, 'ro')
                ax[0].set_yscale('log')
                ax[1].set_yscale('log')
                ax[0].set_xlabel('Frequency [MHz]')
                ax[0].set_ylabel('Noise [nV/sqrt(Hz)]')
                ax[1].set_xlabel('Frequency [MHz]')
                ax[1].set_ylabel('Conversion [SDU/(nV^2/Hz)]')
                fig.suptitle(f"Channel {ch} Gain {g}")  
                fig.savefig(os.path.join(figures_dir, f'results_pk_{ch}_{g}.png'))
                figlist_res.append("\n\includegraphics[width=1.0\\textwidth]{Figures/results_pk_"+f"{ch}_{g}"+".png}\n")

#                for f in self.freqs:
#                    key = (ch,g,f)
#                    if key not in power_zero_fit:
#                        power_zero_fit[key] = 0
#                        conversion[key] = 0
        # doign real space  analysis:
        figlist_res_real = []
        v2adu_emi = {'L':5.37E-02,	'M':8.07E-03,	'H':1.22E-03}
        for g in self.gains:
            fig, ax = plt.subplots(1,1, figsize=(12,6))
            for ch in chlist:
                rat = []
                for f in self.freqs:
                    ampl_max =0
                    for cc,(_g, ch_, freq_set_, ampl_set_, bitslic_) in enumerate(self.todo_list):
                        if ch_ == ch and _g == g and freq_set_[ch-1] == f and ampl_set_[ch-1]>ampl_max:
                            ampl_max = ampl_set_[ch-1]
                            cc_max = cc
                    wform = waveforms[ch-1][cc_max]
                    adu_range = wform.max()-wform.min()
                    Vpp = ampl_max*1e-3*1e-2 #1e-3 for mV to V, 1e-2 for 40dB power attenuation
                    rat.append(Vpp/adu_range*1e4)   
                ax.plot(self.freqs, rat, label=f'Channel {ch}')
                ax.axhline(v2adu_emi[g], color='r', linestyle='--')
            ax.set_xlabel('Frequency [MHz]')
            ax.set_ylabel('Amplitude @ 10kADU')
            plt.title(f'V2ADU at gain {g}')
            fig.savefig(os.path.join(figures_dir, f'v2adu_{g}.png'))
            figlist_res_real.append("\n\includegraphics[width=1.0\\textwidth]{Figures/v2adu_"+f"{g}"+".png}\n")


        self.results['ps_results'] = "".join(figlist_res)   
        self.results['real_results'] = "".join(figlist_res_real)
        self.results['result'] = int(passed)




