#!/usr/bin/env python

#####################################################################
#                                                                   #
# This version is enhance with the "upload-to-server"               #
# functionality, in order to interact with the Dataview application #
#                                                                   #
#####################################################################

# ---

import sys, os

sys.path.append(".")
sys.path.append("./scripter/")
sys.path.append("./commander/")
import argparse

from test_alive import Test_Alive
from test_science import Test_Science
from test_wave import Test_Wave
from test_cpt_short import Test_CPTShort

# from test_spec      import Test_Spec
# from test_crosstalk import Test_CrossTalk
from test_data_interface import Test_DataInterface
from test_tr_spectra import Test_TRSpectra

from commander import Commander
import uncrater as uc

import yaml

try:
    import serverAPI
    from serverAPI import serverAPI
    import urllib, base64
except:
    print("Not importing serverAPI")
default_server = "http://localhost:8000/"

Tests = [
    Test_Alive,
    Test_Science,
    Test_Wave,
    Test_CPTShort,
    Test_DataInterface,
    Test_TRSpectra,
]


def Name2Test(name):
    if name is None:
        print("You must specify a test.")
        sys.exit(1)
    for T in Tests:
        if T.name == name:
            return T
    print(f"No test named {name}.")
    sys.exit(1)


def default_user():
    user = os.environ["USER"] if "USER" in os.environ else "anonymous"
    if "HOSTNAME" in os.environ:
        user += " @ " + os.environ["HOSTNAME"]
    return user


def try_to_type(val):
    if val == "True":
        return True
    if val == "False":
        return False
    try:
        return int(val)
    except:
        pass
    try:
        return float(val)
    except:
        pass
    return val


def opt2dict(optin, default_options=None):
    options = default_options if default_options is not None else {}
    for opt in optin.strip().split(","):
        if len(opt) == 0:
            continue
        try:
            key, val = opt.split("=")
            key = key.strip()
            val = val.strip()
        except:
            print("Bad options format: ", opt)
            sys.exit(1)
        if (default_options is not None) and (key in default_options):
            options[key] = type(default_options[key])(val.strip())
        else:
            options[key] = try_to_type(val)
    return options


