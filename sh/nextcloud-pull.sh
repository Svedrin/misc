#!/bin/bash

set -e
set -u

# Pull new nextcloud image (if any)
docker images --format '{{.ID}} {{.Repository}} {{.Tag}}' nextcloud | {
    while read id repository tag; do
        if echo "$tag" | grep -q -P '^\d+$'; then
            # Tag is a number -- try to pull the same tag so we only update within the same version
            printf "pulling:  id = %s | repository = %s | tag = %s\\n" "$id" "$repository" "$tag"
            docker pull "$repository:$tag"
        fi
    done
}

# Find unused nextcloud images and remove them
docker images --format '{{.ID}} {{.Repository}} {{.Tag}}' --filter dangling=true nextcloud | {
    while read id repository tag; do
        printf "deleting: id = %s | repository = %s | tag = %s\\n" "$id" "$repository" "$tag"
        docker image rm "$id"
    done
}
