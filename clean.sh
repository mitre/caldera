#! /bin/bash
for line in $(sudo bleachbit --list)
do
	echo "$line"
	sudo bleachbit --clean $line
done 
