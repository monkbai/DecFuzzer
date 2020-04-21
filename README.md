# How Far We Have Come: Testing Decompilation Correctness of C Decompilers  ISSTA'20

ISSTA'20 Artifact for: `How Far We Have Come: Testing Decompilation Correctness of C Decompilers`

## 0. Environment
The whole experiment was conducted on `Ubuntu 18.04`, the following installation instructions also assume working on Ubuntu system, so we recommend running this experiment on `Ubuntu` or other `*nix` systems.

## 1. Project Structure
* ./src/: source code directory
* ./runtime/: CSmith runtime library
* ./seed_for_retdec/ & ./seed_for_r2/: seed test files

## 2. Code Structure
* *fuzzer.py*: main component, intialize a fuzzing test by running this script
* *generator.py*: to compile and decompile files
    * *IDA_decompile.py* and *idapy_decompile.py*: to decompile files with IDA (not used in this Artifact Evaluation Package)
    * *R2_decompile.py*: to decompile with Radare2_ghidra_plugin
* *EMI_generator.py*: to generate EMI variants
    * *MySQL_connector.py*: to connect MySQL
    * *CFG_measurer.py*: to measure CFG distance of two programs (used for EMI mutation)
    * *ENV_Profiler.py*: to provide live code EMI mutation function
    * *ContextTable.py*: context structure
* *replacer.py*: to replace main() in original code with decompilation result
    * *modifier.py*: to replace custom macros in decompilation results
* *checker.py*: to compare the output of the two programs for consistency
* *Config.py*: constant values/strings/paths

## 3. Installation of dependencies

### 3.0. Libraries and tools:

    sudo apt install gcc-multilib
    sudo apt install m4
    sudo apt install openssl libssl-dev -y
    sudo apt install flex bison
    sudo apt install pkg-config

**Cmake 3.12** or later is needed to build r2ghidra-dec, to install latest version of Cmake, we download source code from [here](https://github.com/Kitware/CMake/releases/download/v3.16.6/cmake-3.16.6.tar.gz), then build it following instructions on their [website](https://cmake.org/install/), like:

    ./bootstrap
    make 
    sudo make install

### 3.1. MySQL
MySQL is used in EMI mutation, to install it on Ubuntu:

    apt-get install mysql-server

Then start mysql service:

    service mysql start

**Remember to update `user` and `passwd` in MySQL_connector.py** if you set another user and password. You can check your default user and password by:

    sudo cat /etc/mysql/debian.cnf

### 3.2. PyMySQL
To install the MySQL Driver for Python3:

    pip3 install PyMySQL

If pip3 is not installed, you can install it by:

    apt-get install python3-pip

### 3.3. Decompilers
We tested 4 decompilers:
* IDA Pro: [https://www.hex-rays.com/products/ida/](https://www.hex-rays.com/products/ida/ )
* JEB3: [https://www.pnfsoftware.com/](https://www.pnfsoftware.com/)
* RetDec: [https://retdec.com/](https://retdec.com/)
* Radare2: [https://www.radare.org/n/radare2.html](https://www.radare.org/n/radare2.html) 
(we tested the r2ghidra plugin of radare2, more specifically)

Since *IDA Pro* and *JEB3* are expensive commercial tools, we would only show how to test the two opensource tools *RetDec* and *r2ghidra* plugin of *radare2* in the experiment below. 
You can test the two commercial decompilers in the same way if you have license.

#### 3.3.1. Radare2 and r2ghidra 
To install radare2 from git:

    git clone https://github.com/radareorg/radare2
    cd radare2 ; sys/install.sh ; cd ..

To install the decompiler plugin r2ghidra after installation of radare2:

    r2pm update
    r2pm -i r2ghidra-dec

Then we need to install r2pipe to use the decompiler script *R2_decompile.py*:

    pip3 install r2pipe

#### 3.3.2. RetDec
To install RetDec, we recommend to download and unpack [pre-built package](https://github.com/avast/retdec/releases) to save time, you can also build from source code following the instructions on their [github page](https://github.com/avast/retdec). (The size of unpacked RetDec is about 5.5 GB.)

Please download and unpack the 64 bits version for Ubuntu at [here](https://github.com/avast/retdec/releases/download/v4.0/retdec-v4.0-ubuntu-64b.tar.xz), then you can find the `retdec-decompiler.py` file under `retdec/bin/`. 

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

The script `run.py` will run fuzzing test on *RetDec* and *r2ghidra* separately. It will first test 100 csmith generated programs in directory `./seed_for_[retdec|r2]`, the result will be stored in `./seed_for_[retdec|r2]/result/` and `./seed_for_[retdec|r2]/error/`, the EMI variants will be stored in `./seed_for_[retdec|r2]/emi/`.

Then it will test all generated EMI variants, the results are stored in a similar manner.

### 4.4. Result example 
For example, if a C file `./10.c` is to be tested, it will be compiled first:

    ./10.c ==compile==> ./10

Then the executable `./10` will be decompiled by corresponding decompiler:

    ./10 ==decompile==> ./10_retdec.c or ./10_r2.c

We try to generate a new compilable file by replacing `func_1` function in original `./10.c` with code in `./10_retdec.c` or `./10_r2.c`:

    ./10_retdec.c or ./10_r2.c ==replace==> ./10_new.c ==recompile==> ./10_new

If recompilation is failed, the source code is stored in `./error/` and error information is logged in `./error/error_log.txt`.

Finally, we compare the outputs of `./10` and `./10_new`, if it turns out differently, this file will be store in `./result/` and logged in `./result/result_log.txt`.

