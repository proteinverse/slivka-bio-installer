#! /usr/bin/env bash

set -euo pipefail
aacon "$@"
for arg in "$@"; do
    if [[ ${arg} == -o=* ]]; then
        outputFile=${arg:3}
        break
    fi
done
python $JALVIEW_PARSER_SCRIPT \
    --annot aacon.jvannot \
    "$outputFile"
