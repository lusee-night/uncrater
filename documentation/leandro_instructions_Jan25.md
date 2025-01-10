# Instructions for uploading new firmware

## Preliminaries

* update coreloop repository to `calibrator_support_program` branch:
    ``` 
    cd coreloop
    git pull
    git checkout calibrator_support_program
    git pull
    ```
* regenerate C-python interface in coreloop
    ```
    cd pycoreloop
    make clean
    make
    ```
    You might see some errors regarding `cdefs.h` -- those are harmless

* update the uncrater repository and also checkout `calibrator_support_program` branch
    ```
    cd ../uncrater
    git pull
    git checkout calibrator_support_program
    git pull
    ```
* ensure the `$CORELOOP_DIR` environment variable points to coreloop repo root:
    ```
    anze@lusee-01: ~/work/lusee/uncrater ? echo $CORELOOP_DIR
    /u/home/anze/work/lusee/coreloop
    ```
* see the uncrater driver runs:
    ```
    anze@lusee-01: ~/work/lusee/uncrater ? python test/cli_driver.py -l
    Not importing serverAPI
    Available tests:
    * alive -  Basic aliveness test of communication and spectral engine.
    * science -  Runs the spectrometer in close to the real science mode
    * wave -  Collects waveform data and checks the waveform statistics.
    * cpt-short -  Comprehensive Performance Test - Short Version.
    * data_interface -  Check that RFS_SET_AVG_SET_HI and RFS_SET_AVG_SET_MID commands work.
    * time_resolved -  Check that time resolved spectra are received.
    * route -  Runs the spectrometer and iterates over routing combinations
    * bootload -  Reboots spectrometer and interacts with bootloader.
    * bin_response -  Test the response of a bin to a signal, tests notch filter.
    * encoding_format -  Check that different compression formats work as expected.
    * calibrator -  Runs the WV calibrator EM
    ```

## Interact with bootloader

* If UART is available, looking at the output can make your life easier. First find the UART port corresponding to "Standard COM port" for the UART bridge. Typically, this is something like /dev/ttyUSB1. Run
```
minicom --device /dev/ttyUSB1
```
* Establish pygse bent pipe
* Bootloader commanding goes with the following command
```
    python test/cli_driver.py -r bootload -b DCB -o "cmd=[list of commands]"
```
commands are semicolon separated list of commands. The following are available:
  * `reboot`: reboot and stay in bootloader
  * `reboot_only`: reboot and progress to region loading
  * `reboot_hard`: hard reboot
  * `check`: checks what is in the regions
  * `cmd [cmd] [arg]`: send CDI command
  * `register [addres] [val]`: write a register via CDI commanding
  * `wait [n]`: wait for n seconds 
  * `launch [n]`: launch region n
  * `delete [n]`: delete region n
  * `write [n] [hex filename]`: write into region n


For example, you should try:

```
    python test/cli_driver.py -r bootload -b DCB -o "cmd=reboot; check"
```

You can follow the progress on UART where you should see something like

```
****  LuSEE Bootloader V1.05  7/05/24****


0. Stay in Bootloader
1. Load Flash Region 1 to TCM
2. Load Flash Region 2 to TCM
3. Load Flash Region 3 to TCM
4. Load Flash Region 4 to TCM
5. Load Flash Region 5 to TCM
6. Load Flash Region 6 to TCM
7. Jump to Application in TCM
8. Verify ALL Region Checksums
9. Send Program from memory over CDI
A. Clear LuSEE Defaults from Flash
B. Write SFL-page to FLASH (SFL registers must be set)
C. Write Region Meta Data  (SFL registers must be set)
D. Delete Flash Region     (SFL registers must be set)
E. SEND Raw ADC DATA
F. Send Program from memory over CDI
Region 1   Size =  0x1bc0   Checksum =  0x63c21ee5   Checksum_cal =  0x63c21ee5
Region 2   Size =  0x0   Checksum =  0x0   Checksum_cal =  0x0
Region 3   Size =  0x0   Checksum =  0x0   Checksum_cal =  0x0
Region 4   Size =  0x0   Checksum =  0x0   Checksum_cal =  0x0
Region 5   Size =  0x0   Checksum =  0x0   Checksum_cal =  0x0
Region 6   Size =  0x0   Checksum =  0x0   Checksum_cal =  0x0
TCM RAM  Size = 0x0   Checksum =  0x0
SENDING PACKT TO DCB
```

