#
# This is a base class for a testing script.
#

import sys
import os
import uncrater as uc
import numpy as np
import matplotlib.pyplot as plt

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

# now try to import pycoreloop
try:
    import pycoreloop
except ImportError:
    print("Can't import pycoreloop\n")
    print("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo.")
    sys.exit(1)


def texify(s):
    """Convert a string to a TeX-friendly format"""
    if type(s) is str:
        s = s.replace("_", r"\_")
        s = s.replace("%", r"\%")
        s = s.replace("&", r"\&")
        s = s.replace("$", r"\$")
        s = s.replace("#", r"\#")
        s = s.replace("{", r"\{")
        s = s.replace("}", r"\}")
        s = s.replace("^", r"\^{}")
        s = s.replace("~", r"\~{}")
    else:
        s = str(s)
    return s

class Test:

    name = None
    description = """ Base class for a testing script. """
    instructions = """ Here come instructions for setup required for the test."""
    default_options = {}  ## dictinary of options for the test
    options_help = {}  ## dictionary of help for the options

    def __init__(self, options, analysis_options=None):

        self.options = self.default_options
        self.analysis_options = analysis_options if analysis_options is not None else {}
        self.options.update(options)
        self.need_cut_to_hello = True # most test do need this

        # first check options sanity internally
        if not (set(self.default_options.keys()) == set(self.options_help.keys())):
            for k in self.default_options.keys():
                if k not in self.options_help:
                    print("Missing help for option: ", k)
                    sys.exit(1)
            for k in self.options_help.keys():
                if k not in self.default_options:
                    print("Missing option: ", k)
                    sys.exit(1)
            raise ValueError("Internal error: options and options_help do not match OR mismatching test specification")

        for k, v in self.options.items():
            if k not in self.default_options:
                print("Extranous option: ", k)
                sys.exit(1)
            setattr(self, k, v)
        self.results = None

    def generate_script(self):
        """Generates a script for the test"""
        raise NotImplementedError("generate_script not implemented in base class")

    def analyze(self, work_dir, figures_dir):
        """Analyzes the results of the test.
        Returns true if test has passed.
        """
        return False

    def texify_name(self) -> str:
        """Convert self.name to valid TeX representation"""
        return texify(self.name)

    def make_report(self, work_dir, output_file, add_keys={}, verbose=False):
        """Makes a report for the test.
        template is a path to the latex template.
        result_dict is a dictionary of results that will be replaced in the template.
        work_dir where the template the template is copied over.
        output_file is the output pdf file.

        """

        if self.results is None:
            print("Cannot call make_report without calling analyze first.")
            sys.exit(1)
        base_keys = {
            "test_version": self.version,
            "test_name": self.texify_name(),
            "options_table": self.generate_options_table(),
        }



        base_dir = os.path.dirname(__file__)
        header = open(os.path.join(base_dir, "report_templates/header.tex")).read()
        body = open(os.path.join(base_dir, f"report_templates/body_{self.name}.tex")).read()
        footer = open(os.path.join(base_dir, "report_templates/footer.tex")).read()
        styfile = os.path.join(base_dir, "report_templates/sansfontnotes.sty")
        output_tex = os.path.join(work_dir, "report.tex")
        template = header + body + footer

        combined_dict = {**self.results, **base_keys, **add_keys}
        for key in combined_dict:
            template = template.replace("++" + key + "++", str(combined_dict[key]))
        with open(output_tex, "w") as f:
            f.write(template)
            f.close()

        os.system(f"cp {styfile} {work_dir}")

        if verbose:
            os.system(f"cd {work_dir}; pdflatex -interaction=batchmode report.tex")
        else:
            os.system(
                f"cd {work_dir}; pdflatex -interaction=batchmode report.tex >/dev/null 2>&1"
            )
        os.system(f"cp {work_dir}/report.pdf {output_file}")
        if self.results["result"]:
            open(f"{work_dir}/../PASSED", "w").close()
        else:
            open(f"{work_dir}/../FAILED", "w").close()

    def generate_options_table(self):
        """Generates a table with the options"""
        table = "\\begin{tabular}{p{2.5cm}p{2.5cm}}\n"
        # table += "\\hline\n"
        # table += " Option & Value \\\\ \n"
        # table += "\\hline\n"
        for key, value in self.options.items():
            table += " \\texttt{" + texify(key) + "}" + " &  " + texify(value)+ "} \\\\ \n"
        # table += "\\hline\n"
        table += "\\end{tabular}\n"
        print(table)
        return table

    def coreloop_version(self):
        return pycoreloop.pystruct.VERSION_ID

    def get_versions(self, C):
        if len(C) > 0 and type(C.cont[0]) == uc.Packet_Hello:
            H = C.cont[0]
            H._read()
            self.results["hello"] = 1

            def h2v(h):
                v = f"{h:#0{6}x}"
                v = v[2:4] + "." + v[4:6]
                return v

            def h2vs(h):
                v = f"{h:#0{10}x}"
                v = v[4:6] + "." + v[6:8] + " r" + v[8:10]
                return v

            def h2d(h):
                v = f"{h:#0{10}x}"
                v = v[6:8] + "/" + v[8:10] + "/" + v[2:6]

                return v

            def h2t(h):
                v = f"{h:#0{10}x}"
                v = v[4:6] + ":" + v[6:8] + "." + v[8:10]
                return v

            self.results["SW_version"] = h2vs(H.SW_version)
            self.results["FW_version"] = h2v(H.FW_Version)
            self.results["FW_ID"] = f"{H.FW_ID:#0{4}x}"
            self.results["FW_Date"] = h2d(C.cont[0].FW_Date)
            self.results["FW_Time"] = h2t(C.cont[0].FW_Time)
            if H.SW_version != self.coreloop_version():
                print(
                    f"WARNING!!! SW version in pycoreloop ({self.coreloop_version():x}) does not match SW version in coreloop ({H.SW_version:x})"
                )
        else:
            self.results["hello"] = 0
            self.results["SW_version"] = "N/A"
            self.results["FW_version"] = "N/A"
            self.results["FW_ID"] = "N/A"
            self.results["FW_Date"] = "N/A"
            self.results["FW_Time"] = "N/A"

    def plot_telemetry(self, spectra, figures_dir, save_data=None):
        time, V1_0, V1_8, V2_5, T_FPGA = [], [], [], [], []
        for sp in spectra:
            time.append(sp["meta"].time)
            V1_0.append(sp["meta"].telemetry_V1_0)
            V1_8.append(sp["meta"].telemetry_V1_8)
            V2_5.append(sp["meta"].telemetry_V2_5)
            T_FPGA.append(sp["meta"].telemetry_T_FPGA)

        time = np.array(time)
        V1_0 = np.array(V1_0)
        V1_8 = np.array(V1_8)
        V2_5 = np.array(V2_5)
        T_FPGA = np.array(T_FPGA)

        fig, ax = plt.subplots(4, 1, figsize=(12, 8))
        ax[0].plot(time, V1_0, label="V1.0")
        ax[0].axhline(1.0, color="b", linestyle="--")
        ax[0].set_ylabel("Volts")
        ax[0].set_xlabel("Time [s]")
        ax[0].set_ylim(min(0.8, V1_0.min() - 0.1), max(1.2, V1_0.max() + 0.1))
        ax[0].legend()

        ax[1].plot(time, V1_8, label="V1.8")
        ax[1].axhline(1.8, color="b", linestyle="--")
        ax[1].set_ylabel("Volts")
        ax[1].set_xlabel("Time [s]")
        ax[1].set_ylim(min(1.6, V1_8.min() - 0.1), max(2.0, V1_8.max() + 0.1))
        ax[1].legend()

        ax[2].plot(time, V2_5, label="V2.5")
        ax[2].axhline(2.5, color="b", linestyle="--")
        ax[2].set_ylabel("Volts")
        ax[2].set_xlabel("Time [s]")
        ax[2].set_ylim(min(2.3, V2_5.min() - 0.1), max(2.7, V2_5.max() + 0.1))
        ax[2].legend()
        ax[3].plot(time, T_FPGA, label="T_FPGA")
        ax[3].set_ylabel("Temperature [C]")
        ax[3].set_xlabel("Time [s]")
        ax[3].set_ylim(T_FPGA.min() - 5, T_FPGA.max() + 5)
        ax[3].legend()
        if not figures_dir is None:
            fig.savefig(os.path.join(figures_dir, "telemetry.pdf"))
        if save_data is not None:
            np.savetxt(
                save_data,
                np.array([time, V1_0, V1_8, V2_5, T_FPGA]).T,
                fmt="%s",
            )

        return time, V1_0, V1_8, V2_5, T_FPGA
