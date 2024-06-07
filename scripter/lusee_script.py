# LuSEE script module

import lusee_commands as lc


class Scripter:

    def __init__ (self):
        self.script = []
        self.default_dt = 0.1


    def write_script(self, name):
        fname = "scripts/"+name+".scr"
        open(fname,'w').writelines(self.script)

    def reset(self,dt=None):
        if dt is None:
            dt=self.default_dt

        self.script.append(f"{dt:5.1f} reset\n")
    
    def save(self,name,dt=None):
        if dt is None:
            dt=self.default_dt
        self.script.append(f"{dt:5.1f} save {name}\n")

    def exit(self,dt=None):
        if dt is None:
            dt=self.default_dt
        self.script.append(f"{dt:5.1f} exit\n")

    def command(self, cmd, arg, dt=None):
        if dt is None:
            dt = self.default_dt
        self.script.append(f"{dt:5.1f} CMD {cmd:02x} {arg:04x} \n")


    def spectrometer_command(self,cmd,arg,dt=None):
        assert(arg<256)
        assert(cmd<256)
        self.command(0x10,(cmd<<8)+arg,dt)     
           
    def adc_range(self,dt=None):
        self.spectrometer_command(lc.RFS_SET_RANGE_ADC,0x0, dt)
        
    def route(self, ch, plus, minus=None, gain = 'M', dt=None):
        assert ((ch>=0) and (ch<4))
        cmd = lc.RFS_SET_ROUTE_SET1+ch
        if minus is None:
            minus = 4
        if plus is None:
            plus = 4
        print ("route", plus, minus, gain, ch)
        assert (gain in "LMHD")
        gain = "LMHD".index(gain)
        arg = (gain<<6) + (minus<<3)+plus
        self.spectrometer_command(cmd, arg, dt)

    def ana_gain(self, gains, dt=None):
        assert(len(gains)==4)
        cmd = lc.RFS_SET_GAIN_ANA_SET
        arg = 0
        for c in gains[::-1]:
            assert c in "LMHA"
            arg = (arg<<2)+"LMHA".index(c)
        self.spectrometer_command(cmd, arg, dt)
        
    def waveform(self,ch,dt=None):
        arg = ch
        self.spectrometer_command(lc.RFS_SET_WAVEFORM,arg,dt)
        
    def disable_ADC(self, bitmask=None, dt=None):
        if bitmask is None:
            bitmask = 0b1111
        self.spectrometer_command(lc.RFS_SET_DISABLE_ADC,bitmask)
            
    def set_bitslice (self, ch, value, dt=None):
        assert (value<32)
        if ch<8:
            cmd = lc.RFS_SET_BITSLICE_LOW 
        else:
            cmd = lc.RFS_SET_BITSLICE_HIGH
            ch-=8
            
        arg = ch+(value << 3)
        self.spectrometer_command(cmd, arg, dt = dt)
        
    def set_bitslice_auto (self, keep_bits, dt = None):
        cmd = lc.RFS_SET_BITSLICE_AUTO
        if keep_bits == False:
            keep_bits = 0
        arg = keep_bits
        self.spectrometer_command(cmd, arg, dt= dt)

    def range_ADC(self, dt=None):
        cmd = lc.RFS_SET_RANGE_ADC
        arg = 0
        self.spectrometer_command(cmd, arg, dt)

    def select_products(self, mask, dt=None):
        assert(type(mask)==int) ## can support other way as well.
        low = (mask & 0x00FF)
        high = ((mask & 0xFF00) >> 8)
        self.spectrometer_command  (lc.RFS_SET_PRODMASK_LOW, low, dt=dt)    
        self.spectrometer_command  (lc.RFS_SET_PRODMASK_HIGH, high, dt=0)
        
    def set_Navg(self,Navg1,Navg2,dt=None):
        val = Navg1+(Navg2<<4)
        self.spectrometer_command(lc.RFS_SET_AVG_SET, val)

    def start(self,dt=None):
        cmd = lc.RFS_SET_START
        arg = 0
        self.spectrometer_command(cmd, arg, dt)
        
    def stop(self,dt=None):
        cmd = lc.RFS_SET_STOP
        arg = 0
        self.spectrometer_command(cmd, arg, dt)
    

    