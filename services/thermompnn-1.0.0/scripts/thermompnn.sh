#!/bin/bash
set -eu

: "${PYTHON_EXE:=python3}"

while [ $# -gt 0 ]
do
  case "$1" in
    --pdb) input_pdb="$(realpath -s $2)"; shift 2 ;;
    --chain) input_chain="$2"; shift 2 ;;
  esac
done

if [[ -z "${input_pdb}" ]]; then
    echo "Error: --pdb argument is required."
    exit 1
fi
if [[ -z "${input_chain}" ]]; then
    echo "Error: --chain argument is required."
    exit 1
fi

current_directory=${PWD}
cd "${THERMO_MPNN}"
$PYTHON_EXE custom_inference.py \
    --model_path "${THERMO_MPNN}/models/thermoMPNN_default.pt" \
    --output ${current_directory} \
    --pdb ${input_pdb} \
    --chain ${input_chain}
