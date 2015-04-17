#!/bin/bash -ae

# creates a cronus package
# it will also create a prop file

###########################################
# function to clean up and exit
###########################################
function clean {
    if [[ -e $CRONUS_FILE ]]; then
        rm $CRONUS_FILE
    fi

    if [[ -e $PROP_FILE ]]; then
        rm $PROP_FILE
    fi
}

function quit {
    clean
    exit -1
}


###########################################
# argument parsing and validation
###########################################

EXPECTED_ARGS=1

# check the number of args
if [[ $# -ne $EXPECTED_ARGS ]]
then
        echo "Usage: `basename $0` <path to package directory>"
        exit -1
fi

echo "Attempting to create cronus package out of $1..."
echo "" 

PKG=$(echo $1 | sed -e 's/\/$//')
#convert windows path
PKG=$(echo $PKG | sed  -e 's:\\:/:g')
PKG=$(echo $PKG | sed -e 's_C:_/cygdrive/c_')

PKG_DIR=$(dirname $PKG)
#convert windows path
PKG_DIR=$(echo $PKG_DIR | sed  -e 's:\\:/:g')
PKG_DIR=$(echo $PKG_DIR | sed -e 's_C:_/cygdrive/c_')

PKG_NAME=$(basename $PKG)
CRONUS_NAME="$PKG_NAME.cronus"

CRONUS_FILE="$1.cronus"
#convert windows path
CRONUS_FILE=$(echo $CRONUS_FILE | sed  -e 's:\\:/:g')
CRONUS_FILE=$(echo $CRONUS_FILE | sed -e 's_C:_/cygdrive/c_')

PROP_FILE="$1.cronus.prop"
CRONUS_PROP="$PKG/cronus/cronus.prop"

if [[ ! -d $PKG ]]; then
    echo "Error: $PKG is not a directory"
    exit -1
fi

if [[ ! -r $CRONUS_PROP ]]; then
    echo "Error: unable to find $CRONUS_PROP"
    exit -1    
fi

for key in 'description' 'contact'
do
    grep "\"$key\":" $CRONUS_PROP > /dev/null || {
        echo "Error: Unable to find $key in $CRONUS_PROP"
        exit -1
    }
done

for key in 'name' 'md5' 'size'
do
    grep "\"$key\":" $CRONUS_PROP | grep "\[\[\[$key\]\]\]" > /dev/null || {
        echo "Error: Unable to find variable ($key) in $CRONUS_PROP"
        exit -1
    }
done

####################################################
# remove the old packages
####################################################
clean

####################################################
# create the cronus package
####################################################

echo "Creating $CRONUS_FILE..."
echo ""
echo "tar -h --preserve-permissions -czf $CRONUS_FILE --directory $PKG $(ls $PKG)"
tar -h --preserve-permissions -czf $CRONUS_FILE --directory $PKG $(ls -A $PKG) || {
    echo "Error: Did not successfully tar the file ($CRONUS_FILE)"
    quit
}

#########################################
# create the prop file
#########################################

echo ""
echo "Creating $PROP_FILE..."
echo ""

# change the parameters
if [[ $(uname) == 'Darwin' ]]; then
    SIZE=$(stat -f '%z' $CRONUS_FILE)
else
    SIZE=$(du -b $CRONUS_FILE | cut -f 1)
fi
MD5=$(md5sum $CRONUS_FILE | cut -d " " -f 1)
#Correcting for Mac
if [ ${#MD5} == 0 ]
  then MD5=$(md5 $CRONUS_FILE | cut -d " " -f 4)
fi

# move the cronus prop
cp $CRONUS_PROP $PROP_FILE || {
    echo "Unable to copy $CRONUS_PROP $PROP_FILE"
    quit
}

sed -e "s/\[\[\[size\]\]\]/$SIZE/" $PROP_FILE > ${PROP_FILE}.tmp || {
    echo "Unable to replace size in $PROP_FILE"
    quit
}
mv ${PROP_FILE}.tmp $PROP_FILE

sed -e "s/\[\[\[name\]\]\]/$CRONUS_NAME/" $PROP_FILE > ${PROP_FILE}.tmp || {
    echo "Unable to replace name in $PROP_FILE"
    quit
}
mv ${PROP_FILE}.tmp $PROP_FILE

sed -e "s/\[\[\[md5\]\]\]/$MD5/" $PROP_FILE > ${PROP_FILE}.tmp || {
    echo "Unable to replace name in $PROP_FILE"
    quit
}
mv ${PROP_FILE}.tmp $PROP_FILE

echo ""
echo "Finished."

