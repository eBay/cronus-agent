#!/bin/bash

echo copy agent package to current dir
cp ../../target/dist/agent-$1.unix.cronus .
cp ../../target/dist/agent_config-$1prod.unix.cronus .

echo copy python package to current dir
cp ../../../python-package/target/dist/python_package-$2.unix.cronus .

echo stop any existing cronus agent
sudo initctl stop cronus

echo now install agent
cat  install_agent_localbuild | sudo pkg_ver=$1 pypkg_ver=$2 target_dir=$3 bash
