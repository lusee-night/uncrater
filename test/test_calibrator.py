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
        "slow": False,
        "Nac1": 6,
        "Nac2": 7,
        "slicer": "15.17.21.15.18.1.0",
        "snr_on": 5,
        "snr_off": 1,
        "Nnotch": 4,
        "corA": 1,
        "corB": 10
    } ## dictinary of options for the test
    options_help = {
        "mode" : "manual",
        "slow": "Run the test in slow mode for SSL",
        "slicer": "Slicer configuration in the format powertop.sum1.sum2.prod1.prod2.delta_powerbot.sd2_slice",
        "snr_on": "SNR on value for calibration",
        "snr_off": "SNR off value for calibration",
        "Nac1": "First Nac value for calibration (5=32)",
        "Nac2": "Second Nac value for calibration (5=32)",
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
    
        S.enable_heartbeat(False)
        S.set_Navg(14,4)

        ### Main spectral engine
        
        S.set_ana_gain('HHHH')
        for i in range(4):        
            S.set_route(i, None, i)
        
        
        S.set_bitslice(0,10)
        for i in range(1,4):
            S.set_bitslice(i,19)    
        

        S.cal_set_avg(self.Nac1,self.Nac2)
        S.set_notch(self.Nnotch,disable_subtract=True)
        S.cal_set_drift_step(10)
        S.select_products(0b1111)

        S.cal_set_pfb_bin(1522)
        #S.cal_antenna_enable(0b1110) # disable antenna 0
        S.cal_antenna_enable(0b1110)
        slicer = [int(x) for x in self.slicer.split('.')]
        S.cal_set_slicer(auto=False, powertop=slicer[0], sum1=slicer[1], sum2=slicer[2], prod1=slicer[3], prod2=slicer[4], delta_powerbot=slicer[5], sd2_slice=slicer[6])

        #S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_SNR_SETTLE)  
        S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_RUN)  
        #S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_RAW2)  


        
        fstart = 17.4
        fend = +17.0
        
        
        
        
        
    
        S.cal_SNRonff(self.snr_on,self.snr_off)

        S.cal_set_corrAB(self.corA,self.corB)
        S.cal_set_ddrift_guard(1500)
        S.cal_set_gphase_guard(250000)


        if False:
            sig, noise = np.loadtxt("session_calib_weights_Mar25/calib_weights.dat").T
            #weights = (sig/(noise)**1.5)
            #weights /= weights.max()
            #weights[weights<0.2]=0
            weights = np.zeros(512)
            weights[90:400] = 1.0
            S.cal_set_weights(weights)
            S.cal_weights_save(1)
        else:
            S.cal_weights_load(1)
        

        
        S.start()
        S.cdi_wait_seconds(126)
        S.stop()
        S.request_eos()
        
        S.awg_cal_off()
        S.wait(41)
        S.awg_cal_on(fstart)
        #S.wait(41)
        
        
        
        #S.wait(100)
        #for d in np.linspace(fstart,fend,1300):
        #    if cal_on:
        #        S.awg_cal_on(d)
        #    S.wait(0.3)
        #S.wait(100)                
        S.wait_eos()
        S.awg_cal_off()
        return S



    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)
        self.get_versions(C)


        self.results['result'] = int(passed)
        NNotch = (1<<self.Nnotch)
        Nac1 = (1<<self.Nac1)
        Nac2 = (1<<self.Nac2)
        
        alpha_to_pdrift = 50e3*4096*NNotch/102.4e6*2*np.pi*1e-6
        
        time = np.arange(len(C.cd_drift))*NNotch*Nac1*4096/102.4e6
        plt.plot(time,C.cd_drift/alpha_to_pdrift)
        avg_drift = np.convolve(C.cd_drift/alpha_to_pdrift, np.ones(200)/200, mode='valid')
        avg_time = time[:len(avg_drift)]
        plt.plot(avg_time, avg_drift,'r-')
        plt.xlabel('Time [s]')  
        plt.ylabel('Relative drift [ppm]')
        plt.savefig(os.path.join(figures_dir,'drift.pdf'))
        plt.close()

        x = C.cd_drift[200:]/np.pi*(1<<30)#/alpha_to_pdrift
        d = x[1:]-x[:-1]

        plt.hist(d,bins=101,range=(-2000,+2000))
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

        plt.imshow(C.calib_gphase[0:,:Nac1],aspect='auto', interpolation='nearest')
        plt.colorbar()
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
        plt.legend()
        for i in range(5):
            plt.axhline(i, color='black', linestyle='--')
        plt.savefig(os.path.join(figures_dir,'lock.pdf'))
        plt.close()

        _,wf = np.loadtxt("calibrator_231001.txt").T
        wf = np.fft.rfft(np.hstack((wf,wf)))
        wf = wf[2::4]

        kcomb = np.arange(512)*4+2

        def phase_up (first, second):
            """ Phases up second waveform to the first one """
            Nfft= len(first)*1024
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
            calib_data_wf = []
            for ch in range(4):
                first = np.zeros(512,dtype=complex)
                for second in C.calib_data[1:,ch,:]:
                    second_phased = phase_up(wf,second)
                    first += second_phased
                    #plt.plot(np.angle(first[20:]/second_phased[20:]))
                    #plt.plot(second_phased[20:])
                    #stop()
                calib_data_wf.append(first)
            calib_data_wf = np.array(calib_data_wf)
            return calib_data, calib_data_wf

        calib_data, calib_data_wf = coherent_addition(C)

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
        
        plt.figure(figsize=(15,10))
        tfreq=0.5+0.1*np.arange(512)
        for ch in range(0,4):
            da = np.abs(calib_data_wf[ch,2:]**2)
            plt.plot(tfreq[2:],da,ls='-',label='CH'+str(ch)+" total")

        plt.legend()
        plt.xlabel('tone freq [MHz]')
        plt.ylabel('tone power [arbitrary units]')
        plt.semilogy()
        plt.savefig(os.path.join(figures_dir,'result.pdf'))
        plt.close()
