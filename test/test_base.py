#
# This is a base class for a testing script.
# 


class Test:
    
    name = None
    description = """ Base class for a testing script. """
    instructions = """ Here come instructions for setup required for the test."""
    default_options = {} ## dictinary of options for the test
    options_help = {} ## dictionary of help for the options


    def __init__(self,options):
        self.options = options
        # first check options sanity internally
        if not (set(self.default_options.keys()) == set(self.options_help.keys())):
            raise ValueError("Internal error: options and options_help do not match.")
        
        for k,v in options.items():
            if k not in self.default_options:
                print ("Extranous option: ",k)
                sys.exit(1)
            setattr(self,k,v)
        self.results = None

    def generate_script(self):
        """ Generates a script for the test """
        raise NotImplementedError("generate_script not implemented in base class")

    def analyze(self, work_dir):
        """ Analyzes the results of the test. C is uncrater.Collection object.
            Returns true if test has passed.
        """
        return False
    
    def make_report(self, template, result_dict, work_dir, output_file):
        """ Makes a report for the test. 
            template is a path to the latex template.
            result_dict is a dictionary of results that will be replaced in the template.
            work_dir where the template the template is copied over.
            output_file is the output pdf file.
            
        """
        if results is None:
            print ("Cannot call make_report without calling analyze first.")
            sys.exit(1)
        temp = open(template).read()
        for key in result_dict:
            temp = temp.replace('>>'+key+'<<', result_dict[key])
        open(os.path.join(work_dir, 'report.tex'),'w').write(temp)
        os.system(f"cd {work_dir}; pdflatex report.tex")
        os.system(f"mv {work_dir}/report.pdf {output_file}")


    