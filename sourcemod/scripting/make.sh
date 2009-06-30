#!/bin/bash

if [ -z $1 ]
then
	COMPILETHESE=*.sp
	SKIPEXISTING=true
else
	COMPILETHESE=$1
	SKIPEXISTING=false
fi

for sourcefile in $COMPILETHESE
do
	smxfile="`echo $sourcefile | sed -e 's/\.sp$/\.smx/'`"
	
	if [ $SKIPEXISTING = true -a -e ../plugins/$smxfile ]
	then
		echo -e "Skipping existing output file $smxfile.\n\n"
		continue
	fi
	
	echo -n "Compiling $sourcefile ... "
	./spcomp -i"`pwd`/include" $sourcefile -o../plugins/$smxfile
	echo -e "\nDone.\n\n"
done

