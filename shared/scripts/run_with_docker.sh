#! /bin/bash

set -eu

image=$1
shift

docker_env_args=()
for env_var in $(env | grep -vw '^PATH')
do
    docker_env_args+=(--env "$env_var")
done

docker_mount_args=()
for link_target in $(find $PWD -type link | xargs readlink -f)
do
    docker_mount_args+=(--mount "type=bind,src=$link_target,dst=$link_target,ro")
done

exec docker run --rm \
    --mount "type=bind,src=$PWD,dst=/root" \
    "${docker_mount_args[@]}" \
    "${docker_env_args[@]}" \
    --workdir "/root" \
    -- "$image" "$@"
