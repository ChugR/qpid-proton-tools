#!/bin/bash
#
# address is in $1
#  $EC1_normal/multicast/q1
#

while true
do
	for var in {1..20}
	do
		S_RECV -a $1 -m $var > /dev/null || { exit; }
	done
	echo "done a set"
done
