#!/bin/bash
#
# address is in $1
#  $EC1_normal/multicast/q1
#

while true
do
	for var in {1..5}
	do
		S_RECV -a $1 -m $var
	done
done
