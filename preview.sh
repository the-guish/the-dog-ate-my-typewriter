#!/bin/sh
# Preview the site, drafts included, at http://localhost:4000/the-dog-ate-my-typewriter/
# Needs only Docker. Gems are kept in a Docker volume, so only the first run installs them.
set -eu

cd "$(dirname "$0")"

image=ruby:3.3
gems=the-dog-ate-my-typewriter-gems
user="$(id -u):$(id -g)"

# The container runs as you, so the files it writes here are yours. The volume must be too.
docker run --rm -v "$gems":/gems "$image" chown "$user" /gems

# -it lets Ctrl-C stop the server; it needs a terminal.
tty=""
[ -t 0 ] && tty="-it"

docker run --rm $tty \
  -p 4000:4000 -p 35729:35729 \
  -u "$user" \
  -e HOME=/tmp \
  -e BUNDLE_PATH=/gems \
  -v "$gems":/gems \
  -v "$PWD":/srv/jekyll \
  -w /srv/jekyll \
  "$image" \
  sh -c "bundle install && bundle exec jekyll serve --drafts --livereload --host 0.0.0.0"
