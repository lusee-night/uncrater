#
# Generic interface for the AWG backends
#
try:
    import pyvisa
except:
    print ("Warning: pyvisa not installed. You won't be able to use the AWG.")
    pyvisa = None

from AWGBackendBase import AWGBackendBase
from VWDriver import VWDriver

class AWGBackendLab7(AWGBackendBase):
    def __init__ (self, channel = 3):
        if pyvisa is None:
            raise ValueError("pyvisa not installed, can't use AWG")
        resource = "USB0::1689::834::C010077::0::INSTR"
        self.rm = pyvisa.ResourceManager('@py')
        self.inst = self.rm.open_resource(resource)
        self.inst.write('OUTP1:STAT OFF')
        self.channel = channel
        print ("Initialized AWG backend for lab7, will respond to request for channel", self.channel)
        self.calibrator = VWDriver()

    
    def tone (self, ch, frequency, amplitude):
        # ch is 0-4
        # freq is in MHz
        # amplitude is in mVPP
        if ch==self.channel-1: ## ch==3 is what we have working in the lab
            if amplitude > 0:
                self.inst.write(f'SOUR1:FREQ {frequency} mhz')
                print (f'SOUR1:VOLT {amplitude:5.2f} mvpp')
                self.inst.write(f'SOUR1:VOLT {amplitude:5.2f} mvpp')
                self.inst.write('OUTP1:STAT ON')
            else:
                self.inst.write(f'SOUR1:FREQ 80 mhz') ## let's put it out of band
                self.inst.write('OUTP1:STAT OFF')
        
    def cal_on (self, alpha):
        range_correction = alpha * 2.998e8 * 1e3 ## convert to mm/s 
        print ("Applying range correction", range_correction)
        self.calibrator.enable_PA(range_correction)
    
    def cal_off (self):
        self.calibrator.disable_PA()
        
    def stop(self):
        self.inst.write('OUTP1:STAT OFF')
        del self.calibrator



    

