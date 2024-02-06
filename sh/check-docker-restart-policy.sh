#!/bin/bash
#
# Query the restart policy of all containers and report containers for which it's
# not one of "always" or "unless-stopped".
#

set -e
set -u

for cnt in $(docker ps -q); do
    docker_inspect="$(docker inspect $cnt)"
    restart_policy="$(<<<$docker_inspect jq -r .[0].HostConfig.RestartPolicy.Name)"
    if [ "$restart_policy" != "always" ] && [ "$restart_policy" != "unless-stopped" ]; then
        cnt_name="$(<<<$docker_inspect jq -r .[0].Name)"
        printf '%-50s %s\n' "$cnt_name" "$restart_policy"
    fi
done
