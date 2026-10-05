#!/bin/sh
# Build the site and copy it to your own server with rsync.
# Set DEST to user@host:/path, e.g.  DEST=me@nimory:/srv/www/{{ name }} ./deploy.sh
set -eu
DEST="${DEST:?set DEST=user@host:/path/to/site}"
rynz build --check
rsync -az --delete "{{ output }}/" "$DEST/"
echo "deployed to $DEST"
