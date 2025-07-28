#! /usr/bin/env bash

set -euo pipefail
GlobPipe "$@" >output.txt

python $JALVIEW_PARSER_SCRIPT \
    --input output.txt \
    --annot globplot.jvannot \
    --feat globplot.jvfeat
