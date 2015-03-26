#!/bin/bash

for dir in $(find -name pytest.ini -exec dirname {} \;); do
    pushd "$dir" >/dev/null
    py.test "$@"
    popd >/dev/null
done
