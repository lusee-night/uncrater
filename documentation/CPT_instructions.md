# Instructions for performing the CPT

The general interface to the CPT test is via the `cpt.py` script in test directory of uncrater.

To access this script, open a linux VM terminal and run it like

```

cd ~/fsw/uncrater
python test/cpt.py -h
```

There are two parameters to this filename

 * root directory for the test to save its data. This should be the same for a test suite as explained below:
    - say you have some root dir where you want to save data `/data/CPT/`
    - for each CPT suite you want to decide on one root directory, e,g `/data/CPT/high_temperature_1`
    - You specify `/data/CPT/high_temperature_1` for *all* tests below.
    - the script will create this directory if it doesn't exist yet.
    - individual runs below will be saved under these directory with `session*` subdiretories, e.g. `/data/CPT/high_temperature_1/session_route`

 * the test name. Valid test names are: alive, route, gain, noise, combine, science.

The aliveness test is thus run as

```
python test/cpt.py /path/to/some/tvac/storage alive
```


## CPT test: routing / gain / noise

This CPT test is done in 3 steps:


### Step 1: test multiplexer (5 minutes)

Connect AWG to the preamps as per table below:

  
| AWG Selection | AWG IP          | AWG CH | ATN SN | PREAMP SN | SPT Input |
|---------------|-----------------|--------|--------|-----------|-----------|
| AWG1          | 192.168.0.133   | 1      | 6      | 6         | J4        |
| AWG1          | 192.168.0.133   | 2      | 3      | 3         | J5        |
| AWG2          | 192.168.0.132   | 1      | 4      | 4         | J6        |
| AWG2          | 192.168.0.132   | 2      | 1      | 1         | J7        |


Execute:

```
python test/cpt.py /path/to/some/tvac/storage route
```

The result will be printed at the end. It should be PASSED. You can also inspect the pdf report in `/root_dir/session_route/report.pdf`




### Step 2: measure gains (42 minutes)


With AWG remain contected run
```
python test/cpt.py /path/to/some/tvac/storage gain
```

This test will almost certainly PASS if the data has been taken correctly.

### Step 3: measure noise properties (45 minutes)

Connect 50Ohm terminators to the pre-amp inputs and run

```
python test/cpt.py /path/to/some/tvac/storage noise
```

This test will also almost certainly PASS.

Now combined the tests 2 and 3 above by runnung

```
python test/cpt.py /path/to/some/tvac/storage combine
```

This will not take any more data, but analyze it. It should run in less than 2 minutes. It will produce PASSED if the system satifies noise requirements. You can always peek at the 
`/root_dir/session_cpt-short_awg/report.pdf` for more information.

If you got PASSED after Step 1 and Step 3 we are still not dead. If not contect BNL for more information.


## Power runs

Power runs are run with AWG connected and specifying power as the test name
```
python test/cpt.py /path/to/some/tvac/storage power
```
During this test, the system will feed full range signal to all 4 ADC and adjust bitslices so that all bins are seeing significant power.  This is meant to stress the system and the power will not be representative of what the real-life power consumption will be, but it does exercise a viable off-nominal power consumption if things go awry and spectrometer ends up misconfigured.  By default it runs for 30 mins.

At the first test, I suggest that you stop if after one minut (6 HB) packets and check the value of ADC ranges spit out during analysis steps. The should be around -4000 to +4000.

```
Starting analysis...
ADC MIN: [  -25 -3842 -2811 -1357]
ADC MAX: [ -14 3420 2981 1466]
Writing report...
```

## Transit runs

Transit runs are meant to be used at Firefly during their quick check-out tests. They are run simply by specifying transit as test name
```
python test/cpt.py /path/to/some/tvac/storage transit
```

The test takes some 17 minutes to run.



## Science runs

Every time when possible, please run science-style data acquisition so that we can get as much data as possible.

To do this run

```
python test/cpt.py /path/to/some/tvac/storage science
```

This will run ad infinitum, but you can stop it with a few Ctrl-C presses.


