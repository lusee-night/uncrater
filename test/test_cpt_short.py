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
    version = 0.41
    description = """ Comprehensive Performance Test - Short Version."""
    instructions = """ Connect AWG."""
    default_options = {
        'channels': '0123',
        'gains': 'LMH',
        'freqs': '0.05 0.1 0.5 1 5 10 20 30 40 50 60 75 95',
        'amplitudes': '280 200 140 0',
        'bitslices': '25 23 21 16',
        'amplitude_fact': '5',
        'routing': 'default',
        'notch': False, 
        'slow': False,
        'nowave': False,
        'terminated': False, 
        'terminated_set': "",
        'corr_fact': 1.18
    } ## dictinary of options for the test
    options_help = {
        'channels': 'List of channels used in test. 1234 will loop over channels 1 by 1, all_same will do all the same time, all_robin will round-robin frequncies.',
        'gains' : 'List of gains used in the test.',
        'freqs': 'Frequencies used in the test. They are staggered by input channel.',
        'amplitudes': 'Amplitudes used in the test. ',
        'bitslices' : 'List of bitslices to use for the test. Must the same size as amplitudes. If empty, will assume 31 throughout.',
        'amplitude_fact': 'Factor to multiply the amplitude by for L gain and divide by for H gain.',
        'routing': 'Routing: default, invert, alt1 ',
        'notch': 'Enable notch filter',
        'slow': 'Enable very slow operation: large interpacket distance and minimize the number of total packets by limiting to what we really need',
        'nowave': 'Do not record waveforms to speed up',
        'terminated': 'This is a terminated set, take just the pure noise values',
        'terminated_set': "session directory with the terminated inputs (when AWG is noisy). If non-empty, the noise only sets will be taken from there. Must be run with the same options as the main test.",
        'corr_fact': "Correction factor to apply. Default is 1.18 which takes into account the suppression in the middle of the PFB response shape."
    } ## dictionary of help for the options
    
    ### NOTE TO SELF:
    ### for corrfact see cell 20 of notch_response.ipynb. We use kaiser-03 now.


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
                    if v < 0 or v > 3:
                        raise ValueError ("Invalid channel settings.")
            except:
                raise ValueError ("Invalid channels settings.")
            all = "separate"
        self.channels = channels

        print ("slow settings:", self.slow)


        todo = []
        #first find bitslice zero
        if 0 in self.amplitudes:
            bitslice_zero =self.bitslices[self.amplitudes.index(0)]
        else:
            raise ValueError ("Cannot find 0 amplitude")


        for gain in self.gains:
            for ch in self.channels:
                ## always start with zero if slow and skip it later
                if self.slow:
                    todo.append((gain,ch, (0,0,0,0), (0,0,0,0),(bitslice_zero,bitslice_zero, bitslice_zero, bitslice_zero)))

                for i,f in enumerate(self.freqs):
                    if all == "robin":
                        freq_set = (freq0[i],freq1[i],freq2[i],freq3[i])
                    else:
                        freq_set = (f,f,f,f)
                    for a,s in zip(self.amplitudes, self.bitslices):
                        if self.slow and (a==0):
                            continue
                        if gain == "L":
                            a = a*self.amplitude_fact
                        elif gain == "H":
                            a = a/self.amplitude_fact
                        if ch==-1: ## do we ever use this?
                            ampl_set = (a,a,a,a)
                            bitslice_set = (s,s,s,s)
                        else:
                            ampl_set = [0,0,0,0]
                            bitslice_set = [31,31,31,31]
                            ampl_set[ch] = a
                            bitslice_set[ch] = s
                        todo.append((gain, ch, freq_set,ampl_set,bitslice_set))
                # also one at the end
                if self.slow:
                    todo.append((gain,ch, (0,0,0,0), (0,0,0,0),(bitslice_zero,bitslice_zero, bitslice_zero, bitslice_zero)))
        self.todo_list = todo





    def generate_script(self):
        """ Generates a script for the test """

        # check if self.gain is a valid gain setting

        self.prepare_list()


        S = Scripter()
        S.awg_init()

        S.reset()
        S.wait(3)
        if (self.slow):
            S.set_cdi_delay(10)
        else:
            S.set_cdi_delay(2)
            S.set_dispatch_delay(6)
        S.set_Navg(14,2)
        if not self.slow:
            S.select_products('auto_only')
        old_gain = None

        
        
        if self.routing == 'default':
            pass
            awg_map = [0,1,2,3]
        elif self.routing == 'invert':
            for i in range(4):
                S.set_route(i,None,i)
            awg_map = [0,1,2,3]
        elif self.routing == 'alt1':
            S.set_route(0,None,3)
            S.set_route(1,None,2)
            S.set_route(2,None,0)
            S.set_route(3,None,1)
            awg_map = [3,2,0,1]
        elif self.routing == 'alt2':
            S.set_route(0,None,2)
            S.set_route(1,None,3)
            S.set_route(2,None,1)
            S.set_route(3,None,0)
            awg_map = [2,3,1,0]           
        else:
            raise ValueError ("Invalid routing setting.")

        if self.notch:
            S.set_notch(4)

        if self.nowave and self.terminated:
            for i in range(4):
                S.awg_tone(0,0,0)
                S.select_products(0b1111)

            for gain in self.gains:
                S.set_ana_gain(gain*4)
                S.set_bitslice('all', self.bitslices[-1])
                S.cdi_wait_ticks(20) # settle
                S.start(no_flash=True)
                S.cdi_wait_spectra(1)
                S.stop(no_flash=True)
                S.wait(10)
        else:

            for gain, ch, freq, ampl, bslice in self.todo_list:
                
                if gain != old_gain:
                    gain_set = f'{gain}{gain}{gain}{gain}'
                    S.set_ana_gain(gain_set)
                    S.cdi_wait_ticks(20) # settle
                    old_gain = gain

                for i,(f,a,s) in enumerate(zip(freq,ampl,bslice)):
                    S.awg_tone(awg_map[i],f,a)
                    S.set_bitslice(i,s)
                S.cdi_wait_ticks(10)
                if (not self.nowave):
                    if self.slow:
                        S.waveform(ch)
                    else:
                        S.waveform(4)
                    
                if self.slow:
                    S.select_products(1<<(ch))


                S.start(no_flash=True)
                S.cdi_wait_spectra(1)
                S.stop(no_flash=True)

                if self.nowave:
                    S.wait(4.5 if self.slow else 3)
                else:
                    S.wait(9 if self.slow else 7)
            
        # request housekeeping to force the buffer to empty
        S.house_keeping(0)
        S.request_eos()
        S.wait_eos()
        S.awg_close()
        return S

    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True


        self.results['packets_received'] = len(C.cont)

        self.get_versions(C)

        if len(self.terminated_set)>0:
            Cterminated = uc.Collection(self.terminated_set+"/cdi_output/", cut_to_hello=True)
            
            if (not self.terminated) and (len (Cterminated.spectra)!=len(C.spectra)):
                print ("ERROR: Terminated set has different number of spectra. Breaking.")
                sys.exit(1)
            print ("Loaded terminated set.")
        else: 
            Cterminated = None


        # extract data

        waveforms = [[],[],[],[]]
        hk = None
        num_wf =0

        self.prepare_list()
        if self.slow:
            num_sp_expected = len(self.todo_list)
            num_wf_expected = num_sp_expected
        else:
            num_sp_expected = len(self.todo_list)
            num_wf_expected = num_sp_expected*4

        for P in C.cont:

            if type(P) == uc.Packet_Waveform:
                num_wf += 1
                P._read()
                if self.slow:
                    for ch in range(4):
                        if ch==P.ch:
                            waveforms[ch].append(P.waveform)
                        else:
                            waveforms[ch].append(None)
                else:
                    waveforms[P.ch].append(P.waveform)

        num_sp = len(C.spectra)


        if (num_wf!=num_wf_expected) and (not self.nowave):
            print ("ERROR: Missing waveforms or housekeeping packets.")
            print (num_wf, num_wf_expected)
            passed = False
        if (num_sp!=num_sp_expected):
            print ("ERROR: Missing spectra.")
            print ('got=',num_sp, 'expected=',num_sp_expected)
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
        power_zero_terminated = {}
        data_plots = int(self.analysis_options['data_plots']) if 'data_plots' in self.analysis_options else True
        attenuation = int(self.analysis_options['attenuation']) if 'attenuation' in self.analysis_options else 40
        attenuation_fact = 10**(-attenuation/20)
        print (f"Attenuation {attenuation}dB, Afact={attenuation_fact}, use -p attenuation=X to change to X dB.")

        if data_plots:
            print ("... collecting and plotting (to speed up run with -p data_plots=False)...")
        else:
            print ("... collecting...")

        for cc, sp in enumerate(C.spectra):
            g, ch, freq_set, ampl_set, bitslic = self.todo_list[cc]
            if Cterminated is not None and (not self.terminated):
                sp_terminated = Cterminated.spectra[cc]


            if data_plots:

                fig = plt.figure(figsize=(12, 8))
                title = f"Gain {g}" + " ({0:.1f} {1:.1f} {2:.1f} {3:.1f})MHz".format(*freq_set)+ " ({0:.1f} {1:.1f} {2:.1f} {3:.1f})mVpp".format(*ampl_set)
                fig.suptitle(title)

                gs = gridspec.GridSpec(2, 2, height_ratios=[2, 1])
                ax_large = fig.add_subplot(gs[0, :])
                ax_left = fig.add_subplot(gs[1, 0])
                ax_right = fig.add_subplot(gs[1, 1])

                # Plot waveforms in the large plot

                if not self.nowave:
                    for ich in range(4):
                        ndxmax = min(int(12 * (102.4e6/(freq_set[ich]*1e6))), 16384) if freq_set[ich]>0 else 16384
                        wform = waveforms[ich][cc]
                        if wform is not None:
                            ax_large.plot(wform[:ndxmax], label=f'Channel {ich}')
                ax_large.set_title('Waveforms')
                ax_large.legend(loc='upper right')

                # Plot spectra in the left plot (linear scale)
                for ich in range(4):
                    if ich in sp:
                        sp[ich]._read()
                        try:
                            ax_left.plot(sp_freq, sp[ich].data, label=f'Channel {ich}')
                        except Exception as e:
                            print(f"Error plotting channel {ich}: {e}")

                ax_left.set_title('Spectra (Linear Scale)')
                ax_left.set_xlabel('Frequency')
                ax_left.set_ylabel('Amplitude')

                # Plot spectra in the right plot (logarithmic scale)
                for ich in range(4):
                    if ich in sp:
                        try:
                            ax_right.plot(sp_freq, sp[ich].data, label=f'Channel {ich}')
                        except Exception as e:
                            print(f"Error plotting channel {ich}: {e}")
                ax_right.set_title('Spectra (Logarithmic Scale)')
                ax_right.set_xlabel('Frequency')
                ax_right.set_ylabel('Amplitude')
                ax_right.set_yscale('log')

                plt.tight_layout(rect=[0, 0, 1, 0.96])
                plt.savefig(os.path.join(figures_dir, f'data_{cc}.png'))
                plt.close()

                figlist.append("\n\\includegraphics[width=0.8\\textwidth]{Figures/data_%d.png}\n"%cc)

            waveforms_out = []
            spectra_out = []
            for i in range(4):
                if not self.nowave:
                    if len(waveforms[i])>cc:
                        waveforms_out.append(waveforms[i][cc])
                if i in sp:
                    sp[i]._read()
                    spectra_out.append(sp[i].data)
            results_list.append(list(self.todo_list[cc])+[waveforms_out, spectra_out])


            if ch>=0:
                chlist = [ch]
            else:
                chlist = [0,1,2,3]

            def freq_to_bin(freq):
                bin = int(freq/0.025+1e-3)
                if bin>2048:
                    bin = 2048-bin
                return bin

            for ich in chlist:
                cfreq = freq_set[ich]
                key = (ich,g,cfreq)
                # now we need to isolate the power
                bin = freq_to_bin(cfreq)

                if key not in power_out:
                    power_out[key] = []
                    power_in[key] = []

                sppow = sp[ch].data* (2**(bitslic[ch]-31))
                
                #print (cfreq,sppow[bin-1],sppow[bin],sppow[bin+1])

                power_out[key].append(sppow[bin])
                ## we have /2 to get from Vpp to amplitude, *1000 to get from mV to V, *1e-4 to account for 40dB attenuation, 
                ## *(1e9)**2 to get from V^2 to nV^2, /25e3 to get from 25kHz bandwidth to get to nV^2/Hz
                ## here we also apply the correction factor since the power measure at the bin center will be in effect this number
                power_in[key].append((ampl_set[ich]/2/1000)**2*(attenuation_fact**2) * self.corr_fact *(1e9)**2 /25e3)
                #print ('here',ch, ampl_set, power_in[key][-1], power_out[key][-1])
                if ampl_set[ich] == 0:
                    if (ich,g) not in power_zero:
                        power_zero[(ich,g)] = []
                        power_zero_terminated[(ich,g)] = []
                    power_zero[(ich,g)].append(sppow)
                    if Cterminated is not None and (not (self.terminated and self.nowave)):
                        sppow_terminated = sp_terminated[ch].data* (2**(bitslic[ch]-31))   
                        power_zero_terminated[(ich,g)].append(sppow_terminated)

        if (self.terminated and self.nowave and self.terminated_set):
            for i,g in enumerate(self.gains):
                for ch in range(4):
                    sppow_terminated = Cterminated.spectra[i][ch].data * (2**(self.bitslices[-1]-31))
                    key = (ch,g,0)


        pickle.dump(results_list, open(os.path.join(figures_dir, '../../data.pickle'), 'wb'))
        self.results['data_plots'] = "".join(figlist)

        if self.slow:
            for key in power_in:
                (ch,g,cfreq) = key
                bin = freq_to_bin(cfreq)
                power_in[key].append(0)
                power_out[key].append(power_zero[(ch,g)][0][bin])


        print ('... plotting telemetry ...')

        self.plot_telemetry(C.spectra, figures_dir, figures_dir+"/../../telemetry.txt")
        if Cterminated is not None:
            self.plot_telemetry(Cterminated.spectra, None, figures_dir+"/../../telemetry_terminated.txt")


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
            if f==0:
                continue
            fi = self.freqs.index(f)
            #print (key, power_out[key], power_in[key])
            if np.any(np.array(power_out[key])==0):
                if (not self.terminated): 
                    print (f"WARNING: Zero power detected for {key}. Skipping.")
                offset, slope = 0,0
            else:
                try:
                    slope, offset = np.polyfit(power_in[key],power_out[key],1, w = 1/np.sqrt(power_out[key]))
                except:
                    print (f"WARNING: Error in fitting {key}. Skipping.")
                    print ('In power', power_in[key])
                    print ('Out power', power_out[key])
                    offset, slope = 0,0
            #print (key, slope, offset, power_zero[key])
            power_zero_fit[key] = offset
            conversion[key] = slope
            ax[fi][gain_ndx[g]].plot(power_in[key], power_out[key], 'o', color=clr[ch])
            ax[fi][gain_ndx[g]].plot(power_in[key], np.array(power_in[key])*slope+offset,'-', color=clr[ch])
            ax[fi][0].set_ylabel(f"{f} MHz")
            #ax[fi][c-1].set_yscale('log')
            #ax[fi][c-1].set_xscale('log')
        ax[0][0].set_title('L Gain')
        ax[0][1].set_title('M Gain')
        ax[0][2].set_title('H Gain')
        fig.savefig(os.path.join(figures_dir, 'power_fits.pdf'))

        print ("... plotting gain / noise curves...")
        figlist_res = []
        if -1 in self.channels:
            chlist = [0,1,2,3]
        else:
            chlist = self.channels

        if not self.terminated:
            noise_table = "Table of power with and without PF noise in nV/rtHz, mean 250kHz to 51MHz:\n\n" 
        else:
            noise_table = "Table of noise in arbitrary units normalized to be $\\approx$ 100 if evertyhing is OK:\n\n"
        noise_table += " \\begin{tabular}{|c|"+"c|c|"*len(self.gains)+"}\n"
        noise_table += "\\hline\n"
        noise_table += "Channel " + " ".join([" & \\multicolumn{2}{|c|}{"+str(g)+"}" for g in self.gains])+"\\\\\n"
        noise_table += "\\hline\n"
        gain_out = [self.freqs]
        noise_out = []
        noise_out_sans_pf = []
        for ch in chlist:
            noise_table += f"{ch} "
            for g in self.gains:
                pzero_fit = np.array([power_zero_fit[(ch,g,f)] for f in self.freqs])
                conv = np.array([conversion[(ch,g,f)] for f in self.freqs])
                gain_out.append(conv)
                conv_fit = interp1d(self.freqs, conv, kind='linear', fill_value='extrapolate')
                fig, ax = plt.subplots(1,2, figsize=(12,6))
                ffreq=np.arange(2048)*0.025
                pzero = np.array(power_zero_terminated[(ch,g)]) if Cterminated is not None else np.array(power_zero[(ch,g)])
                np.savetxt(figures_dir+f'/../../power_zero_{g}_{ch}.dat', pzero)
                pzero = pzero.mean(axis=0)
                self.freqs=np.array(self.freqs)           
                if not self.terminated: 
                    noise_power = pzero/conv_fit(ffreq) 
                else:
                    noise_norm = {'L':9.0e-4, 'M':5.7e-3, 'H':4.0e-2}
                    noise_power = pzero/noise_norm[g]**2
                #noise_power[::8]=0
                ax[0].plot(ffreq,np.sqrt(noise_power) , 'b-')
                ax[0].plot(self.freqs[self.freqs<51.2], np.sqrt(pzero_fit/conv)[self.freqs<51.2],'ro' )
                ax[1].plot(ffreq,conv_fit(ffreq), 'b-')
                ax[1].plot(self.freqs, conv, 'ro')
                ax[0].set_yscale('log')
                ax[1].set_yscale('log')
                ax[0].set_xlabel('Frequency [MHz]')
                ax[0].set_ylabel('Noise [nV/sqrt(Hz)]')
                ax[1].set_xlabel('Frequency [MHz]')
                ax[1].set_ylabel('Conversion [SDU/(nV^2/Hz)]')
                
                ## 10 to -8 is 250kHZ to 51MHz
                avg_rms = np.sqrt(noise_power[10:-8].mean())
                # sans PF
                noise_power_sans_pf = np.copy(noise_power)
                noise_power_sans_pf [::8] = np.nan
                avg_rms_sans_pf = np.sqrt(np.nanmean(noise_power_sans_pf[10:-8]))
                noise_table += f" & {avg_rms:.2f} & {avg_rms_sans_pf:.2f}"
                noise_out.append(avg_rms)
                noise_out_sans_pf.append(avg_rms_sans_pf)

                if len(self.terminated_set)>0 and ((avg_rms_sans_pf>5) or np.isnan(avg_rms_sans_pf)):
                    passed = False 
                elif self.terminated:
                    if (avg_rms_sans_pf<75) or (avg_rms_sans_pf>125):
                        passed = False
                #y axis, left plot
                yl,yh = ax[0].get_ylim()
                if yl<20:
                    ## we are in the right ballpark
                    yl = 1
                    yh = 100
                ax[0].set_ylim(yl,yh)
                
                #y axis, right plot
                yl,yh = ax[1].get_ylim()
                if yl/yh<1e-2:
                    yl = yh/1e2
                ax[1].set_ylim(yl,yh)
                
                
                fig.suptitle(f"Channel {ch} Gain {g}")
                fig.savefig(os.path.join(figures_dir, f'results_pk_{ch}_{g}.png'))
                figlist_res.append("\n\\includegraphics[width=1.0\\textwidth]{Figures/results_pk_"+f"{ch}_{g}"+".png}\n")
            noise_table += "\\\\\n"
        noise_table += "\\hline\n"
        noise_table += "\\end{tabular}\n"
        self.results['noise_table'] = noise_table    
