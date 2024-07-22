import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import argparse

from test_spec import Test_Spec
from test_crosstalk import Test_CrossTalk

Tests = [Test_Spec, Test_CrossTalk]

def Name2Test(name):
    for T in Tests:
        if T.name == name:
            return T
    return None

def main():
    parser = argparse.ArgumentParser(description='Driver for tests.')
    parser.add_argument('test_name', nargs='?', default=None, help='Name of the test')
    parser.add_argument('-l', '--list', action='store_true', help='Show the available tests')
    parser.add_argument('-i', '--info', action='store_true', help='Print information for the test')
    parser.add_argument('-r', '--run', action='store_true', help='Run the test')
    parser.add_argument('-o', '--options', default='', help='Test options, option=value, comma or space separated.')
    parser.add_argument('-w', '--workdir', default='.', help='Output directory (as test_name.pdf)')
    parser.add_argument('-b', '--backend', default='DCBEmu', help='What to command. Possible values: DCBEmu (DCB Emulator), DCB (DCB), coreloop (coreloop running on PC)')
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
            for opt in t.options.keys():
                print (f"{opt:20} : {str(t.options[opt]):20} : {t.options_help[opt]} ")
        sys.exit(0)

    if args.run:
        print("Running commander...")
        run(args)
        print ("Done.")

if __name__ == "__main__":
    main()