At the same time, the commander will be getting packets and after collection time is over it will report the same information from its packets:

```
anze@lusee-01: ~/work/lusee/uncrater ? python test/cli_driver.py -r bootload -o "cmd=reboot; check"
Not importing serverAPI
Running test:  bootload
Options set to:
   cmd                : reboot; check
Generating script... >>>>> reboot, []
>>>>> check, []
OK.
Starting commander...
Starting commander.
Sending FW command 0xff with argument 0x0.
Storing appdid 0x0208 (32 bytes)
Sending FW command 0xb0 with argument 0x0.
Sending FW command 0xb0 with argument 0x8.
Storing appdid 0x0208 (112 bytes)
Total test time: 9s
Exiting commander.
Commander done.
Analyzing 2 files from session_bootload/cdi_output.
Starting analysis...
Packet 0: bootloader
Bootloader Packet
MSG_Type : BL_STARTUP
Seq      : 0
Timestamp: 0.001952
Compilation date: 20241220
Compilation time: 142119
Payload Length: 0
Magic OK: True
Payload:

Packet 1: bootloader
Bootloader Packet
MSG_Type : BL_PRGM_CHKSUM
Seq      : 0
Timestamp: 1.29199525
Compilation date: 20241220
Compilation time: 142119
Payload Length: 20
Magic OK: True
Payload:  1BC0 63C21EE5 63C21EE5 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
Region 1 : Size = 28416 Checksum = 63C21EE5 Expected Checksum = 63C21EE5
Region 2 : Size = 0 Checksum = 0 Expected Checksum = 0
Region 3 : Size = 0 Checksum = 0 Expected Checksum = 0
Region 4 : Size = 0 Checksum = 0 Expected Checksum = 0
Region 5 : Size = 0 Checksum = 0 Expected Checksum = 0
Region 6 : Size = 0 Checksum = 0 Expected Checksum = 0

```

