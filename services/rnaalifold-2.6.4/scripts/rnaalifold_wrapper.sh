#! /usr/bin/env bash

set -euo pipefail
RNAalifold "$@" | tee output.txt
OPTS=""
if [[ -f alifold.out ]]; then
    OPTS="--alifold alifold.out"
fi
python $JALVIEW_PARSER_SCRIPT \
    $OPTS \
    output.txt \
    rnaalifold.jvannot
