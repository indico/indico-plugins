#!/bin/bash

for dir in $(find -name pytest.ini -exec dirname {} \;); do
    pushd "$dir" >/dev/null
    pytest "$@"
    popd >/dev/null
done
