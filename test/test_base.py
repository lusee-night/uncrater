#
# This is a base class for a testing script.
# 

import sys
import os


if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

# now try to import pycoreloop
try:
    import pycoreloop
except ImportError:
    print ("Can't import pycoreloop\n")
    print ("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo.")
    sys.exit(1)


class Test:
    
    name = None
    description = """ Base class for a testing script. """
    instructions = """ Here come instructions for setup required for the test."""
    default_options = {} ## dictinary of options for the test
    options_help = {} ## dictionary of help for the options


    def __init__(self,options):
        
        self.options = self.default_options
        self.options.update(options)

        # first check options sanity internally
        if not (set(self.default_options.keys()) == set(self.options_help.keys())):
            raise ValueError("Internal error: options and options_help do not match.")
        
        for k,v in self.options.items():
            if k not in self.default_options:
                print ("Extranous option: ",k)
                sys.exit(1)
            setattr(self,k,v)
        self.results = None

    def generate_script(self):
        """ Generates a script for the test """
        raise NotImplementedError("generate_script not implemented in base class")

    def analyze(self, work_dir, figures_dir):
        """ Analyzes the results of the test. 
            Returns true if test has passed.
        """
        return False
    
    def make_report(self, work_dir, output_file, add_keys = {},verbose=False):
        """ Makes a report for the test. 
            template is a path to the latex template.
            result_dict is a dictionary of results that will be replaced in the template.
            work_dir where the template the template is copied over.
            output_file is the output pdf file.
            
        """
        
        if self.results is None:
            print ("Cannot call make_report without calling analyze first.")
            sys.exit(1)
        base_keys = {'test_version':self.version, 'test_name':self.name,
                     'options_table': self.generate_options_table()}
        
        header = open('test/report_templates/header.tex').read()
        body = open(f'test/report_templates/body_{self.name}.tex').read()
        footer = open(f'test/report_templates/footer.tex').read()
        styfile = 'test/report_templates/sansfontnotes.sty'
        output_tex = os.path.join(work_dir, 'report.tex')
        template = header+body+footer
        
        combined_dict = {**self.results, **base_keys, **add_keys}
        for key in combined_dict:
            template = template.replace('++'+key+'++', str(combined_dict[key]))
        with open(output_tex,"w") as f:
            f.write(template)
            f.close()
        
        
        os.system(f"cp {styfile} {work_dir}")
    
    
        work_dir_bash = work_dir.replace('\\','/')
    
        if (verbose):
            os.system(f'bash -c "cd {work_dir_bash}; pwd; pdflatex -interaction=batchmode report.tex"')
        else:
            os.system(f'bash -c "cd {work_dir_bash}; pwd; pdflatex -interaction=batchmode report.tex >/dev/null 2>&1"')
        os.system(f"cp {work_dir}/report.pdf {output_file}")


    def inspect_hello_packet(self,C):
        if len(C)>0 and type(C.cont[0]) == uc.Packet_Hello:
            H = C.cont[0]
            H._read()
            self.results['hello'] = 1
            def h2v(h):
                v = f"{h:#0{6}x}"
                v = v[2:4]+'.'+v[4:6]
                return v
            def h2vs(h):
                v = f"{h:#0{10}x}"
                v = v[4:6]+'.'+v[6:8]+' r'+v[8:10]
                return v

            def h2d(h):
                v = f"{h:#0{10}x}"
                v = v[6:8]+'/'+v[8:10]+'/'+v[2:6]

                return v
            def h2t(h):
                v = f"{h:#0{10}x}"
                v = v[4:6]+':'+v[6:8]+'.'+v[8:10]
                return v
            
                
            self.results['SW_version'] = h2vs(H.SW_version)
            self.results['FW_version'] = h2v(H.FW_Version)
            self.results['FW_ID'] = f"0x{H.FW_ID:#0{4}}"
            self.results['FW_Date'] = h2d(C.cont[0].FW_Date)
            self.results['FW_Time'] = h2t(C.cont[0].FW_Time)
            if H.SW_version != self.coreloop_version():
                print ("WARNING!!! SW version in pycoreloop ({self.coreloop_version():x}) does not match SW version in coreloop ({H.SW_version:x})")                
        else:
            self.results['hello'] = 0
            self.results['SW_version'] = "N/A"
            self.results['FW_version'] = "N/A"
            self.results['FW_ID'] = "N/A"
            self.results['FW_Date'] = "N/A"
            self.results['FW_Time'] = "N/A"


    def generate_options_table(self):
        """ Generates a table with the options """
        table = "\\begin{tabular}{p{2.5cm}p{2.5cm}}\n"
        #table += "\\hline\n"
        #table += " Option & Value \\\\ \n"
        #table += "\\hline\n"
        for key, value in self.options.items():
            skey = key.replace('_','\\_')
            table += " \\texttt{"+f"{skey}"+"}"+f" & {value} \\\\ \n"
        #table += "\\hline\n"
        table += "\\end{tabular}\n"
        return table
    
    def coreloop_version(self):
        return pycoreloop.pystruct.VERSION_ID