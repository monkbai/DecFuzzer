# How Far We Have Come: Testing Decompilation Correctness of C Decompilers  ISSTA'20

ISSTA'20 Artifact for: `How Far We Have Come: Testing Decompilation Correctness of C Decompilers`

## 0. Environment
Our experiment was conducted on `64-bit Ubuntu 18.04`. We recommend to setup on
the same OS system. 

## 1. Project Structure
* `src/`: source code directory
* `runtime/`: CSmith runtime library
* `seed_for_retdec` and  `seed_for_r2`: seeds for EMI testing

## 2. Code Structure
* `fuzzer.py`: main component, main component, intializing a fuzzing test campaign by calling functions in this script
* `generator.py`: to compile and decompile files
    * `R2_decompile.py`: to decompile the Radare2/Ghidra plugin
    * `IDA_decompile.py` and `idapy_decompile.py`: to decompile files with IDA (not used in this Artifact Evaluation Package; see clarifications below)
* `EMI_generator.py`: to generate EMI variants
    * `MySQL_connector.py`: to connect MySQL, which is used in the implementation of EMI mutation
    * `CFG_measurer.py`: to measure CFG distance of two programs (used for EMI mutation)
    * `ENV_Profiler.py`: to provide live code EMI mutation function
    * `ContextTable.py`: context structure
* `replacer.py`: to replace main() in original code with decompilation result
    * `modifier.py`: to replace custom macros in decompilation results
* `checker.py`: to compare the output of the two programs for consistency
* `Config.py`: constant values/strings/paths

## 3. Installation of dependencies

### 3.0. Libraries and tools:

    sudo apt install gcc-multilib
    sudo apt install m4
    sudo apt install openssl libssl-dev -y
    sudo apt install flex bison
    sudo apt install pkg-config