## Flash new software. 

 * get the hex blob [here](https://www.dropbox.com/scl/fi/cjz74eabkn16eafe03h6u/LuSEE_FS_202.hex?rlkey=u7e9ncxb1u7q1qmeqzq0m31mz&dl=0).
 * We will delete region 1 and write this blob into region 2:

     ```
    python test/cli_driver.py -b DCB -r bootload -o "cmd=reboot; delete 1; delete 2; write 2 LuSEE_FS_202.hex"
    ```

The UART output should be something like:
```

****  LuSEE Bootloader V1.05  7/05/24****


0. Stay in Bootloader
1. Load Flash Region 1 to TCM
2. Load Flash Region 2 to TCM
3. Load Flash Region 3 to TCM
4. Load Flash Region 4 to TCM
5. Load Flash Region 5 to TCM
6. Load Flash Region 6 to TCM
7. Jump to Application in TCM
8. Verify ALL Region Checksums
9. Send Program from memory over CDI
A. Clear LuSEE Defaults from Flash
B. Write SFL-page to FLASH (SFL registers must be set)
C. Write Region Meta Data  (SFL registers must be set)
D. Delete Flash Region     (SFL registers must be set)
E. SEND Raw ADC DATA
F. Send Program from memory over CDI
Erase page 0
Erase page 1
Erase page 2
Erase page 3
Region erase complete
Erase page 0
Erase page 1
Erase page 2
Erase page 3
Region erase complete
Page Write complete
Page Write complete
Page Write complete
...
```

while the commander window will display a stream of sending FW commands.

If you get a "Page write fail" instead of "Page Write complete", slowdown and try again. To slow it down, look at the L48 of `command/DCB/DCB.py` and increase wait from 0.03 to something somewhat larger.



 * check that the software has loaded by 
    ```
    python test/cli_driver.py -b DCB -r bootload -o "cmd=check"
    ```

    You should see something like

    ```
    Region 1 : Size = 0 Checksum = 0 Expected Checksum = 0
    Region 2 : Size = 39936 Checksum = 99FBED77 Expected Checksum = 99FBED77
    Region 3 : Size = 0 Checksum = 0 Expected Checksum = 0
    Region 4 : Size = 0 Checksum = 0 Expected Checksum = 0
    Region 5 : Size = 0 Checksum = 0 Expected Checksum = 0
    Region 6 : Size = 0 Checksum = 0 Expected Checksum = 0
    ```

    If checksums don't match, the upload was not successful and you should try again. Bootloader will refuse to load a region with mismatching checksums.

* Now issue a reboot and see if it loads region 2 and reports the right version (we are using reboot only, otherwise it stays in bootloader):

    ```
    python test/cli_driver.py -b DCB -r bootload -o "cmd=reboot_only; wait 30"
    ```

You will get a lot of good stuff:

```
anze@lusee-01: ~/work/lusee/uncrater ? python test/cli_driver.py -b DCBEmu -r bootload -o "cmd=reboot_only; wait 30"
Not importing serverAPI
Running test:  bootload
Options set to:
   cmd                : reboot_only; wait 30
Generating script... >>>>> reboot_only, []
>>>>> wait, ['30']
OK.
Starting commander...
Starting commander.
Sending FW command 0xff with argument 0x0.
Storing appdid 0x0208 (32 bytes)
Storing appdid 0x0208 (40 bytes)
Storing appdid 0x0209 (32 bytes)
Hello Packet
SW_Version : 0x202
FW_Version : 0x406
FW_ID      : 0x22a
FW_Date    : 0x20241220
FW_Time    : 0x142119
packet_id : 814477
time_sec : 12.420759

Storing appdid 0x020a (24 bytes)
Heartbeat Packet
Magic : OK
Count : 0
V1_0 :  1.061 V
V1_8 :  1.837 V
V2_5 :  2.564 V
T_FPGA :  46.39 C
```

Explanation: 
 * Two 0x208 packets are bootloader packets from entering bootloader and launching region 2 (they get intepreted at the end)
 * The 0x209 packet is hello packet from the flight SW and is parsed immediately. It should report SW version 0x202. The FW_ID will be somewhat lower in your case, but that is OK
 * Later on you see the hearbeat packet 0x02a which contains the temperature payload printed below.


## Run the aliveness test

Next run the aliveness test 

```
python test/cli_driver.py -b DCB -r alive -o "superslow=True"
```

This one runs particularly slowly so it shouldn't break any time limits. On UART you will see a series of stars and dots which represent varios stages in data accumulation/sending.
It will take about 3 mins to run.
Hopefully it will end with something like:

```
Starting analysis...
Writing report...
Test result: PASSED
Done.
```

You can look at the report in `session_alive/report.pdf`


## Run other tests

Now we can run some other tests. Normally you specify GSE driver with the `-g` option. We are going to omit this, which means that all GSE commands are going to be ignored and so these tests will _fail by construction_. But these are still good ways to check data transfer issues.

Try running these test to completion:

 * `python test/cli_driver.py -b DCB -r route`
 * `python test/cli_driver.py -b DCB -r cpt-short -o "channels=0123, gains=LMH, freqs=0.1 0.7 1.1 3.1 5.1 10.1 15.1 20.1 25.1 30.1 35.1 40.1 45.1 50.1 60.1 70.1, amplitudes=280 0, bitslices=25 16, superslow=True"`


Then there are some tests that will run forver, so you need to stop then with Ctrl-C. These are good ones for long term testing when you need some background data taking.

* `python test/cli_driver.py -b DCB -r science -o "bitslicer=16, disable_awg=True, notch=True, preset=simple, slow=true, time_mins=0"`

More data (same throttling as above, but more bnunched togeter):

* `python test/cli_driver.py -b DCB -r science -o "bitslicer=16, disable_awg=True, notch=True, preset=simplex2, slow=true, time_mins=0"`

A different pattern of data:
* `python test/cli_driver.py -b DCB -r science -o "bitslicer=16, disable_awg=True, notch=True, preset=trula, slow=true, time_mins=0"`



