import binascii
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
        "mode": "manual",
        "mins": 4,
        "slow": True,
        "gain": "LLLL",
        "antenna_mask": 0b1111,
        "Nac1": 6,
        "Nac2": 8,
        "weights_set": 6,
        #"slicer": "15.19.21.15.18.1.6.0",
        "slicer": "24.25.27.15.18.1.12.0",
        "notch_detector": False,
        "snr_on": 5.0,
        "snr_off": 1.0,
        "Nnotch": 4,
        "corA": 0.0,
        "corB": 0.0
    } ## dictinary of options for the test
    options_help = {
        "mode" : "full = everything with autoslicer and autosnr, run= just run",
        "mins": "Number of minutes to run the test",
        "slow": "Run the test in slow mode for SSL",
        "gain": "Analog gain settings",
        "antenna_mask": "Antenna mask to enable antennas (bits 0-3 for ch 0-3)",
        "slicer": "Slicer configuration in the format powertop.sum1.sum2.prod1.prod2.delta_powerbot.fd_slice,sd2_slice",
        "notch_detector": "Enable notch detector",
        "snr_on": "SNR on value for calibration",
        "snr_off": "SNR off value for calibration",
        "Nac1": "First Nac value for calibration (5=32)",
        "Nac2": "Second Nac value for calibration (5=32)",
        "weights_set": "Weights set for calibration (0-8)",
        "Nnotch": "Notch value for calibration",
        "corA": "corA value for calibration",
        "corB": "corB value for calibration"
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """

        S = Scripter()
            
        S.wait(1)
        S.reset()
        S.wait(3)

        if self.slow:
            S.set_dispatch_delay(120)
    
        S.set_Navg(14,7)

        ### Main spectral engine
        
        S.set_ana_gain(self.gain)
        for i in range(4):        
            S.set_route(i, None, i)
                
        S.set_bitslice(0,10)
        for i in range(1,4):
            S.set_bitslice(i,19)
        

        S.cal_set_avg(self.Nac1,self.Nac2)
        S.set_notch(self.Nnotch,disable_subtract=False)
        S.cal_set_drift_step(10)
        S.select_products('auto_only')

        S.cal_set_pfb_bin(1522)
        #S.cal_antenna_enable(0b1110) # disable antenna 0
        S.cal_antenna_enable(self.antenna_mask)
        slicer = [int(x) for x in self.slicer.split('.')]
        assert(len(slicer)==8)
        S.cal_set_slicer(auto=True, powertop=slicer[0], sum1=slicer[1], sum2=slicer[2], prod1=slicer[3], prod2=slicer[4], delta_powerbot=slicer[5], fd_slice=slicer[6], sd2_slice=slicer[7])



        S.cal_weights_load(self.weights_set)

        S.cal_set_corrAB(self.corA,self.corB)
        S.cal_set_drift_guard(120*(self.Nnotch-3)) # (120 at 4, 240, at 5,etc)
        S.cal_set_ddrift_guard(1500)
        S.cal_set_gphase_guard(250000)
        S.cal_SNRonff(self.snr_on,self.snr_off)

        fstart = 17.0
        fend = +16.0        

        S.cal_raw11_every(0x0) # always send raw11 data
        S.notch_detector(self.notch_detector)
        if self.mode == "full":
            S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_BIT_SLICER_SETTLE)              
            S.start()
            S.cdi_wait_minutes(self.mins)
            S.stop()
            S.request_eos()
                    
    
        elif self.mode == "run":
            S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_RUN)
            S.awg_cal_on(fstart)
            S.start()
            S.cdi_wait_minutes(self.mins)
            S.stop()
            S.request_eos()

        elif self.mode == "erc_spectra" or self.mode=='erc':
            #get spectra
            if self.mode == "erc_spectra":
                S.set_notch(self.Nnotch,disable_subtract=True, notch_detector=False)        
            else:
                S.set_notch(self.Nnotch,disable_subtract=False, notch_detector=True)        
            S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_RUN)  
            S.awg_cal_off()
            S.start()
            S.wait(80)
            S.awg_cal_on(fstart)
            S.wait(120)
            for f in np.linspace(fstart,fend,3600):
                S.awg_cal_on(f)
                S.wait(0.1)
            S.wait(120)
            S.stop()
            S.request_eos()



        elif self.mode == "spectra_only":
            S.cal_enable(enable=False)
            S.select_products('all')
            S.awg_cal_on(fstart)
            S.wait(1)
            S.set_Navg(14,5)
            
            S.set_notch(self.Nnotch,disable_subtract=True)            
            S.start()
            S.cdi_wait_spectra(1)
            S.stop()
            S.request_eos()
            S.wait_eos()

            S.set_notch(self.Nnotch,disable_subtract=False)            
            S.start()
            S.cdi_wait_spectra(1)
            S.stop()
            S.request_eos()
            S.wait_eos()

            S.set_notch(self.Nnotch,disable_subtract=False, notch_detector=True)            
            S.start()
            S.cdi_wait_spectra(1)
            S.stop()
            S.request_eos()
            

        #S.wait(100)
        #for d in np.linspace(fstart,fend,1300):
        #    if cal_on:
        #        S.awg_cal_on(d)
        #S.wait(100)       

        S.wait_eos()
        return S



    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)
        self.get_versions(C)


        
        NNotch = (1<<self.Nnotch)
        Nac1 = (1<<self.Nac1)
        Nac2 = (1<<self.Nac2)
        
        mode = [p.mode for p in C.calib_meta]
        plt.plot(mode)
        plt.xlabel('Time')
        plt.ylabel('Calibrator mode')
        plt.savefig(os.path.join(figures_dir,'mode.pdf'))
        plt.close()

        sum1_slice = [p.sum1_slice for p in C.calib_meta]
        sume2_slice = [p.sum2_slice for p in C.calib_meta]
        fd_slice = [p.fd_slice for p in C.calib_meta]
        sd2_slice = [p.sd2_slice for p in C.calib_meta]
        prod1_slice = [p.prod1_slice for p in C.calib_meta]
        prod2_slice = [p.prod2_slice for p in C.calib_meta]
        plt.plot(sum1_slice, label='sum1_slice')
        plt.plot(sume2_slice, label='sum2_slice')
        plt.plot(fd_slice, label='fd_slice')
        plt.plot(sd2_slice, label='sd2_slice')
        plt.plot(prod1_slice, label='prod1_slice')
        plt.plot(prod2_slice, label='prod2_slice')
        plt.xlabel('Time')
        plt.ylabel('Slicer settings')
        plt.legend()
        plt.savefig(os.path.join(figures_dir,'slicer_settings.pdf'))
        plt.close()

        alpha_to_pdrift = 50e3*4096*NNotch/102.4e6*2*np.pi*1e-6        
        time = np.arange(len(C.cd_drift))*NNotch*Nac1*4096/102.4e6
        phy_drift = C.cd_drift/alpha_to_pdrift
        plt.plot(time,phy_drift)
        avg_drift = np.convolve(phy_drift, np.ones(200)/200, mode='valid')
        avg_time = time[:len(avg_drift)]
        plt.plot(avg_time, avg_drift,'r-')
        plt.xlabel('Time [s]')  
        plt.ylabel('Relative drift [ppm]')
        plt.savefig(os.path.join(figures_dir,'drift.pdf'))
        plt.close()

        x = C.cd_drift[200:]/np.pi*(1<<30)#/alpha_to_pdrift
        d = x[1:]-x[:-1]

        plt.hist(d,bins=101,range=(-2000,+2000))
        plt.xlabel('Delta drift ')
        plt.ylabel('Counts')
        plt.savefig(os.path.join(figures_dir,'delta_drift.pdf'))
        plt.close() 

        fig, ax = plt.subplots(5,2,figsize=(10,10))
        ax[0,0].plot(C.cd_fd0[50:])
        ax[1,0].plot(C.cd_fd1[50:])
        ax[2,0].plot(C.cd_fd2[50:])
        ax[3,0].plot(C.cd_fd3[50:])
        ax[4,0].plot(C.cd_fdx[50:])
        ax[0,1].plot(C.cd_sd0[50:])
        ax[1,1].plot(C.cd_sd1[50:])
        ax[2,1].plot(C.cd_sd2[50:])
        ax[3,1].plot(C.cd_sd3[50:])
        ax[4,1].plot(C.cd_sdx[50:])
        fig.suptitle('FD 0123X, SD0123X', fontsize=16)
        plt.savefig(os.path.join(figures_dir,'fd_sd.pdf'))
        plt.close()

        
        fig, ax = plt.subplots(4,3,figsize=(13,10))
        ax[0,0].plot(C.cd_powertop0)
        ax[1,0].plot(C.cd_powertop1)
        ax[2,0].plot(C.cd_powertop2)
        ax[3,0].plot(C.cd_powertop3)

        ax[0,1].plot(C.cd_powerbot0)
        ax[1,1].plot(C.cd_powerbot1)
        ax[2,1].plot(C.cd_powerbot2)
        ax[3,1].plot(C.cd_powerbot3)

        ax[0,2].plot(C.cd_snr0)
        ax[1,2].plot(C.cd_snr1)
        ax[2,2].plot(C.cd_snr2)
        ax[3,2].plot(C.cd_snr3)

        fig.suptitle('Power top 0123, Power bot 0123', fontsize=16)
        plt.savefig(os.path.join(figures_dir,'snr.pdf'))
        plt.close()

        if len(C.calib_data)>2:
            plt.figure()
            plt.imshow(C.calib_gphase[0:,:Nac2],aspect='auto', interpolation='nearest')
            plt.colorbar()
        else:
            plt.figure()
            plt.text(0.1,0.5,"Not enough calibrator data packets received for gphase plot")
        
        plt.savefig(os.path.join(figures_dir,'gphase.pdf'))
        plt.close()

        fig, ax = plt.subplots(4,1,figsize=(13,10))   
        f = C.spectra[0][0].frequency
        for ch in range(4):
            s = np.mean([sp[ch].data[:] for sp in C.spectra],axis=0)
            ax[ch].plot(f,s,'b-')
            ax[ch].plot(f[2:2048:4],s[2:2048:4],'ro',markersize=3)
            ax[ch].set_yscale('log')
            ax[ch].set_ylabel('power')
        ax[3].set_xlabel('frequency [MHz]')
        fig.suptitle('Spectra', fontsize=16)
        plt.savefig(os.path.join(figures_dir,'spectra.pdf'))

        plt.close()

        plt.plot(time, C.cd_have_lock/C.cd_have_lock.max()/2, label='lock')
        for i in range(4):
            plt.plot(time, ((C.cd_lock_ant& (1<<i))>0)*0.5+(i+1), label=f'ant {i}')
        plt.xlabel('time axis')
        plt.ylabel('lock status')
        plt.legend()
        for i in range(5):
            plt.axhline(i, color='black', linestyle='--')
        plt.savefig(os.path.join(figures_dir,'lock.pdf'))
        plt.close()



        fig, ax = plt.subplots(2,2,figsize=(13,10))
        for ch in range(4):
            axi = ax[ch//2,ch%2]
            im = axi.imshow(C.cd_error_averager[:,:,ch], aspect='auto', interpolation='nearest')
            plt.colorbar(im, ax=axi)
            axi.set_title(f'averager error ch {ch}')
            axi.set_xlabel('averager error bit')
            axi.set_ylabel('time')
        fig.suptitle('Averager Error', fontsize=16)
        fig.savefig(os.path.join(figures_dir,'errors_averager.pdf'))
        
        fig, ax = plt.subplots(1,3,figsize=(13,10))
        im = ax[0].imshow(C.cd_error_phaser, aspect='auto', interpolation='nearest')
        plt.colorbar(im, ax=ax[0])
        ax[0].set_title(f'phaser error')
        ax[0].set_xlabel('phaser error bit')
        ax[0].set_ylabel('time')
        im = ax[1].imshow(C.cd_error_process, aspect='auto', interpolation='nearest')
        plt.colorbar(im, ax=ax[1])
        ax[1].set_title(f'process error')
        ax[1].set_xlabel('process error bit')
        ax[1].set_ylabel('time')
        im = ax[2].imshow(C.cd_error_stage3, aspect='auto', interpolation='nearest')
        plt.colorbar(im, ax=ax[2])
        ax[2].set_title(f'stage3 error')
        ax[2].set_xlabel('stage3 error bit')
        ax[2].set_ylabel('time')
        fig.suptitle('Error', fontsize=16)
        fig.savefig(os.path.join(figures_dir,'errors_other.pdf'))

        def phase_up (first, second):
            """ Phases up second waveform to the first one """
            Nfft= len(first)*1024
            kcomb = np.arange(512)*4+2
            cross= first*np.conj(second)
            fi = np.zeros(Nfft,complex)
            fi[kcomb] = cross
            xi = np.real(np.fft.fft(fi))
            phi = xi.argmax()*2*np.pi/len(xi)
            second_phased = np.exp(+1j*phi*kcomb)*second
            return second_phased

        def coherent_addition (C):
            calib_data = []
            for ch in range(4):
                first = np.copy(C.calib_data[-1,ch,:])
                for second in C.calib_data[-1:1:-1,ch,:]:
                    second_phased = phase_up(first,second)
                    first += second_phased
                    #plt.plot(np.angle(first[20:]/second_phased[20:]))
                    #plt.plot(second_phased[20:])
                    #stop()
                calib_data.append(first)
            calib_data = np.array(calib_data)
            return calib_data

        if len(C.calib_data)>2:
            calib_data = coherent_addition(C)


            plt.figure(figsize=(15,10))
            tfreq=0.5+0.1*np.arange(512)
            for ch in range(0,4):
                da = np.abs(calib_data[ch,2:]**2)
                plt.plot(tfreq[2:],da,ls='-',label='CH'+str(ch)+" total")

            plt.legend()
            plt.xlabel('tone freq [MHz]')
            plt.ylabel('tone power [arbitrary units]')
            plt.semilogy()
        else:
            plt.figure()
            plt.text(0.1,0.5,"Not enough calibrator data packets received for coherent addition")
        plt.savefig(os.path.join(figures_dir,'result.pdf'))
        plt.close()

        if len(C.calib_data)>2:
            fig, ax = plt.subplots(2,2,figsize=(13,10))
            for ch in range(4):
                axi = ax[ch//2,ch%2]
                im = axi.imshow(np.log(np.abs(C.calib_data[0:,ch,20:])),aspect='auto', interpolation='nearest')
                plt.colorbar(im, ax=axi)
                axi.set_title(f'calib data ch {ch}')
                axi.set_xlabel('tone index')
                axi.set_ylabel('time index')
            fig.suptitle('Calib Data', fontsize=16)
            fig.savefig(os.path.join(figures_dir,'calib_data.pdf'))
            plt.close(fig)   
        else:
            plt.figure()
            plt.text(0.1,0.5,"Not enough calibrator data packets received for calib data plot")
            plt.savefig(os.path.join(figures_dir,'calib_data.pdf'))
            plt.close()


        N = len(phy_drift)
        Nlast = N/3
        drift_std = np.std(phy_drift[int(N-Nlast):])
        have_lock_last = np.all(C.cd_have_lock[int(N-Nlast):])
        print ("Drift std:", drift_std)
        print ("Have lock last:", have_lock_last)
        passed = passed and (drift_std < 0.05)

        self.results['result'] = int(passed)
