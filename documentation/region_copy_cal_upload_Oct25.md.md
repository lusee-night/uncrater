# Changelog

* 10/24/25 -- first version



# Instructions for uploading new firmware

## Preliminaries

* update coreloop repository to `main` branch:
    ``` 
    cd coreloop
    git checkout main
    git pull
    ```
* regenerate C-python interface in coreloop
    ```
    cd pycoreloop
    make clean
    make
    ```
    You might see some errors regarding `cdefs.h` -- those are harmless

* update the uncrater repository and also checkout `main` branch
    ```
    cd ../uncrater
    git checkout main
    git pull
    ```

* update the blobs repository in main (checkout `git@github.com:lusee-night/blobs.git` if needed)
  ```
    cd ../blobs
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
     [...]
    ```

## Install 0x307 into region 1 
 * We will delete region 1 and write this blob into region 1:

     ```
    python test/cli_driver.py -b DCB -r bootload -o "cmd=reboot; delete 1; write 1 ../blobs/SW/LuSEE_FS_307.hex"
    ```

 * check that the software has loaded by 
    ```
    python test/cli_driver.py -b DCB -r bootload -o "cmd=check"
    ```

    You should see something like

    ```
       Region 1 : Size = 83968 Checksum = 13D6FAAD Expected Checksum = 13D6FAAD
    ```

    If checksums don't match, the upload was not successful and you should try again. Bootloader will refuse to load a region with mismatching checksums.

    
* Now issue a reboot and see if it loads region 1 and reports the right version (we are using reboot only, otherwise it stays in bootloader):

    ```
    python test/cli_driver.py -b DCB -r bootload -o "cmd=reboot_only; wait 30"
    ```

You will get something like :

```
Packet 1: SWS hello
Hello Packet
SW_Version : 0x307     <--- this needs to match
FW_Version : 0x406
FW_ID      : 0x24d     <--- this will be 0x508 for TMRed FW
FW_Date    : 0x20250822
FW_Time    : 0x113019
packet_id : 0x237384
time_sec : 35.4521484375

```

## Test copying region 1 into region 2 


```
python test/cli_driver.py -b DCB -r region -o "cmd=copy,src=1, tgt=2" -w session_copy_1_2
```

It should run for about a minute and issue a pass/fail.

You can look at the report in `session_copy_1_2/report.pdf`


## Upload calibrator weights 

```
python test/cli_driver.py -b DCB -r calupload -o "cmd=copy,src_dir=../blobs/cal_weights/251022" -w session_calupload_copy
```

It should run a few minutes and issue a pass/fail

You can look at the report in `session_calupload_copy/report.pdf`