`Cmake` version 3.12 or later is needed to build r2ghidra-dec. To install latest
version of Cmake, download source code from
[here](https://github.com/Kitware/CMake/releases/download/v3.16.6/cmake-3.16.6.tar.gz),
and then build it following instructions on their
[website](https://cmake.org/install/), like:

    ./bootstrap
    make 
    sudo make install

### 3.1. MySQL
MySQL is used in EMI mutation. To install it on Ubuntu:

    apt-get install mysql-server

Then start mysql service:

    service mysql start

**Remember to update `user` and `passwd` in MySQL_connector.py** if you set another user and password. You can check your default user and password by:

    sudo cat /etc/mysql/debian.cnf

### 3.2. PyMySQL

To install the MySQL Driver for Python3:

    apt-get install python3-pip
    pip3 install PyMySQL


### 3.3. Decompilers

As reported in the paper, four decompilers are tested as follows:

* IDA Pro: [https://www.hex-rays.com/products/ida/](https://www.hex-rays.com/products/ida/ )
* JEB3: [https://www.pnfsoftware.com/](https://www.pnfsoftware.com/)
* RetDec: [https://retdec.com/](https://retdec.com/)
* Radare2: [https://www.radare.org/n/radare2.html](https://www.radare.org/n/radare2.html) 
(we tested the r2ghidra plugin of radare2, more specifically)

We note that *IDA Pro* and *JEB3* are commercial tools, and we decide to not
provide them in this artifact evaluation phase. Instead, we provide instructions
to setup the other two free decompilers *RetDec* and *Radare2* with *Ghidra*
plugin. We assure that two commercial decompilers are tested in exactly the same way.

#### 3.3.1. Radare2 and r2ghidra 

To install Radare2:

    git clone https://github.com/radareorg/radare2
    cd radare2 ; sys/install.sh ; cd ..

We use commit 06ab29b93cb0168a8ec1cb39f860c6b990678838 when writing this README.

To further install the Ghidra decompiler plugin (named r2ghidra):

    r2pm update
    r2pm -i r2ghidra-dec

Then we need to install r2pipe to use our decompiler script *R2_decompile.py*:

    pip3 install r2pipe

#### 3.3.2. RetDec

To install RetDec, we recommend to download and unpack [pre-built
package](https://github.com/avast/retdec/releases) to save time, you can also
build from source code following the instructions on their [github
page](https://github.com/avast/retdec) (note that the size of unpacked RetDec is
about 5.5 GB.)

Download and unpack the pre-built RetDec (ver. 4.0) for Ubuntu at
[here](https://github.com/avast/retdec/releases/download/v4.0/retdec-v4.0-ubuntu-64b.tar.xz),
then you can use `retdec-decompiler.py` under `retdec/bin/`.

**Remember to update the absolute path to `retdec-decompiler.py` in _Config.py_.** For example:

    RetDec_absolute_path = '/home/fuzz/Documents/retdec-install/bin/retdec-decompiler.py'


## 4. Reproducing experimental results

### 4.1. Setup

Clone this repository

    git clone https://github.com/monkbai/DecFuzzer.git

Then do not forget to **update the absolute path to csmith runtime `runtime_dir` in _Config.py_.** For example:

    runtime_dir = '/home/fuzz/Documents/DecFuzzer/runtime/'

### 4.3. Reproducing experimental results

    python3 run.py

The script `run.py` will run fuzzing test on *RetDec* and *r2ghidra*, separately.
It will first test 1000 csmith generated programs in directory
`./seed_for_[retdec|r2]`, the result will be stored in
`./seed_for_[retdec|r2]/result/` and `./seed_for_[retdec|r2]/error/`, the EMI
variants will be stored in `./seed_for_[retdec|r2]/emi/`.

Then it will test all generated EMI variants, the results are stored in a
similar manner.

It will takes several hours to finish the whole process. While it's unlikely to get exactly the same number (since certain randomness are involved in generating EMI mutations), it should give a very close number reported in Table 3 in our paper.

### 4.4. Access to data

Meanwhile, for the ease of understanding/checking our setup, We also provide all csmith generated programs and EMI mutations which can be used to re-produce findings in Table 3, you can download them from [here](https://www.dropbox.com/sh/kqw7e19snfeukai/AADHZ45TAL9Kxi7v9nmdXfLCa?dl=0).

You can reproduce the experiment results using `./reproduce.py` script we provided. It takes two steps:

**Step 1**

Put all the C source files to be tested in a directory.

**Step 2**

Run `./reproduce.py` like:

    python3 ./reproduce.py --decompiler <decompiler name> --files_dir <directory to C files> --emi_dir <directory to store generated EMI variants> --EMI

Or

    python3 ./reproduce.py --decompiler <decompiler name> --files_dir <directory to C files>

There are four options for this `--decompiler` parameter: retdec, r2, jeb and ida. The `--EMI` parameter represents enable generating EMI variants.

For example:

    python3 ./reproduce.py --decompiler retdec --files_dir ./seed_for_retdec
    python3 ./reproduce.py --decompiler r2 --files_dir ./seed_for_r2 --emi_dir ./seed_for_r2/emi --EMI


### 4.5. Interpret Result

For example, if a C file `./10.c` is to be tested, it will be compiled first:

    ./10.c ==compile==> ./10

Then the executable `./10` will be decompiled by corresponding decompiler:

    ./10 ==decompile==> ./10_retdec.c or ./10_r2.c

We try to generate a new compilable file by replacing `func_1` function in original `./10.c` with code in `./10_retdec.c` or `./10_r2.c`:

    ./10_retdec.c or ./10_r2.c ==replace==> ./10_new.c ==recompile==> ./10_new

If recompilation is failed, the source code is stored in `./error/` and error information is logged in `./error/error_log.txt`.

Finally, we compare the outputs of `./10` and `./10_new`, if it turns out differently, this file will be store in `./result/` and logged in `./result/result_log.txt`.
