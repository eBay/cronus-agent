#!/bin/bash

echo "removing whitespace for $1"
# copy the file to preserve file permissions
cp $1 ${1}.tmp
sed -e 's/[ 	]*$//' $1 > ${1}.tmp
mv ${1}.tmp $1
