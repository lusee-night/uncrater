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
    # this triggers stat packets, but will only autorange
    # channels that are in auto
    S.range_ADC(dt=0.2)  
    # wait a little in case we need to settle on new gains
    S.waveform(1, dt = 0.5)    
    S.waveform(2, dt = 0.2 )    
    S.waveform(3, dt = 0.2)    
    S.range_ADC(dt=0.2)    
    S.waveform(0, dt = 0.2)
    S.waveform(0, dt = 0.2)

    S.exit(dt=1)    
    S.write_script("test_adc")
    C = Commander(session="session_test_adc", script='test_adc')
    C.run()
    
def analyze():
    try:
        import uncrater
        from uncrater import Collection
    except:
        print ("No uncrater. Sorry.\n")
        sys.exit(1)
    import matplotlib.pyplot as plt
    
    C = Collection('session_test_adc/cdi_output')
    print (C.cont)
    stat=None
    for p in C.cont:
        if type(p)==uncrater.Packet_Housekeep:
            print (p.info()) 
            if stat is None:
                stat=p # first packet
    wf = []
    for p in C.cont:
        if type(p)==uncrater.Packet_Waveform:
            p.read()
            print (p.info())
            wf.append(p.waveform)
    wf = [wf[3], wf[0],wf[1],wf[2]]
    fig, ax = plt.subplots (2,4,figsize=(15,10))
    Hmask = 8
    Lmask = 128
    Amask = 2048
    
    for i in range(4):
        mask = ""
        if stat.error_mask&(Hmask<<i):
            mask+="H"
        if stat.error_mask&(Lmask<<i):
            mask+="L"
        if stat.error_mask&(Amask<<i):
            mask+="C"
        ax[0][i].set_title(f"ADC channel {i}")
        ax[1][i].set_title(f"Actual gain {stat.actual_gain[i]} Mask:{mask}")
        ax[0][i].plot(wf[i][:200])
        ax[1][i].hist(wf[i])
        ax[1][i].axline([stat.min[i],0], [stat.min[i],1],ls='--',color='r')
        ax[1][i].axline([stat.mean[i],0], [stat.mean[i],1],ls='--',color='r')
        ax[1][i].axline([stat.max[i],0], [stat.max[i],1],ls='--',color='r')
        

    plt.show()    
                   



def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-r', '--run', action='store_true', help='Run the program')
    parser.add_argument('-a', '--analyze', action='store_true', help='Analyze the program')
    parser.add_argument('-g', '--gain_autorange', action='store_true', help='Autorange gains before doing sampling.')
    parser.add_argument('-c', '--channel_config', type=str, default='D00:D00:D00:D00', help='channel gain:route configuration')
    

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