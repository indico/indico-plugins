#!/bin/bash
# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2022 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

USAGE="$0 [init <locale>|extract|update <locale>|compile <locale>] [plugin...]"

if [[ $# -eq 0 || "$1" == '-h' || "$1" == '--help' ]]; then
    echo "$USAGE"
    exit 0
fi

ACTION="$1"
LOCALE="$2"
PLUGINS=$(find . -name setup.py -exec sh -c 'basename $(dirname $0)' {} \;)

if [[ "$ACTION" == "extract" ]]; then
    PLUGINSINPARAMS=${@:2}
else
    PLUGINSINPARAMS=${@:3}
fi

if [[ ! -z $PLUGINSINPARAMS ]]; then
    PLUGINS=$PLUGINSINPARAMS
fi

function require_locale {
    if [[ -z "$LOCALE" ]]; then
        echo "$USAGE"
        exit 1
    fi
}

if [[ ! "init extract update compile" =~ $ACTION ]]; then
    echo "$USAGE"
    exit 1
fi

for plugin in $PLUGINS; do
    [[ "$plugin" == "_meta" ]] && continue
    [[ ! -d "$plugin" ]] && echo "plugin $plugin not found" && exit 1
    pushd "${plugin}" >/dev/null
    if [[ "$ACTION" == "init" ]]; then
        require_locale
        pybabel init -l "$LOCALE" -i "./indico_${plugin}/translations/messages.pot" -d "./indico_${plugin}/translations/"
    elif [[ "$ACTION" == "extract" ]]; then
        TRANSLATIONS_DIR="./indico_${plugin}/translations"
        [[ ! -d "$TRANSLATIONS_DIR" ]] && mkdir "$TRANSLATIONS_DIR"
        pybabel extract -o "${TRANSLATIONS_DIR}/messages.pot" "indico_${plugin}" -F ../babel.cfg
        num_strings=$(grep msgid "${TRANSLATIONS_DIR}/messages.pot" | wc -l)
        if (( $num_strings == 1 )); then
            echo "deleting empty dict ${TRANSLATIONS_DIR}/messages.pot"
            rm "${TRANSLATIONS_DIR}/messages.pot"
        fi
        pybabel extract -o "${TRANSLATIONS_DIR}/messages-js.pot" "indico_${plugin}" -k '$t.gettext' -k '$t.ngettext:1,2' -F ../babel-js.cfg
        num_strings=$(grep msgid "${TRANSLATIONS_DIR}/messages-js.pot" | wc -l)
        if (( $num_strings == 1 )); then
            echo "deleting empty js dict ${TRANSLATIONS_DIR}/messages-js.pot"
            rm "${TRANSLATIONS_DIR}/messages-js.pot"
        fi
    elif [[ "$ACTION" == "update" ]]; then
        require_locale
        pybabel update -i "./indico_${plugin}/translations/messages.pot" -l "$LOCALE" -d "./indico_${plugin}/translations"
    elif [[ "$ACTION" == "compile" ]]; then
        require_locale
        pybabel compile -f -d "./indico_${plugin}/translations/" -l "$LOCALE"
    fi
    popd >/dev/null
done
