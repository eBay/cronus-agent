#!/bin/bash 
# 
# Use this script to initialize a cronus package structure
#

###########################################
# argument parsing and validation
###########################################


#EXPECTED_ARGS=1

# check the number of args
#if [[ $# -gt $EXPECTED_ARGS ]]
#then
#        echo "Usage: sh `basename $0` <path to initialize cronus package>"
#	exit -1;
#fi


# check if have 1 args or 0
# if 0, then continue in current directory
#if [[ $# -eq $EXPECTED_ARGS ]]; then
#	if [[ -d $1 ]]; then
#		DIR=$1	
#	else
#		echo "$1 is not a valid path"
#		exit -1;
#	fi
#else

#	DIR='./'
#fi


if [[ ! $# -eq 1 ]]; then
	#number of input parameter > 1
	echo "Usage1: sh bootstrap.sh <path to initialize cronus package>" 
	echo "Usage2: curl -sS 'https://raw.githubusercontent.com/yubin154/cronusagent/master/agent/scripts/cronus_package/bootstrap.sh' | DIR=<path to initialize cronus package> bash" 
 	echo "examples:"
	echo " sh bootstrap.sh"
	echo " sh bootstrap.sh ./tmp"
  	echo " curl -sS 'https://raw.githubusercontent.com/yubin154/cronusagent/master/agent/scripts/cronus_package/bootstrap.sh' | bash"
   	echo " curl -sS 'https://raw.githubusercontent.com/yubin154/cronusagent/master/agent/scripts/cronus_package/bootstrap.sh' | DIR=/home/yourname/Documents bash"
    	echo ""
	exit -1;

#number of input parameter = 1
else
	DIR=$1		
fi


#Validate Inputl Directory
if [[ -d $DIR ]]; then
	echo "Attempting to Bootstrap In $DIR"	
else
	echo "$DIR is not a valid path"
	exit -1;
fi

###########################################
# generating cronus package structure
###########################################

mkdir -p $DIR/cronus/scripts
cd  $DIR/cronus/scripts

touch startup
touch shutdown
touch activate
touch deactivate
touch "install"
touch uninstall

chmod 755 startup
chmod 755 shutdown
chmod 755 activate
chmod 755 deactivate
chmod 755 "install"
chmod 755 uninstall

mkdir monitors

echo '{
"name":"[[[name]]]",
"md5":"[[[md5]]]",
"description":"your description here",
"long description":"your long description here",
"size":[[[size]]],
"contact":"you@abc.com"
}' > ../cronus.prop

touch ../cronus.ini

cd -

echo "Finished"

