import sys, os
# LuSEE script module

if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

# now try to import pycoreloop
try:
    from pycoreloop import command as lc
    from pycoreloop import command_from_value, value_from_command
except ImportError:
    print ("Can't import pycoreloop\n")
    print ("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo. [lusee_script.py]")
    sys.exit(1)



class Scripter:

    def __init__ (self):
        self.script = []
        self.total_time = 0

    def command(self, cmd, arg):
        self.total_time += 0.01 ## assume 10ms for a real command, already overestimated
        assert (cmd>=0 & cmd < 256)
        assert (arg>=0 & arg < 65536)
        self.script.append((cmd,arg))


    def spectrometer_command(self,cmd,arg):
        assert(arg<256)
        assert(cmd<256)
        self.command(0x10,(cmd<<8)+arg)     

    def wait (self, dt):
        """ Wait for dt in seconds, rounted to 100ms"""
        if dt<0.1:
            print ("Warning: wait time too short")
        elif dt>6553.6:
            print ("Warning: wait time too long, rounding down")
            dt = 6553.6
        dt = int(dt*10)
        self.total_time += dt/10
        self.command(lc.CTRL_WAIT,dt)

    def reset(self, stored_state = 'ignore'):
        if stored_state == 'load':
            arg_low = 0
        elif stored_state == 'ignore':
            arg_low = 1
        elif stored_state == 'delete_all':
            arg_low = 2
        else:
            raise ValueError("Unknown stored_state")
        self.spectrometer_command(lc.RFS_SET_RESET,arg_low)
        

    def ADC_special_mode (self, mode='normal'):
        print (mode)
        assert(mode in ['normal', 'ramp','zeros', 'ones'])
        arg = ['normal', 'ramp','zeros', 'ones'].index(mode)
        self.spectrometer_command(lc.RFS_SET_ADC_SPECIAL, arg)

    def house_keeping(self, req_type):
        assert(req_type<2)
        self.spectrometer_command(lc.RFS_SET_HK_REQ, req_type)

    def section_break(self):
        self.spectrometer_command(lc.RFS_SET_HK_REQ, 99)

    def adc_range(self):
        self.spectrometer_command(lc.RFS_SET_RANGE_ADC, 0x0)
        
    def route(self, ch, plus, minus=None, gain='M'):
        assert ((ch >= 0) and (ch < 4))
        cmd = lc.RFS_SET_ROUTE_SET1 + ch
        if minus is None:
            minus = 4
        if plus is None:
            plus = 4
        print("route", plus, minus, gain, ch)
        assert (gain in "LMHD")
        gain = "LMHD".index(gain)
        arg = (gain << 6) + (minus << 3) + plus
        self.spectrometer_command(cmd, arg)
        
    def ana_gain(self, gains):
        assert(len(gains) == 4)
        cmd = lc.RFS_SET_GAIN_ANA_SET
        arg = 0
        for c in gains[::-1]:
            assert c in "LMHA"
            arg = (arg << 2) + "LMHA".index(c)
        self.spectrometer_command(cmd, arg)
        
    def waveform(self, ch):
        arg = ch
        self.spectrometer_command(lc.RFS_SET_WAVEFORM, arg)
        
    def disable_ADC(self, bitmask=None):
        if bitmask is None:
            bitmask = 0b1111
        self.spectrometer_command(lc.RFS_SET_DISABLE_ADC, bitmask)
            
    def set_bitslice(self, ch, value):
        assert (value < 32)
        if ch < 8:
            cmd = lc.RFS_SET_BITSLICE_LOW 
        else:
            cmd = lc.RFS_SET_BITSLICE_HIGH
            ch -= 8
            
        arg = ch + (value << 3)
        self.spectrometer_command(cmd, arg)
        
    def set_bitslice_auto(self, keep_bits):
        cmd = lc.RFS_SET_BITSLICE_AUTO
        if keep_bits == False:
            keep_bits = 0
        arg = keep_bits
        self.spectrometer_command(cmd, arg)
        
    def range_ADC(self):
        cmd = lc.RFS_SET_RANGE_ADC
        arg = 0
        self.spectrometer_command(cmd, arg)
        
    def select_products(self, mask):
        assert(type(mask) == int)
        low = (mask & 0x00FF)
        high = ((mask & 0xFF00) >> 8)
        self.spectrometer_command(lc.RFS_SET_PRODMASK_LOW, low)
        self.spectrometer_command(lc.RFS_SET_PRODMASK_HIGH, high)
        
    def set_Navg(self, Navg1, Navg2):
        val = Navg1 + (Navg2 << 4)
        self.spectrometer_command(lc.RFS_SET_AVG_SET, val)
        
    def start(self):
        cmd = lc.RFS_SET_START
        arg = 0
        self.spectrometer_command(cmd, arg)
        
    def stop(self):
        cmd = lc.RFS_SET_STOP
        arg = 0
        self.spectrometer_command(cmd, arg)           