#                for f in self.freqs:
#                    key = (ch,g,f)
#                    if key not in power_zero_fit:
#                        power_zero_fit[key] = 0
#                        conversion[key] = 0
        
        gain_out = np.array(gain_out)
        np.savetxt(figures_dir+'/../../gain.dat', gain_out.T, fmt='%.6e', delimiter='\t', header='freq\tL0\tL1\tL2\tL3\tM0\tM1\tM2\tM3\tH0\tH1\tH2\tH3', comments='')

        noise_out = np.array(noise_out).reshape(len(chlist), len(self.gains))
        noise_out_sans_pf = np.array(noise_out_sans_pf).reshape(len(chlist), len(self.gains))
        np.savetxt(figures_dir+'/../../noise.dat', noise_out.T, fmt='%.6e', delimiter='\t', header='ch0 ch1 ch2 ch3', comments='')
        np.savetxt(figures_dir+'/../../noise_sans_pf.dat', noise_out_sans_pf.T, fmt='%.6e', delimiter='\t', header='ch0 ch1 ch2 ch3', comments='')

        # time domain simple analysis
        figlist_res_real = []
        v2adu_emi = {'L':5.37E-02,	'M':8.07E-03,	'H':1.22E-03}
        print (len(waveforms[0]),len(waveforms[1]))
        if not self.nowave:
            for g in self.gains:
                fig, ax = plt.subplots(1,1, figsize=(12,6))
                for ch in chlist:
                    rat = []
                    for f in self.freqs:
                        ampl_max =0                    
                        for cc,(_g, ch_, freq_set_, ampl_set_, bitslic_) in enumerate(self.todo_list):
                            if ch_ == ch and _g == g and freq_set_[ch] == f and ampl_set_[ch]>ampl_max:
                                ampl_max = ampl_set_[ch]
                                cc_max = cc
                        wform = waveforms[ch][cc_max]
                        adu_range = wform.max()-wform.min()
                        Vpp = ampl_max*1e-3*attenuation_fact #1e-3 for mV to V, 1e-2 for 40dB power attenuation
                        rat.append(Vpp/adu_range*1e4)
                    ax.plot(self.freqs, rat, label=f'Channel {ch}')
                    ax.axhline(v2adu_emi[g], color='r', linestyle='--')
                ax.set_xlabel('Frequency [MHz]')
                ax.set_ylabel('Amplitude @ 10kADU')
                plt.title(f'V2ADU at gain {g}')
                fig.savefig(os.path.join(figures_dir, f'v2adu_{g}.png'))
                figlist_res_real.append("\n\\includegraphics[width=1.0\\textwidth]{Figures/v2adu_"+f"{g}"+".png}\n")


        self.results['ps_results'] = "".join(figlist_res)
        self.results['real_results'] = "".join(figlist_res_real)
        self.results['result'] = int(passed)
