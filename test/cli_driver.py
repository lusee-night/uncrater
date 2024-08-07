#!/usr/bin/env python

import sys, os
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import argparse

from test_alive import Test_Alive
from test_spec import Test_Spec
from test_crosstalk import Test_CrossTalk

from commander import Commander
from uncrater import Collection
import yaml

Tests = [Test_Alive, Test_Spec, Test_CrossTalk]

import serverAPI

# ---

def Name2Test(name):
    
    for T in Tests:
        if T.name == name:
            return T
    print (f"No test named {name}.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Driver for tests.')
    parser.add_argument('test_name', nargs='?', default=None, help='Name of the test')
    parser.add_argument('-l', '--list', action='store_true', help='Show the available tests')
    parser.add_argument('-i', '--info', action='store_true', help='Print information for the test')
    parser.add_argument('-r', '--run', action='store_true', help='Run the test and analyze the results')
    parser.add_argument('-a', '--analyze', action='store_true', help='Analyze the results on a previously run test')
    parser.add_argument('-d', '--dataview', action='store_true', help='Send the data to DataView viewer')
    parser.add_argument('-o', '--options', default='', help='Test options, option=value, comma or space separated.')
    parser.add_argument('-w', '--workdir', default='session_%test_name%', help='Output directory (as test_name.pdf)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose processing')
    parser.add_argument('-b', '--backend', default='DCBEmu', help='What to command. Possible values: DCBEmu (DCB Emulator), DCB (DCB), coreloop (coreloop running on PC)')
    parser.add_argument('--operator', default='anonymous', help='Operator name (for the report)')
    parser.add_argument('--comments', default='None', help='Comments(for the report)')
    args = parser.parse_args()

    
    if args.list:
        print ("Available tests:")
        for T in Tests:
            print ( ' *',T.name,'-', T.description)
        sys.exit(0)

    if args.info:
        t = Name2Test(args.test_name)
        if t is None:
            print ("No such test.") 
            sys.exit(1)
        else:
            print ("Test: ",t.name)
            print ("\nDescripton:\n",t.description)
            print ("\nInstructions:\n",t.instructions)
            print ("\nOptions:\n")
            print ("Option               : Default Value         : Help")
            print ("-----------------------------------------------------")
            for opt in t.default_options.keys():
                print (f"{opt:20} : {str(t.default_options[opt]):20} : {t.options_help[opt]} ")
        sys.exit(0)

    if args.run:
        if args.backend not in ['DCBEmu', 'DCB', 'coreloop']:
            print ("Unknown backend: ",args.backend)
            sys.exit(1)
        t = Name2Test(args.test_name)
        print ("Running test: ",t.name) 
        options = t.default_options
        for opt in args.options.strip().split(','):
            if len(opt)==0:
                continue
            try:
                key, val = opt.split('=')
            except:
                print ("Bad options format: ",opt)
                sys.exit(1)
            
            options[key] = type(t.default_options[key])(val.strip())
            #except:
            #    print ("Error setting option: ",opt, "with value: ",val)
            #    sys.exit(1)
        print ("Options set to: ")
        for key, value in options.items():
            print (f"   {key:18} : {value}")
        T = t(options)
        print ("Generating script... ", end='')
        S = T.generate_script()
        print ("OK.")
        workdir = args.workdir.replace('%test_name%',t.name)
        ## this will also generated the work dir
        print ("Starting commander...")        
        C = Commander(session = workdir, script=S.script, backend=args.backend)
        C.run()
        # Save options to YAML file
        options_file = f"{workdir}/options.yaml"
        with open(options_file, 'w') as file:
            yaml.dump(options, file)
        print ("Commander done.")
        
    if args.run or args.analyze:
        T= Name2Test(args.test_name)
        workdir = args.workdir.replace('%test_name%',T.name)
        # Load options from YAML file
        options_file = f"{workdir}/options.yaml"
        with open(options_file, 'r') as file:
            options = yaml.safe_load(file)
        # Create an instance of the test with the loaded options
        t = T(options)
        C = Collection(os.path.join(workdir,'cdi_output'))
        uart_log = open (os.path.join(workdir,'uart.log')).read()
        commander_log = open (os.path.join(workdir,'commander.log')).read()
        report_dir = os.path.join(workdir,'report')
        fig_dir = os.path.join(report_dir,'Figures')    
        try:
            os.mkdir(report_dir)
            os.mkdir(fig_dir)
        except:
            pass
        print ("Starting analysis...")
        t.analyze(C, uart_log, commander_log, fig_dir)
        print ("Writing report...")
        add_keys = {'operator':args.operator, 'comments':args.comments,'uart_log':uart_log, 'commander_log':commander_log}
        t.make_report(report_dir,os.path.join(workdir,"report.pdf"), add_keys, verbose=args.verbose)
        print ("Done.")
        sys.exit(0)
    
    if args.dataview:
        workdir = args.workdir.replace('%test_name%',args.test_name)
        C = Collection(os.path.join(workdir,'cdi_output'))
        # uart log and commander log are txt files that you might want to disply
        # in dataview
        uart_log = open (os.path.join(workdir,'uart.log')).read()
        commander_log = open (os.path.join(workdir,'commander.log')).read()
        last_time = 0
        print ("| count  |appid|uniq_id |  time      | binary blob (size)")
        print ("|--------|-----|--------|------------|-----------------")
        for count, P in enumerate(C.cont):
            P._read()
            appid = P.appid
            if appid == 0x4f0:
                appid = 0x2f0 ## fix for firmware bug

            blob = P._blob
            unique_id = P.unique_packet_id if hasattr(P, 'unique_packet_id') else 0
            time = P.time if hasattr(P, 'time') else last_time
            last_time = time 
            ## HERE you send to dataview
            print (f"|{count:8d}|{appid:5x}|{unique_id:8x}|{time:12.3f}| binary blob {len(blob)}B") 






if __name__ == "__main__":
    main()