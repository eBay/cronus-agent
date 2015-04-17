#!/bin/bash

OS=$(awk '/DISTRIB_ID=/' /etc/*-release | sed 's/DISTRIB_ID=//' | tr '[:upper:]' '[:lower:]')

ARCH=$(uname -m | sed 's/x86_//;s/i[3-6]86/32/')

case $(uname -m) in
x86_64)
    ARCH=x64  # or AMD64 or Intel64 or whatever
    ;;
i*86)
    ARCH=x86  # or IA32 or Intel32 or whatever
    ;;
*)
    # leave ARCH as-is
    ;;
esac

VERSION=$(awk '/DISTRIB_RELEASE=/' /etc/*-release | sed 's/DISTRIB_RELEASE=//' | sed 's/[.]//')

if [ -z "$OS" ]; then
    OS=$(awk '{print $1}' /etc/*-release | tr '[:upper:]' '[:lower:]')
fi

if [ -z "$VERSION" ]; then
    VERSION=$(awk '{print $3}' /etc/*-release)
fi

OPENSSL=$(openssl version | tr '[:upper:]' '[:lower:]' | awk '{print $1,$2}' | sed 's/ //;s/[.]//;s/[.].*//')

echo "python_package-1.0.0.${ARCH}_${OS}_${OPENSSL}.cronus"
