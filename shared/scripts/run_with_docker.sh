#! /bin/bash

set -eu
guest_workdir="/root"

docker_env_args=()
for env_var in $(env | grep -vw '^PATH')
do
    docker_env_args+=(--env "$env_var")
done

docker_mount_args=()
for link_file in $(find * -type link)
do
    link_target="$(readlink -f $link_file)"
    docker_mount_args+=(--mount "type=bind,src=$link_target,dst=$guest_workdir/$link_file,ro")
done

while [[ $# -gt 0 ]]; do
case $1 in
    --mount|--volume)
        docker_mount_args+=("$1" "$2")
        shift 2;;
    --env)
        docker_env_args+=("$1" "$2")
        shift 2;;
    *)
        break;;
esac
done

image=$1
shift

exec {BASH_XTRACEFD}>.docker.command
set -o xtrace
exec docker run --rm \
    --mount "type=bind,src=$PWD,dst=$guest_workdir" \
    "${docker_mount_args[@]}" \
    "${docker_env_args[@]}" \
    --workdir "$guest_workdir" \
    -- "$image" "$@"
