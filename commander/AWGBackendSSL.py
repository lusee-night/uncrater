#
# Generic interface for the AWG backends
#
import KS33500 as KS

from AWGBackendBase import AWGBackendBase

class AWGBackendSSL(AWGBackendBase):
    def __init__ (self):
        if KS.pyvisa is None:
            raise ValueError("pyvisa not installed, can't use AWG")
        ip_adress_12 = '130.199.32.45'
        ip_adress_34 = '130.199.32.46'
        
        self.ks1, self.ks2 = KS.KS33500(ip_adress_12),KS.KS33500(ip_adress_34)
        
        for ks in [self.ks1, self.ks2]:
            ks.init_33500()
            for ch in range(2):
                ks.set_function(ch+1, 'SIN')                
                ks.output_off(ch+1)

    def tone (self, ch, frequency, amplitude):
        if ch in [0,1]:
            ks = self.ks1
            kch = ch
        elif ch in [2,3]:
            ks = self.ks2
            kch = ch-2
        else:
            return

        if amplitude > 0:
            # I think this should work, otherwise multilpy by 1e6
            ks.set_frequency(kch+1, frequency+" mhz")
            ks.set_amplitude(kch+1, amplitude+" mvpp")
            ks.output_on(kch+1)
        else:
            ks.output_off(kch+1)
        
    def stop(self):
        for k in [self.ks1, self.ks2]:
            for ch in range(2):
                ks.output_off(ch)        
