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
        self.script.append(f"reset\n")
    
    def add_save(self,name):
        self.script.append(f"save {name}\n")

    def add_command(self, cmd, arg, dt=None):
        if dt is None:
            dt = self.default_dt
        self.script.append(f"CMD {dt:5.1f} {cmd:02x} {arg:04x} \n")

    def add_route(self, ch, plus, min=None, dt=None):
        assert ((ch>=0) and (ch<4))
        cmd = lc.RFS_SET_ROUTE_SET1+ch
        if min is None:
            min = 4
        if plus is None:
            plus = 4

        arg = (plus<<3)+min
        self.add_command(cmd, arg, dt)

    def add_ana_gain(self, gains, dt=None):
        assert(len(gains)==4)
        cmd = lc.RFS_SET_GAIN_ANA_SET
        arg = 0
        for c in gains[::-1]:
            assert c in "LMHA"
            arg+= "LMHA".index(c)
            arg = (arg<<2)
        self.add_command(cmd, arg, dt)

    def add_range_adc(self, dt=None):
        cmd = lc.RFS_SET_RANGE_ADC
        arg = 0
        self.add_command(cmd, arg, dt)

    


    