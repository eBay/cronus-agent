#!/bin/bash

echo "download and install agent of version $1 in $2"
cat install_agent | sudo pkg_ver=$1 target_dir=$2 bash
