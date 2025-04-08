import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')

import time
from test_base import Test
from lusee_script import Scripter
import uncrater as uc
from pycoreloop import lusee_commands as lc

class Test_Watchdog(Test):

    name = "watchdog"
    version = 0.1
    description = "Test that watchdog triggers and causes reboot."
    instructions = "Ensure watchdog logic is implemented in firmware."

    def __init__(self, options, analysis_options=None):
        super().__init__(options, analysis_options)
        self.need_cut_to_hello = False

    def generate_script(self):
        S = Scripter()
        S.reset()
        S.seq_begin()
        S.wait(20)                    # wait before enabling
        S.enable_watchdogs()
        S.wait(20)                    # give watchdog time to trip
        S.request_eos()
        S.seq_end(store_flash=True)

        return S

    def analyze(self, C, uart, commander, figures_dir):
        self.results = {}
        passed = False

        found_watchdog = False
        found_reboot = False
        for pkt in C.cont:
        
            print(f"Packet seen: {type(pkt)} (AppID: {hex(pkt.appid)})")
            if isinstance(pkt, uc.Packet_Watchdog):
                found_watchdog = True
            if found_watchdog and isinstance(pkt, uc.Packet_Hello):
                found_reboot = True
                break

        self.results['found_watchdog'] = int(found_watchdog)
        self.results['found_reboot'] = int(found_reboot)

        passed = found_watchdog and found_reboot
        self.results['result'] = int(passed)
        return passed

