#! /usr/bin/env bash

set -e
DisEMBL "$@" >output.txt

python $JALVIEW_PARSER_SCRIPT \
    --input output.txt \
    --annot disembl.jvannot \
    --feat disembl.jvfeat
