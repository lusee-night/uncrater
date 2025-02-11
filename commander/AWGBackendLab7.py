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
    def __init__ (self, channels = [1,3]):
        if pyvisa is None:
            raise ValueError("pyvisa not installed, can't use AWG")
        #resource = "USB0::1689::834::C010077::0::INSTR"
        # Tektronix two channels
        resource = 'USB0::0x0699::0x0356::C020364::INSTR'
        self.rm = pyvisa.ResourceManager('@py')
        try:
            self.inst = self.rm.open_resource(resource)
        except:
            print ("Error: could not open AWG resource", resource)
            self.inst=None
        if self.inst is not None:
            self.inst.write('OUTP1:STAT OFF')
            self.inst.write('OUTP2:STAT OFF')
            self.channel = channels
            
            print ("Initialized AWG backend for lab7, will respond to request for channel", self.channel)
        #try:
        #self.calibrator = VWDriver()
        #print ("Initialized WV EM Calibrator")
        #except:
        #    self.calibrator=None


    
    def tone (self, ch, frequency, amplitude):
        # ch is 0-4
        # freq is in MHz
        # amplitude is in mVPP
        if ch in self.channel: 
            sour = self.channel.index(ch)+1

            if amplitude > 0:
                self.inst.write(f'SOUR{sour}:FREQ {frequency} mhz')
                print (f'SOUR{sour}:VOLT {amplitude:5.2f} mvpp')
                self.inst.write(f'SOUR{sour}:VOLT {amplitude:5.2f} mvpp')
                self.inst.write(f'OUTP{sour}:STAT ON')
            else:
                self.inst.write(f'SOUR{sour}:FREQ 80 mhz') ## let's put it out of band
                self.inst.write(f'OUTP{sour}:STAT OFF')
        
    def cal_on (self, alpha):
        range_correction = round((alpha * 1e-6) *  2.998e8 * 1e3) ## convert to mm/s 
        print ("Applying range correction", range_correction)
        self.calibrator.enable_PA(range_correction)
    
    def cal_off (self):
        self.calibrator.disable_PA()
        
    def stop(self):
        if self.inst is not None:
            self.inst.write('OUTP1:STAT OFF')
            self.inst.write('OUTP2:STAT OFF')
        #del self.calibrator



    