def main():

    parser = argparse.ArgumentParser(description="Driver for tests.")
    parser.add_argument("test_name", nargs="?", default=None,       help="Name of the test")
    parser.add_argument("-w", "--workdir",  default="session_%test_name%", help="Output directory (as test_name.pdf)")
    parser.add_argument("-l", "--list",     action="store_true",    help="Show the available tests")
    parser.add_argument("-i", "--info",     action="store_true",    help="Print information for the test")
    parser.add_argument("-r", "--run",      action="store_true",    help="Run the test and analyze the results")
    parser.add_argument("-a", "--analyze",  action="store_true",    help="Analyze the results on a previously run test")
    parser.add_argument("-d", "--dataview", action="store_true",    help="Send the data to DataView viewer")
    parser.add_argument("-o", "--options",  default="",             help="Test options, option=value, comma separated.")
    parser.add_argument("-p", "--analysis-options",default="",      help="Analysis options, option=value, comma separated.")
    parser.add_argument("-I", "--inspect",  action="store_true",    help="Inspect data before sending DataView viewer")
    parser.add_argument('-v', '--verbose',  action='store_true',    help='Verbose processing')
    parser.add_argument('-b', '--backend',  default='DCBEmu',          help='What to command. Possible values: DCBEmu (DCB Emulator), DCB (DCB), coreloop (coreloop running on PC)')
    parser.add_argument('-g', '--awg',      default='None',          help='AWG backend to use. Possible values: None, lab7, ssl')
    parser.add_argument('--operator',       default=default_user(), help='Operator name (for the report)')
    parser.add_argument('--comments',       default='None',         help='Comments(for the report)')
    parser.add_argument("-S","--server",    type=str,               help="server URL: defaults to http://localhost:8000/", default=default_server)

    # ---
    args = parser.parse_args()

    if args.list:
        print("Available tests:")
        for T in Tests:
            print(" *", T.name, "-", T.description)
        sys.exit(0)

    if args.info:
        t = Name2Test(args.test_name)
        if t is None:
            print("No such test.")
            sys.exit(1)
        else:
            print("Test: ", t.name)
            print("\nDescripton:\n", t.description)
            print("\nInstructions:\n", t.instructions)
            print("\nOptions:\n")
            print("Option               : Default Value         : Help")
            print("-----------------------------------------------------")
            for opt in t.default_options.keys():
                print(
                    f"{opt:20} : {str(t.default_options[opt]):20} : {t.options_help[opt]} "
                )
        sys.exit(0)

    if args.run:
        if args.backend not in ["DCBEmu", "DCB", "coreloop"]:
            print("Unknown backend: ", args.backend)
            sys.exit(1)
        t = Name2Test(args.test_name)
        print("Running test: ", t.name)

        options = opt2dict(args.options, t.default_options)

        print("Options set to: ")
        for key, value in options.items():
            print(f"   {key:18} : {value}")
        T = t(options)
        print("Generating script... ", end="")
        S = T.generate_script()
        print("OK.")
        workdir = args.workdir.replace("%test_name%", t.name)
        ## this will also generated the work dir
        print("Starting commander...")
        awg = None if args.awg == "None" else args.awg
        C = Commander(
            session=workdir, script=S.script, backend=args.backend, awg_backend=awg
        )
        # Save options to YAML file
        options_file = f"{workdir}/options.yaml"
        with open(options_file, "w") as file:
            yaml.dump(options, file)
        try:
            C.run()
        except KeyboardInterrupt:
            print("Interrupted.")

        print("Commander done.")

    if args.run or args.analyze:
        T = Name2Test(args.test_name)
        workdir = args.workdir.replace("%test_name%", T.name)
        # Load options from YAML file
        try:
            runtime = int(open(f"{workdir}/runtime").read())
        except:
            runtime = 0
        if runtime > 60:
            runtime = f"{runtime//60}m {runtime%60}s"
        else:
            runtime = f"{runtime}s"
        options_file = f"{workdir}/options.yaml"
        with open(options_file, "r") as file:
            options = yaml.safe_load(file)
        # Create an instance of the test with the loaded options
        analysis_options = opt2dict(args.analysis_options)
        t = T(options, analysis_options)
        C = uc.Collection(os.path.join(workdir, "cdi_output"))

        def read_and_fix(fn, max_lines=200, max_line_length=2000):
            try:
                lines = open(fn).readlines()
            except:
                return ""
            lines = [
                (l[:max_line_length] + "[...]" if len(l) > max_line_length else l)
                for l in lines
            ]
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines.append("... truncated ...\n")
            return "".join(lines)

        uart_log = read_and_fix(os.path.join(workdir, "uart.log"))
        commander_log = read_and_fix(os.path.join(workdir, "commander.log"))
        report_dir = os.path.join(workdir, "report")
        fig_dir = os.path.join(report_dir, "Figures")
        try:
            os.mkdir(report_dir)
            os.mkdir(fig_dir)
        except:
            pass
        print("Starting analysis...")
        t.analyze(C, uart_log, commander_log, fig_dir)
        print("Writing report...")

        add_keys = {
            "operator": args.operator,
            "comments": args.comments,
            "uart_log": uart_log,
            "commander_log": commander_log,
            "runtime": runtime,
        }
        t.make_report(
            report_dir,
            os.path.join(workdir, "report.pdf"),
            add_keys,
            verbose=args.verbose,
        )
        print("Test result:", "PASSED" if t.results["result"] else "FAILED")
        print("Done.")
        sys.exit(0)

    if args.inspect:
        workdir = args.workdir.replace("%test_name%", args.test_name)
        C = uc.Collection(os.path.join(workdir, "cdi_output"))
        # uart log and commander log are txt files that you might want to disply in dataview
        uart_log = open(os.path.join(workdir, "uart.log")).read()
        commander_log = open(os.path.join(workdir, "commander.log")).read()

        last_time = 0
        print(
            "| count  | AppId                  |uniq_id  |  time       | size (B)     | info                    "
        )
        print(
            "|--------|------------------------|---------|-------------|--------------|-------------------------"
        )
        for count, P in enumerate(C.cont):
            P._read()
            appid = P.appid
            if appid == 0x4F0:
                appid = 0x2F0  ## fix for firmware bug
            appid_str = uc.appid_to_str(appid)
            blob = P._blob
            unique_id = P.unique_packet_id if hasattr(P, "unique_packet_id") else 0
            time = P.time if hasattr(P, "time") else last_time
            last_time = time
            info = P.info().replace("\n", " ")[:80]

            print(
                f"|{count:8d}| {appid_str:23}|{unique_id:8x} |{time:12.3f} | {len(blob):12d} | {info}"
            )

            # See if packets can be read as they are in dataview
            if uc.appid_is_spectrum(appid):
                cur_packet = uc.Packet(appid, blob=blob, meta=meta_data)
                assert cur_packet.frequency.shape == cur_packet.data.shape
            else:
                cur_packet = uc.Packet(appid, blob=blob)
            if uc.appid_is_metadata(appid):
                meta_data = cur_packet

    if args.dataview:
        server = args.server
        API = serverAPI(server=server, verb=args.verbose)

        workdir = args.workdir.replace("%test_name%", args.test_name)
        C = uc.Collection(os.path.join(workdir, "cdi_output"))
        # uart log and commander log are txt files that you might want to disply in dataview
        uart_log = open(os.path.join(workdir, "uart.log")).read()
        commander_log = open(os.path.join(workdir, "commander.log")).read()

        last_time = 0

        cnt = 0

        for P in C.cont:
            P._read()
            appid = P.appid
            if appid == 0x4F0:
                appid = 0x2F0  ## fix for firmware bug

            blob = P._blob
            unique_id = P.unique_packet_id if hasattr(P, "unique_packet_id") else 0
            time = P.time if hasattr(P, "time") else last_time
            last_time = time

            ## HERE you send to dataview
            print(appid, unique_id, time, f"""{len(blob)}""")
            payload = base64.b64encode(blob)
            resp = API.post2server(
                "ui",
                "data",
                {
                    "appid": appid,
                    "uniq_id": unique_id,
                    "ts": time,
                    "data": payload,
                },
            )
            cnt += 1
            # if cnt>3: break
            # print (f"|{count:8d}|{appid:5x}|{unique_id:8x}|{time:12.3f}| binary blob {len(blob)}B")


if __name__ == "__main__":
    main()
