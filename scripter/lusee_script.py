# LuSEE script module

import lusee_commands as lc


class Scripter:

    def __init__ (self):
        self.script = []
        self.default_dt = 0.1


    def write_script(self, name):
        fname = "scripts/"+name+".scr"
        open(fname,'w').writelines(self.script)

    def add_reset(self):
        self.script.append(f"{self.default_dt:5.1f} reset\n")
    
    def add_save(self,name):
        self.script.append(f"{self.default_dt:5.1f} save {name}\n")

    def add_command(self, cmd, arg, dt=None):
        if dt is None:
            dt = self.default_dt
        self.script.append(f"{dt:5.1f} CMD {cmd:02x} {arg:04x} \n")


    def add_spectrometer_command(self,cmd,arg,dt=None):
        assert(arg<256)
        assert(cmd<256)
        self.add_command(0x10,(cmd<<8)+arg,dt)     
           
    def add_route(self, ch, plus, minus=None, dt=None):
        assert ((ch>=0) and (ch<4))
        cmd = lc.RFS_SET_ROUTE_SET1+ch
        if minus is None:
            minus = 4
        if plus is None:
            plus = 4
        print ("route", plus, minus,ch)
        arg = (minus<<3)+plus
        self.add_spectrometer_command(cmd, arg, dt)

    def add_ana_gain(self, gains, dt=None):
        assert(len(gains)==4)
        cmd = lc.RFS_SET_GAIN_ANA_SET
        arg = 0
        for c in gains[::-1]:
            assert c in "LMHA"
            arg = (arg<<2)+"LMHA".index(c)
        self.add_spectrometer_command(cmd, arg, dt)

    def add_range_adc(self, dt=None):
        cmd = lc.RFS_SET_RANGE_ADC
        arg = 0
        self.add_spectrometer_command(cmd, arg, dt)

    def add_start(self,dt=None):
        cmd = lc.RFS_SET_START
        arg = 0
        self.add_spectrometer_command(cmd, arg, dt)
        
    def add_stop(self,dt=None):
        cmd = lc.RFS_SET_STOP
        arg = 0
        self.add_spectrometer_command(cmd, arg, dt)
    

    