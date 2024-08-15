# uncrater
LuSEE Night binary blob unpackager

## Dependencies
### Python environment
To install Python dependencies, run
```bash
pip install -r requirements.txt
```
### Linux packages
Install latex
```bash
sudo apt-get install texlive-full
```
> **_NOTE:_**  Installing `texlive` will take up around 5G of disk space. There is a known issue with the installer
> messages hanging at some portions of the download at "This may take some time..." &mdash; simply click enter a few
> times and it should continue running.


## Coreloop dependency

The python module `pycoreloop` that contains definitions of AppIDs and Spectrometer commands has to be imported.
You can specify `CORELOOP_DIR` to specify the directory of the [coreloop](https://github.com/lusee-night/coreloop/) branch.
In most setups `export CORELOOP_DIR=..` will do the job.

## Testing suite

Test are accessed using the CLI interface in `test/cli_driver.py`. Running 
```
python test/cli_driver.py --help
```
will list the available options.

Useful options:
 * `-l` will list available tests
 * `-i test_name` will show more information about the test and its options
 * `-r test_name` will perform the test, analyze and produce a pdf report. The report (together with more data) can be found, by default, in `session_test_name/report.pdf`
 * `-a test_name` will run just the analysis and report producing part (useful, for example, when debugging the actual analysis.)


 ### Developing and debugging the test suite

 
Before we go into tests, let's briefly discuss the mechanics of how these commands and response are constructed. This is described under the section of `Spectrometer commanding, data and pycoreloop` in the coreloop's [README.md](https://github.com/lusee-night/coreloop/).

So now we have the tools to generate commands and understand responses. Next we need to use those to make a test.  Each test is composed of these steps:
  * Preparing a list of commands
  * Sending that list of commands, together with appropriate wait states to a hardware of coreloop running on a PC
  * Collecting the output of the spectrometer during the test period
  * Analyzing the output of the spectrometer
  * Writing a report

This structure is imposed into the base class object [`test/test_base.py`](test/test_base.py). Each test corresponds to a derived object that inherits from `Test` object (defined in `test_base.py`). The command line drive in `test/cli_driver.py` can therefore execute any test in an automated fashion. We can get the list of available options with 

```
$ python test/cli_driver.py --help

usage: cli_driver.py [-h] [-l] [-i] [-r] [-a] [-o OPTIONS] [-w WORKDIR] [-v] [-b BACKEND] [--operator OPERATOR] [--comments COMMENTS] [test_name]

Driver for tests.

positional arguments:
  test_name             Name of the test

options:
  -h, --help            show this help message and exit
  -l, --list            Show the available tests
  -i, --info            Print information for the test
  -r, --run             Run the test and analyze the results
  -a, --analyze         Analyze the results on a previously run test
  -o OPTIONS, --options OPTIONS
                        Test options, option=value, comma or space separated.
  -w WORKDIR, --workdir WORKDIR
                        Output directory (as test_name.pdf)
  -v, --verbose         Verbose processing
  -b BACKEND, --backend BACKEND
                        What to command. Possible values: DCBEmu (DCB Emulator), DCB (DCB), coreloop (coreloop running on PC)
  --operator OPERATOR   Operator name (for the report)
  --comments COMMENTS   Comments(for the report)
```


 This is illustrated in the aliveness test [`test/test_alive.py`](test/test_alive.py). The concepts described here are illustrated below.

In particular, test needs to define the following class variables with obvious names:

  * `name`
  * `description` - short description
  * `instructions` - instructions for how to execute the test if any special setup is needed
  * `default_options` - dictionary with default options 
  * `options_help` - dictionary mapping option names to descriptions

If a test is added to the `cli_driver.py` list of availabe tests it should be automatically executable.

#### Preparing the list of commamnds.

The list of commands is prepared using the scripter in the `generate_script` method taking into account the options. Options are copied straight into object's attribute.

#### Analyzing the output

The output is analyzed in the `analyze` method. This mehtod received, among other things a `Collection` of packets. If performs its analysis based on packets in that collection and saves results in the `self.results` dictionary.

#### Writing report

Report is finally assembled from pieces of latex saved in `test/report_templates` as follows:
 * `header.tex`, `body_testname.tex` and `footer.tex` are collated in the report
 * For every key in results dictionary, `++key++` is replaced with the contents of that key
 * The report is saved in the working directory and pdflatex is executed


 #### Mechanics of executing the test

 This part is subject to change and the current solution is there only temporarily. The script that is generated by `generate_script` command is passed to the `Commander`. `Commander` can speak to several back-ends, in principle, currenlty just to the `DCBemu` (DCB emulator). It sends commands (and processes occasional wait states) via UDP to DCB Emulator in one thread and collects the packets in the other thread. The packets are saved into a `working_dir/cdi_results` in a one file per packet format. The CLI driver collects these packest though the `Collection` object and passes it forward.
  
#### Running with coreloop backend

To run a basic aliveness test with the coreloop backend, you can says something like
```
python test/cli_driver.py -r -b coreloop alive
```

In order for this to work, the system needs to have:
 * be able to read `data/true_spectrum.dat`, easiest for now to link coreloop's data here
 * need to find the coreloop executable, currently assumed to be in `$CORELOOP_DIR/build/coreloop` so one needs to set the `CORELOOP_DIR` variable appropriately (typically `export CORELOOP_DIR=../coreloop` works)

