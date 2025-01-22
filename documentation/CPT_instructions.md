# Instructions for performing the CPT

The general interface to the CPT test is via the `cpt.py` script in test directory of uncrater.

To access this script, open a linux VM terminal and run it like

```

cd ~/fsw/uncrater
python test/cpt.py -h
```

There are two parameters to this filename

 * root directory for the test to save its data. This should be the same across all step described below -- i.e. the script will generate subdirectories for each steps described below
 * the test name. Valid test names are: alive, route, gain, noise, combine, science.

The aliveness test is thus run as

```
python test/cpt.py /path/to/some/tvac/storage alive
```

## CPT test: routing / gain / noise

This CPT test is done in 3 steps:


### Step 1: test multiplexer

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


### Step 2: measure gains


With AWG remain contected run
```
python test/cpt.py /path/to/some/tvac/storage gain
```

This test will almost certainly PASS if the data has been taken correctly.

### Step 3: measure noise properties

Connect 50Ohm terminators to the pre-amp inputs and run

```
python test/cpt.py /path/to/some/tvac/storage noise
```

This test will also almost certainly PASS.

Now combined the tests 2 and 3 above by runnung

```
python test/cpt.py /path/to/some/tvac/storage combine
```

This will not take any more data, but analyze it. It will produce PASS if the system satifies noise requirements. You can always peek at the 
`/root_dir/session_cpt-short_awg/report.pdf` for more information.

If you got PASSED after Step 1 and Step 3 we are still not dead. If not contect BNL for more information.


## Science runs

Every time when possible, please run science-style data acquisition so that we can get as much data as possible.

To do this run

```
python test/cpt.py /path/to/some/tvac/storage science
```

This will run ad infinitum, but you can stop it with a few Ctrl-C presses.


