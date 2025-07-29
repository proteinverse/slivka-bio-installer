#! /usr/bin/env bash

set -e
jronn "$@"
for arg in "$@"; do
    if [[ ${arg} == -o=* ]]; then
        outputFile=${arg:3}
        break
    fi
done
python $JALVIEW_PARSER_SCRIPT \
    --annot jronn.jvannot \
     "$outputFile"
