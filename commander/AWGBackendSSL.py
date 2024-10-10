#
# Generic interface for the AWG backends
#
import KS33500 as ks

from AWGBackendBase import AWGBackendBase

class AWGBackendSSL(AWGBackendBase):
    def __init__ (self):
        if ks.pyvisa is None:
            raise ValueError("pyvisa not installed, can't use AWG")
        self.ks = ks.KS33500()
        self.ks.init_33500()
        for ch in range(4):
            self.ks.set_function(ch+1, 'SIN')
            self.ks.output_off(ch+1)

    def tone (self, ch, frequency, amplitude):
        if amplitude > 0:
            # I think this should work, otherwise multilpy by 1e6
            self.ks.set_frequency(ch+1, frequency+" mhz")
            self.ks.set_amplitude(ch+1, amplitude+" mvpp")
            self.ks.output_on(ch+1)
        else:
            self.ks.output_off(ch+1)
        
    def stop(self):
        for ch in range(4):
            self.ks.output_off(ch)        



    

