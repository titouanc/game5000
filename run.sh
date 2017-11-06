#!/bin/bash

set -e

pushd scoreboard
npm run build
popd

honcho start
