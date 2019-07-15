#!/bin/bash

#
# Shell script to assist with python function refactoring.
#
# Displays which functions are referenced by which files.
# If a function is only referenced by the file it is defined
# in then no output is shown for that function.
#
# outputs results to /tmp/fn_usage.txt


grep ^def *.py | tr '(' '\n' | grep ':def' > /tmp/fn_list.txt


for fn in `cat /tmp/fn_list.txt | awk '{print $2}' | sort `
do 
	line=`grep "def ${fn}"$ fn_list.txt`
	file=`echo $line | tr ':' ' ' | awk '{print $1}'`
	stat=`grep -F ${fn}'(' *.py | grep -v $file | awk '{print $1}' | uniq -c `
	if [ -n "${stat}" ]
	then
		echo '============'
		echo $line
		grep -F ${fn}'(' *.py | grep -v :def | awk '{print $1}' | uniq -c | sort -n
	fi

done > /tmp/fn_usage.txt

