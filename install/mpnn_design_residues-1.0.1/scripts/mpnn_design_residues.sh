#! /bin/bash

: "${PYTHON_EXE:=python3}"

getopt --test >/dev/null 2>&1
if [[ $? -ne 4 ]]; then echo "Error: getopt --test failed" >&2; exit 1; fi

set -eu

PARSED_ARGUMENTS=$(getopt -n mpnn_design_residues.sh -o i:c:d:n:t:s:b:z: -l input_pdb:,chains_to_design:,design_positions: -- "$@")
eval set -- "$PARSED_ARGUMENTS"

folder_with_pdbs="folder_with_pdbs"
if [ -d "$folder_with_pdbs" ]; then rm -Rf $folder_with_pdbs; fi
mkdir $folder_with_pdbs

chains_to_design=""
design_only_positions=""

declare -a MPNN_ARGS

while :
do
  case "$1" in
    -i | --input_pdb)        cp "$2" $folder_with_pdbs/$(basename "$2").pdb; shift; shift ;;
    # chains should have the format "<chain_1> <chain_2> <chain_3>"
    -c | --chains_to_design) chains_to_design="$2"; shift; shift ;;
    # positions should be indexes in the format "<res1_chain1> <res1_chain1> ..., <res1_chain2> <res2_chain2> ..."
    -d | --design_positions) design_only_positions="$2"; shift; shift ;;
    -n)                      MPNN_ARGS[${#MPNN_ARGS[@]}]="--num_seq_per_target"; shift; MPNN_ARGS[${#MPNN_ARGS[@]}]="$1"; shift ;;
    -t)                      MPNN_ARGS[${#MPNN_ARGS[@]}]="--sampling_temp"; shift; MPNN_ARGS[${#MPNN_ARGS[@]}]="$1"; shift ;;
    -s)                      MPNN_ARGS[${#MPNN_ARGS[@]}]="--seed"; shift; MPNN_ARGS[${#MPNN_ARGS[@]}]="$1"; shift ;;
    -b)                      MPNN_ARGS[${#MPNN_ARGS[@]}]="--batch_size"; shift; MPNN_ARGS[${#MPNN_ARGS[@]}]="$1"; shift ;;
    -z)                      MPNN_ARGS[${#MPNN_ARGS[@]}]="--backbone_noise"; shift; MPNN_ARGS[${#MPNN_ARGS[@]}]="$1"; shift ;;
    --) shift; break ;;
  esac
done

if [ "$chains_to_design" == "" ]
then
    echo "Must specify --chains_to_design";
    exit 2;
fi

if [ "$design_only_positions" == "" ]
then
    echo "Must specify --design_positions";
    exit 2;
fi

output_dir="output"
if [ -d "$output_dir" ]; then rm -Rf $output_dir; fi
mkdir $output_dir

path_for_parsed_chains=$output_dir"/parsed_pdbs.jsonl"
path_for_assigned_chains=$output_dir"/assigned_pdbs.jsonl"
path_for_fixed_positions=$output_dir"/fixed_pdbs.jsonl"


$PYTHON_EXE ${PROTEIN_MPNN}/helper_scripts/parse_multiple_chains.py \
        --input_path=$folder_with_pdbs \
        --output_path=$path_for_parsed_chains
$PYTHON_EXE ${PROTEIN_MPNN}/helper_scripts/assign_fixed_chains.py \
        --input_path=$path_for_parsed_chains \
        --output_path=$path_for_assigned_chains \
        --chain_list "$chains_to_design"
$PYTHON_EXE ${PROTEIN_MPNN}/helper_scripts/make_fixed_positions_dict.py \
        --input_path=$path_for_parsed_chains \
        --output_path=$path_for_fixed_positions \
        --chain_list "$chains_to_design" \
        --position_list "$design_only_positions" \
        --specify_non_fixed

$PYTHON_EXE ${PROTEIN_MPNN}/protein_mpnn_run.py \
        --jsonl_path $path_for_parsed_chains \
        --chain_id_jsonl $path_for_assigned_chains \
        --fixed_positions_jsonl $path_for_fixed_positions \
        --out_folder $output_dir \
        "${MPNN_ARGS[@]}" 
