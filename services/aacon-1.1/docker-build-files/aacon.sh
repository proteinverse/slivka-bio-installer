#! /usr/bin/env bash
set -eu
exec java -jar ${COMPBIO_CONSERVATION} "$@"
