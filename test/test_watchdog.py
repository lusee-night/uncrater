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
        #S.enable_heartbeat(enable=False)
        S.wait(5)                    # wait before enabling
        S.enable_watchdogs(0b11111111)  # enable all except CDI and uC watchdog
        S.wait(20)                    # give watchdog time to trip
        S.spectrometer_command(lc.RFS_SET_TEST_WATCHDOG, 0x13)  # Stop feeding uC watchdog
        S.wait(20)


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

class Test_Watchdog_Command(Test):

    name = "watchdog_command"
    version = 0.1
    description = "Test that watchdog test command trips ADC + uC watchdogs."
    instructions = "Ensure watchdog test command (0x1A) is implemented."

    def generate_script(self):
        S = Scripter()
        S.reset()
        S.seq_begin()
        S.wait(5)
        S.enable_watchdogs(True)
        S.wait(5)
        S.spectrometer_command(lc.RFS_SET_TEST_WATCHDOG, 0x13)  # Stop feeding uC watchdog
        S.wait(4)                              # Let it trip
        S.spectrometer_command(lc.RFS_SET_TEST_WATCHDOG, 0x49)  # Simulate ADC trip
        S.wait(4)
        S.request_eos()
        S.seq_end(store_flash=True)
        return S

    def analyze(self, C, uart, commander, figures_dir):
        self.results = {}
        found_watchdog = False
        correct_mask = False

        for pkt in C.cont:
            print(f"Seen packet: {pkt.__class__.__name__}, AppID: {hex(pkt.appid)}")
            if hasattr(pkt, 'tripped'):
                print(f"  --> tripped_mask = 0x{pkt.tripped:02X}")
            
            if isinstance(pkt, uc.Packet_Watchdog):
                found_watchdog = True
                print(f"Found watchdog packet with mask 0x{pkt.tripped:02X}")
                if pkt.tripped & 0x80 and pkt.tripped & 0x01:
                    correct_mask = True
                    break

        self.results['found_watchdog'] = int(found_watchdog)
        self.results['correct_mask'] = int(correct_mask)
        passed = found_watchdog and correct_mask
        self.results['result'] = int(passed)
        return passed