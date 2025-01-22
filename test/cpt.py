import argparse
import os

#!/usr/bin/env python


def cpt_options():
    return "channels=0123, gains=LMH, freqs=0.1 0.7 1.1 3.1 5.1 10.1 15.1 20.1 25.1 30.1 35.1 40.1 45.1 50.1 60.1 70.1, amplitudes=280 0, bitslices=25 16, slow=True"

def main():
    parser = argparse.ArgumentParser(description='CPT/TVAC test wrapper.')
    parser.add_argument('root_dir', type=str, help='root directory')
    parser.add_argument('test', type=str, help='test')
    parser.add_argument('-f', '--force', action='store_true', help='Force test even if test exists')
    parser.add_argument('-p', '--pretend', action='store_true', help='Do not actually run the test, just display what you would be writing')

    args = parser.parse_args()

    if not os.path.exists(args.root_dir):
        print ('Creating directory:', args.root_dir)
        os.makedirs(args.root_dir)

    test = args.test
    if test == 'alive':
        out_dir = os.path.join(args.root_dir, 'session_alive')
        cmd_line = 'python test/cli_driver.py -b DCB -a -r alive -w '+out_dir
    elif test == 'route':
        out_dir = os.path.join(args.root_dir, 'session_route')
        cmd_line = 'python test/cli_driver.py -b DCB -r route -w '+out_dir
    elif test == 'gain':
        out_dir = os.path.join(args.root_dir, 'session_cpt-short_awg')
        cmd_line = 'python test/cli_driver.py -b DCB -g ssl -r cpt-short -w '+out_dir+f' -o"{cpt_options()}"'
    elif test == 'noise':
        out_dir = os.path.join(args.root_dir, 'session_cpt-short_terminated')
        cmd_line = 'python test/cli_driver.py -b DCB -g ssl -w '+out_dir+f' -o"{cpt_options()}"'
    elif test == 'combine':
        out_dir = os.path.join(args.root_dir, 'session_cpt-short_awg')
        out_dir_terminated = os.path.join(args.root_dir, 'session_cpt-short_terminated')
        cmd_line = ('python test/cli_driver.py -b DCB -g ssl -r cpt_short_awg -w '+out_dir
                    +f' -o"{cpt_options()},terminated_set={out_dir_terminated}"') 
    elif test == 'science':
        # we do things a bit differently there
        pass
    else:
        print ('Test not recognized:', test)
        print ('Test should be one of alive, route, gain, noise, combine, science')
        return
            
    if test!='science':
        if (os.path.exists(out_dir) and not args.force):
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
    


if __name__ == '__main__':
    main()