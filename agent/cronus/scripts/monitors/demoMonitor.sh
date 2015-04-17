#!/bin/bash

TIMEOUT=5
TIMEINTERVAL=10

OS_NAME=$(uname -o)
if [ "$OS_NAME" == "Cygwin" ]; then
      echo '[AGENT_MESSAGE]{"progress": 100, "result":"App monitor script unsupported in running win32 platform"}'
      exit 0
fi

while getopts cxde option
do  case "$option" in
        c)
            echo "[AGENT_MESSAGE] {\"progress\": 100, \"result\":{\"timeout\":$TIMEOUT, \"timeinterval\":$TIMEINTERVAL}}"
            exit 0
        ;;
        x)
            echo "[AGENT_MESSAGE] {\"progress\": 100, \"result\":{\"timeout\":$TIMEOUT}}"
            exit 0
        ;;
        e)
            echo '[AGENT_MESSAGE] {"error": 500, "errorMsg": "error occured"}'
            exit -1
        ;;
        d)
            echo '[AGENT_MESSAGE] {"progress": 100, "result": {"badkey":"cpu", "value":"10%"}}'
            exit 0
        ;;
        [?])
            echo "Usage: $0 [-c]"
            exit -1
        ;;
    esac
done

echo '[AGENT_MESSAGE] {"progress": 100, "result": {"key":"cpu", "value":"10%"}}'
exit 0
