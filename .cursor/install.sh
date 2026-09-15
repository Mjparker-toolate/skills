#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 NVIDIA Corporation. All rights reserved.
#
# Idempotent Cloud Agent bootstrap for the NVIDIA Agent Skills catalog.
#
# This repo is a catalog of Markdown skills plus the Python + shell tooling
# that packages, validates, and documents them. There is no compiled app and
# no dependency manifest, so this script installs exactly the toolchain the
# CI workflows under .github/workflows/ rely on:
#
#   - rsync            : build-plugins.py shells out to it to materialize the
#                        generated plugin tree (.github/workflows/validate-plugins.yml)
#   - PyYAML/jsonschema/requests : imported by the .github/scripts/*.py tooling
#                        and its test suites
#   - mikefarah/yq     : regenerate-readme.sh and sync-skills.yml drive the
#                        Go `yq` (eval-all `ea`, `-r`); the Python `yq` shipped
#                        in some base images is NOT compatible
#   - fern-api         : the docs site (fern/) is built and previewed with the
#                        Fern CLI (publish-docs.yml runs `fern generate --docs`)
#
# Safe to run repeatedly: every step no-ops when the tool is already present
# and pinned, so it converges on cached or partially-prepared state.
set -euo pipefail

YQ_VERSION="v4.44.3"

log() { printf '\033[1;32m[install]\033[0m %s\n' "$*"; }

# --- system package: rsync -------------------------------------------------
if command -v rsync >/dev/null 2>&1; then
  log "rsync present: $(rsync --version | sed -n 1p)"
else
  log "installing rsync via apt"
  sudo apt-get update -qq
  sudo apt-get install -y -qq rsync
fi

# --- Go yq (mikefarah) on the default PATH ---------------------------------
# Detect the *compatible* yq. The Python `yq` also answers `command -v yq`,
# so probe for the mikefarah signature before deciding to (re)install.
if yq --version 2>/dev/null | grep -q 'mikefarah'; then
  log "mikefarah/yq present: $(yq --version)"
else
  log "installing mikefarah/yq ${YQ_VERSION} to /usr/local/bin/yq"
  sudo curl -fsSL \
    "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" \
    -o /usr/local/bin/yq
  sudo chmod +x /usr/local/bin/yq
fi

# --- Python tooling dependencies -------------------------------------------
# Mirrors the CI installs (`pip install pyyaml jsonschema requests`). --user
# keeps them off the system tree; --break-system-packages satisfies PEP 668
# on the Debian/Ubuntu base image.
log "installing Python deps (pyyaml, jsonschema, requests)"
python3 -m pip install --user --break-system-packages --upgrade \
  pyyaml jsonschema requests

# --- Fern CLI for the docs site --------------------------------------------
# The `fern-api` launcher respects the version pinned in fern/fern.config.json,
# so we do not pin the npm package itself.
#
# node/npm are nvm-managed under $HOME, so they are NOT on sudo's secure_path
# (a plain `sudo npm ...` fails with "npm: command not found"). Install as the
# normal user with an explicit --prefix pointing at the active nvm node dir.
# That dir's bin is the one nvm puts on PATH in login shells, so the `fern`
# binary is resolvable by the agent and by the docs-preview terminal without
# any shell-rc edits.
if command -v fern >/dev/null 2>&1; then
  log "fern present: $(fern --version 2>/dev/null | sed -n 1p)"
elif command -v npm >/dev/null 2>&1; then
  node_prefix="$(dirname "$(dirname "$(command -v npm)")")"
  log "installing fern-api into ${node_prefix} (nvm node dir)"
  npm install -g --prefix "$node_prefix" fern-api
else
  log "WARNING: npm not found — skipping fern-api install (docs preview unavailable)"
fi

log "bootstrap complete"
