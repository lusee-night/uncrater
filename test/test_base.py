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
        
        if (verbose):
            os.system(f'cd {work_dir}; pdflatex -interaction=batchmode report.tex')
        else:
            os.system(f'cd {work_dir}; pdflatex -interaction=batchmode report.tex >/dev/null 2>&1')
        os.system(f"cp {work_dir}/report.pdf {output_file}")
        if self.results['result']:
            open (f"{work_dir}/../PASSED","w").close()
        else:
            open (f"{work_dir}/../FAILED","w").close()

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