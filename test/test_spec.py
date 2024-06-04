import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
    
from  lusee_script import Scripter
from commander import Commander
import argparse


def run(args):
    channel_config = args.channel_config
    autorange = args.gain_autorange
    just_auto = args.just_auto
    Navg1, Navg2= args.Navg1, args.Navg2
    
    S = Scripter()
    S.reset()
    S.ana_gain("MMMM") # to prevent any auto
    cfg = channel_config.split(':')
    if len(cfg)!=4:
        print ('bad configuration\n')
        sys.exit(1)

    for i,c  in enumerate(cfg):
        c=c.strip()
        g=c[0]
        assert (g in 'LMHD')
        p = int(c[1])
        m =int (c[2])
        S.route(i,p,m,g)

    if autorange:
        S.ana_gain("AAAA") # sets everything to auto (except disabled)

    S.set_Navg(Navg1,Navg2)
    if just_auto:
        S.select_products(0b1111) # just auto
        
    S.start()

    S.exit(dt=30)    
    S.write_script("test_spec")
    C = Commander(session="session_test_spec", script='test_spec')
    C.run()
    
def analyze():
    try:
        import uncrater
        from uncrater import Collection
    except:
        print ("No uncrater. Sorry.\n")
        sys.exit(1)
    import matplotlib.pyplot as plt
    
    C = Collection('session_test_spec/cdi_output')
    print (C.cont)
    stat=None
    for p in C.cont:
        if type(p)==uncrater.Packet_Metadata:
            print (p.info()) 

def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-r', '--run', action='store_true', help='Run the program')
    parser.add_argument('-a', '--analyze', action='store_true', help='Analyze the program')
    parser.add_argument('-g', '--gain_autorange', action='store_true', help='Autorange gains before doing sampling.')
    parser.add_argument('-A', '--just_auto', action='store_true', help='Just pass auto-spectra');
    parser.add_argument('-c', '--channel_config', type=str, default='D00:D00:D00:D00', help='channel gain:route configuration')
    parser.add_argument('--Navg1', type=int, default='14', help='Navg1 shift');
    parser.add_argument('--Navg2', type=int, default='3', help='Navg2 shift');
    
    

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