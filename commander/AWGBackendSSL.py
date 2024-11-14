#
# Generic interface for the AWG backends
#
import KS33500 as KS

from AWGBackendBase import AWGBackendBase

class AWGBackendSSL(AWGBackendBase):
    def __init__ (self):
        if KS.pyvisa is None:
            raise ValueError("pyvisa not installed, can't use AWG")
        ip_address_12 = '192.168.0.132'
        ip_address_34 = '192.168.0.133'
        

        self.ks1, self.ks2 = KS.KS33500(ip_address_12),KS.KS33500(ip_address_34)
        ##mapping
        self.ch2awg = [ (self.ks2,0), (self.ks2,1), (self.ks1,1), (self.ks1,0)]

        for ks in [self.ks1, self.ks2]:
            ks.init_33500()
            for ch in range(2):
                ks.set_function(ch+1, 'SIN')                
                ks.output_off(ch+1)

        #self.coonection ()

    def tone (self, ch, frequency, amplitude):
        if ch<4:
            ks,awg_ch = self.ch2awg[ch]
            if amplitude>0:
                ks.set_frequency(awg_ch+1, str(frequency)+" mhz")
                ks.set_amplitude(awg_ch+1, str(amplitude)+" mvpp")
                ks.output_on(awg_ch+1)
            else:
                ks.output_off(awg_ch+1)    
        else:
            return
            
        
    def stop(self):
        for ks in [self.ks1, self.ks2]:
            for ch in range(2):
                ks.output_off(ch)        
