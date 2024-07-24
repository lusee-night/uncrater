import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
    
from  lusee_script import Scripter
import lusee_commands as lc
from commander import Commander
import argparse


def run(args):
    
    S = Scripter()
    #S.reset()

    S.start(dt=1)
    #S.spectrometer_command(0x0D,2,dt=4)
    S.stop(dt=10)
    S.start(dt=1)
    #S.stop(dt=10)
    #S.spectrometer_command(lc.RFS_SET_RESET,0,dt=1)
    S.exit(dt=10)
    
    S.write_script("test_flash")
    C = Commander(session="session_test_flash", script='test_flash')
    C.run()
    
    
def analyze():
    pass

def main():
    parser = argparse.ArgumentParser(description='Test ADC.')
    parser.add_argument('-r', '--run', action='store_true', help='Run the program')
    parser.add_argument('-a', '--analyze', action='store_true', help='Analyze the program')
    
    args = parser.parse_args()

    if args.run:
        print("Running commander...")
        run(args)
        print ("Done.")

    if args.analyze:
        print("Analyzing the program...")
        analyze();
        print ("Done.")

if __name__ == "__main__":
    main()