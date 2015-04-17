#!/bin/bash -euE

ABS_PATH=$(cd ${0%/*} && echo $PWD/${0##*/})
ABS_DIR=$(dirname "$ABS_PATH")

PYTHON_VERSION=2.6.6
PYTHON_NAME=Python-$PYTHON_VERSION
PYTHON_PKG=$PYTHON_NAME.tgz

DOWNLOAD_DIR="${ABS_DIR}/downloads"
TARGET_DIR="${ABS_DIR}/python_package-1.0.3.ubuntu"
PYTHON_DIR="${ABS_DIR}/${PYTHON_NAME}"

function cleanup {
    echo "====================Clean up==========\n"
    rm -rf $DOWNLOAD_DIR
    rm -rf $TARGET_DIR
    rm -rf $PYTHON_DIR
    rm -f $ABS_DIR/*.cronus* 
    echo "====================Done: clean up==========\n"
}

function installPython {
    echo "====================Install python==========\n"
    mkdir -p $DOWNLOAD_DIR
    cd $DOWNLOAD_DIR
    wget http://www.python.org/ftp/python/$PYTHON_VERSION/$PYTHON_PKG

    cd $ABS_DIR
    tar -xvzf ${DOWNLOAD_DIR}/$PYTHON_PKG

    cd $PYTHON_DIR
    ./configure --prefix=$TARGET_DIR
    make
    make install
    echo "====================Done: install python==========\n"
}


function installSetuptools {
    echo "====================Install setuptools==========\n"
    cd $DOWNLOAD_DIR
    wget http://pypi.python.org/packages/2.6/s/setuptools/setuptools-0.6c9-py2.6.egg
    export PYTHONPATH="$TARGET_DIR/lib/python2.6/site-packages"
    sh setuptools-0.6c9-py2.6.egg --prefix=$TARGET_DIR
    echo "====================Done: install setuptools==========\n"
}

function installModules {
    echo "====================Install modules==========\n"
    cd $ABS_DIR
    cat python.modules | xargs -I X $TARGET_DIR/bin/python $TARGET_DIR/bin/easy_install X
    echo "====================Done: install modules==========\n"
}

function makeCronusPackage {
    echo "====================Make Cronus Package==========\n"
    cp -rf $ABS_DIR/cronus $TARGET_DIR/

    cd $DOWNLOAD_DIR
    wget --no-check-certificate https://com.domain.sub/mc2009/build/trunk/scripts/make_cronus.sh
    chmod +x make_cronus.sh

    cd $ABS_DIR
    $DOWNLOAD_DIR/make_cronus.sh $TARGET_DIR
    echo "====================Done: Make Cronus Package==========\n"
}

cleanup
installPython
installSetuptools
installModules
makeCronusPackage
