import argparse
import os
import sys
import time


def gen_cmd_line(test, workdir, options=None, analyze = False, awg = True, analysis_options=None):
    if analyze:
        run = '-a'
    else:
        run = '-r'

    if options is None:
        options = ''
    else:
        options = f'-o "{options}"'

    if analysis_options is not None:
        options += f' -p "{analysis_options}"'

    awg_opt = '-g ssl' if awg else ''
    return  f'{sys.executable} test/cli_driver.py -b DCB  {awg_opt} -w {workdir} {run} {test} {options}'

def cpt_options():
    return "channels=0123, gains=LMH, freqs=0.1 0.7 1.1 3.1 5.1 10.1 15.1 20.1 25.1 30.1 35.1 40.1 45.1 50.1 60.1 70.1, amplitudes=280 0, bitslices=25 16, slow=True"

def main():
    parser = argparse.ArgumentParser(description='CPT/TVAC test wrapper.')
    parser.add_argument('root_dir', type=str, help='root directory')
    parser.add_argument('test', type=str, help='test')
    parser.add_argument('-f', '--force', action='store_true', help='Force test even if test exists')
    parser.add_argument('-p', '--pretend', action='store_true', help='Do not actually run the test, just display what you would be writing')
    parser.add_argument('-x', '--no_awg', action='store_true', help='Do not use AWG (might lead to non-sensical result)')

    args = parser.parse_args()

    if not os.path.exists(args.root_dir):
        print ('Creating directory:', args.root_dir)
        os.makedirs(args.root_dir)
    awg = not args.no_awg

    test = args.test
    if test == 'alive':
        out_dir = os.path.join(args.root_dir, 'session_alive')
        cmd_line = gen_cmd_line('alive',out_dir, 'slow=True', awg = awg)
    elif test == 'route':
        out_dir = os.path.join(args.root_dir, 'session_route')
        cmd_line = gen_cmd_line('route',out_dir, 'Vpp=300', awg = awg)
    elif test == 'gain':
        out_dir = os.path.join(args.root_dir, 'session_cpt-short_awg')
        cmd_line = gen_cmd_line('cpt-short',out_dir, cpt_options(), awg = awg)
    elif test == 'noise':
        out_dir = os.path.join(args.root_dir, 'session_cpt-short_terminated')
        cmd_line = gen_cmd_line('cpt-short',out_dir, cpt_options(),awg = awg)
    elif test == 'combine':
        out_dir = os.path.join(args.root_dir, 'session_cpt-short_awg')
        out_dir_terminated = os.path.join(args.root_dir, 'session_cpt-short_terminated')
        cmd_line = gen_cmd_line('cpt-short',out_dir, cpt_options(), analysis_options="terminated_set="+out_dir_terminated, awg = awg, analyze=True)
    elif test == 'science':
        # we do things a bit differently there
        pass
    else:
        print ('Test not recognized:', test)
        print ('Test should be one of alive, route, gain, noise, combine, science')
        return
            
    if test!='science':
        if (test!='combine') and (os.path.exists(out_dir) and not args.force):
            print ('Test data already exists:', out_dir)
            print ('Use -f to force test.')
            return
        print ('Running:', cmd_line)
        if not args.pretend:
            os.system(cmd_line)
        else:
            print ('Will not run anything, pretend mode')
    else:
        science_test(args.root_dir)
    
    return

def science_test(root_dir):
    out_dir = lambda i : os.path.join(root_dir, f'session_science_{i:03d}')
    c = 0 
    while os.path.exists(out_dir(c)):
        c += 1
    print ('Starting with directory:', out_dir(c))
    while True:
        cmd_line = gen_cmd_line('science', out_dir(c), 'bitslicer=15,notch=False, preset=trula,route=inverse,slow=true,time_mins=20', awg = False)
        print ('Running:', cmd_line)
        os.system(cmd_line)
        c += 1
        time.sleep(1)
        

        for route in ['inverse', 'pairs', 'default']:
            cmd_line = gen_cmd_line('science', out_dir(c), f'bitslicer=15,notch=True, preset=simplex2,route={route},slow=true,time_mins=20', awg = False)
            print ('Running:', cmd_line)
            os.system(cmd_line)
            time.sleep(1)
            c+=1 


if __name__ == '__main__':
    main()
