# test status

![Automated tests now](https://github.com/lusee-night/uncrater/actions/workflows/tests.yml/badge.svg)

# uncrater

Uncrater is a decoder and diagnostic toolkit for coreloop CDI output,
an intermediate one-logical-packet-per-file format used for testing
and as input to luseepy’s analysis pipeline.

## Installation

Install the runtime package with pip or uv:

```bash
python3 -m pip install .
```

```bash
uv pip install .
```

The runtime package includes the frozen coreloop schema bindings needed for
decoding. Importing and decoding do not require `CORELOOP_DIR`, a sibling
coreloop checkout, or a separately installed `pycoreloop` module.

Optional dependency groups keep development-only tools out of the decoder's
runtime environment:

```bash
python3 -m pip install ".[test]"
python3 -m pip install ".[vendor]"
python3 -m pip install ".[plot,report]"
python3 -m pip install ".[lab]"
```

The `vendor` extra is only needed when regenerating frozen bindings from a
pinned coreloop source checkout. The hardware commander/test harness may use
an explicitly configured coreloop checkout; this is separate from runtime
packet decoding.

## Decoder behavior

Packets are dispatched using both their AppID and selected wire schema. The
package contains frozen bindings for `0x203`, `0x305`, the verified early and
final `0x306` layouts, and the latest shipped `0x307` layout. Known but
unverified schemas (`0x300`, `0x302`, `0x308`, and `0x309`) fail closed.
Because `0x306` names two different ABIs, it requires discriminating packet
evidence. An explicit variant must agree with that evidence:

```python
from uncrater.schema_registry import SchemaEvidence, binding_for_wire_version

binding = binding_for_wire_version(
    0x306,
    evidence=SchemaEvidence(
        appid=0x206,
        payload_length=2571,
        housekeeping_type=0,
    ),
)
```

`resolve_packet_stream()` accepts `(AppID, bytes)` pairs and resolves one
immutable schema selection before typed packet decoding. It rejects mixed
reported versions and contradictory structural evidence. Pass the result as
`Collection(..., schema_resolution=resolution)` when decoding a subset of that
input. The subset may lack discriminating housekeeping, but its version
prefixes and any structural evidence must agree with the inherited selection.
The inherited proof also appears as `input_schema` in the canonical report.

Use `schema_resolution_record()` and `schema_resolution_from_record()` to
persist and restore the selection. Restoration re-runs the resolver and checks
the binding fingerprint. Individual `Packet` reads use both
`schema=resolution.binding` and `evidence=resolution.evidence`, including
housekeeping subtypes that cannot distinguish the two 306 layouts on their own.

If a collection has no usable version evidence, decoding uses the latest binding
and records that the schema was assumed. `Collection` is non-strict by default:
it warns on stderr, records machine-readable issues in `decode_status`, and skips
invalid products without discarding the rest of the session. Pass `strict=True`
to raise `PacketDecodeError` on the first fatal issue.

`Collection` orders packet files deterministically and uses the first Hello to
select one schema for the entire directory. When there is no Hello, it falls
back to the first fixed packet-version prefix. The 0x306 layouts still require
structural housekeeping or calibrator evidence because both report the same
version. RawADC is intentionally different from normal spectra: coreloop emits
waveform metadata after the waveform group, so Collection associates that
metadata with the preceding waveforms. Delayed metadata may complete several
captures in stream order, independently of where metadata arrives between
waveform packets. Firmware emits either one selected channel or all four in
order 0,1,2,3. The complete interval determines the possible capture groupings;
only associations shared by every grouping are published. Unexplained counts
and ambiguous partial captures remain unresolved. Corrupt packets keep
their place in this accounting, and valid waveform channels remain available
even when metadata is absent. Hello and EOS in the same source stream delimit
independent intervals; duplicate metadata UIDs or backward mission times make
an interval ambiguous.

`Collection.unresolved_waveforms` and the canonical report retain unresolved
packet associations, including the values of unmatched valid metadata.
Re-reading all accumulated input recomputes the associations, so a later
metadata packet can complete an earlier incomplete capture. Optional
`waveform_packet_context` supplies original order within each source bank.
CCSDS spans are retained as provenance; they do not imply per-APID counters.
Cross-bank Hello/EOS placement cannot be recovered from bank concatenation.
An explicit `metadata_packet_index` (or null) in every context entry replays a
complete-input association without rematching session subsets. Referenced
packets, source banks, and channel uniqueness are validated again.

Without reliable transport-loss evidence, some losses fit another capture
grouping: four singleton channels with three lost metadata packets resemble
one intact quartet. The decoder cannot distinguish those inputs. No time or
metadata interpolation is performed.

## Decoder tests

The public test suite creates packet bytes synthetically and never uses the
private CDI corpus:

```bash
python3 -m pip install ".[test]"
python3 -m pytest -m "not real_data"
```

ABI, vendoring, and compression-parity checks additionally require the
`vendor` extra and a coreloop Git checkout containing the pinned commits:

```bash
python3 -m pip install ".[test,vendor]"
CORELOOP_DIR=/path/to/coreloop python3 scripts/vendor_coreloop.py --coreloop /path/to/coreloop --check
cmake -S /path/to/coreloop -B /path/to/coreloop/build
cmake --build /path/to/coreloop/build --target cl_utils --parallel
CORELOOP_DIR=/path/to/coreloop python3 -m pytest tests/test_abi.py test/standalone/test_coreloop_parity.py
```

Private real-CDI tests read only the root named by `UNCRATER_CDI_CORPUS`; they
never discover or populate a corpus. With that variable unset they skip, and
`--require-cdi-corpus` turns the missing corpus into an error. Release
qualification selects the full tier and fails if any expectation is still
uncurated:

```bash
UNCRATER_CDI_CORPUS=/private/cdi-corpus python3 -m pytest tests/real_data --cdi-tier full --require-cdi-corpus
```

All 127 policies in the current private corpus are still uncurated, so this
full qualification command is expected to fail until their expectations have
been reviewed independently of uncrater.

The emulator integration workflow is separate from public tests and runs only
when started explicitly with GitHub Actions `workflow_dispatch`.

## Development and hardware dependencies

### Linux packages
Install latex
```bash
sudo apt-get install texlive-full
```
> **_NOTE:_**  Installing `texlive` will take up around 5G of disk space. There is a known issue with the installer
> messages hanging at some portions of the download at "This may take some time..." &mdash; simply click enter a few
> times and it should continue running.


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


# Instructions for Eric

You need to checkout three repos. Main branch in all cases as I've updated them
 * uncrater -- this one
 * coreloop -- https://github.com/lusee-night/coreloop/
 * LuSEE_MIV -- https://github.com/lusee-night/lusee_MiV

 Next steps:

 1. Follow instructions in coreloop's README to compile it. Make sure you see generated files in pycoreloop: `lusee_commands.py`, `lusee_appIds.py` and `core_loop.py` and that they are non-zero in length.
 2. Go to `LuSEE_FS` in lusee_MiV. Soft link `coreloop` subdirectory in the coreloops repo to be under `application`. You should have something like
 ```
anze@lusee-01: ~/work/lusee/lusee_MiV/LuSEE_FS/application ? ls -l
total 4
lrwxrwxrwx 1 anze visitors   26 Oct  8 10:10 coreloop -> ../../../coreloop/coreloop
drwxr-xr-x 2 anze visitors   34 Oct  8 10:10 main
drwxr-xr-x 2 anze visitors 4096 Oct  8 10:10 support
 ```
 3. Compile . There should be two versions Debug and Release. Under Project -> Properties -> C/C++ General -> Paths and Symbols -> Symbols tab there should be DEBUG symbol that is 1 for Debug and 0 for Release. Upload to your board. Debug version should be spitting out stuff on UART, Release is silent.
 4. Enter uncrater, set  `CORELOOP_DIR`  to where coreloop has been checked out.  
 5. At this point, with DCB Emulator connected, you should be able to say
```
 python test/cli_driver.py -a alive
 ```
 See what happens and if there is a `report.pdf` under `session_alive`. 

 6. You can now try to run the cpt-test by saying something like

 ```
 time python test/cli_driver.py -r cpt-short -o "freqs=0.1 0.5 1.0 5.0 10.0 15.0 20.0 25.0 30.0 35.0 40.0 45.0 50.0 60.0 75.0, gains=LMH, amplitudes=400 280 200 140 0, bitslices=27 25 23 21 16, amplitude_fact=5, channels=3

 ```

 This will conclude stuff you can do at BNL.

 When you get to the real test, you need change the code as follows:

 1. You need to add a new commanded backend, called DCB. This is done as follows:
  * Template a new commander based on `DCBEmu` module. It needs to inherit BackendBase. They need to two things: 
      - start data listening threads on init. Every time data is picked up, they are send to self.save_data. See L52 in `DCBEmulator.py` and L539 in `ethernet_comm.py`
      - implement `def send_command(self, cmd, arg):` to send a command to the spectrometer via DCB
  * Change `commander.py` L66 to register this backend.

  2. At this point, you can test this by running the aliveness test as per above.

  3. Implemented the AWG backend. This is done as follows:
  * Template the new backed based on AWGBackendLab7.py. It needs to inherit AWGBackedBase. They need to do the following:
     - implement `__init__` and `stop` to initialize and end backend
     - implement 
     ```
      def tone (self, ch, frequency, amplitude):
        # ch is 0-3
        # freq is in MHz
        # amplitude is in mVPP
     ```
  * Change `commander.py` L74 to register this backend

  4. At this point you should be able to run cpt-short. I would start with a minimal few tones test to see if it works.


  ### Possible issues

  My main worry is that the system won't be able to deal with the rate at which data are spit out. You can increase various delays at 3 places:

For the amount of time spectrometer waits between sending out waveforms, change L 438 in spectrometer_interface.c. Unit is my tick which is 10ms. THis requires SW recompile / reupload

For the amount of time spectrometer waits between sending out spectral payloads (it sends metadata + 16 x data), change DISPATCH_DELAY in core_loop.h. This requires SW recompile / reupload

For the amount of time between sending various spectrometer commands, change waits in L143-166 in `test_cpt_short.py`. Note that if you do the above two, you will almost certainly also need to increase wait in this script.
