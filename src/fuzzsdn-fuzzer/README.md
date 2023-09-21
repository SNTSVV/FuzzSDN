# FUZZSDN-FUZZER

A Failure-Inducing Model generation scheme for SDN based systems using Fuzzing and Machine Learning Techniques.

![Openflow](https://img.shields.io/badge/stability-experimental-orange.svg)
![Openflow](https://img.shields.io/badge/Openflow-1.4-brightgreen.svg)

## Prerequisite

+ STEP 1. Get the source code of (Repository Name) on the machine

```
$ cd ~
$ mkdir PacketFuzzer
$ git clone (add url later)
```

+ STEP 2. Install Maven

```
$ sudo apt-get install maven
```

+ STEP 3. Compile the source code manually or run the compiling script

```
$ mvn clean assembly:assembly
$ mv ./target/PacketFuzzer-1.0-SNAPSHOT-jar-with-dependencies.jar ./SVV_PacketFuzzer.jar
$ java -jar ./target/PacketFuzzer-1.0-SNAPSHOT-jar-with-dependencies.jar
```
or
```
$ ./compile_and_run.sh
```
