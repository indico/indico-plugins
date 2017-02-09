#!/usr/bin/env bash
# Perform a complete build of the documentation
set -e

LIB_NAME=indico_sixpay
DOCS_DIR=docs

cd ${DOCS_DIR}
# cleanup backed files
touch source/api/dummy
rm source/api/*
if which plantuml >/dev/null
then
    echo "Building UML images..."
    touch source/images/uml/dummy
    rm source/images/uml/*
    plantuml -tsvg -o ../images/uml/ source/uml/*.uml
fi

# sphinx build
sphinx-apidoc --module-first --separate --output-dir=source/api ../${LIB_NAME} --force && \
python2 $(which sphinx-build) -b html -d build/doctrees . build/html/ && \
open build/html/index.html
