#!/bin/bash

while :
do
    echo .
    date
    ps -eaf | grep qdr
    sleep 1
done
