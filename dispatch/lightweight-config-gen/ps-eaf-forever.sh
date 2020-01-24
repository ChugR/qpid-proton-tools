#!/bin/bash

while :
do
    echo .
    date
    ps -C qdrouterd -O pmem,rsz,vsz,drs
    sleep 1
done
