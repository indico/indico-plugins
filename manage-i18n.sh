#!/bin/bash

USAGE="$0 [init <locale>|extract|update <locale>|compile <locale>]"

if [[ $# -eq 0 || "$1" == '-h' || "$1" == '--help' ]]; then
    echo "$USAGE"
    exit 0
fi

ACTION="$1"
LOCALE="$2"

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

for plugin in $(find . -name setup.py -exec sh -c 'basename $(dirname $0)' {} \;); do
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
        pybabel extract -o "${TRANSLATIONS_DIR}/messages-js.pot" "indico_${plugin}" -k 'gettext' -k 'ngettext:1,2' -k '$T' -F ../babel-js.cfg
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
        pybabel compile -d "./indico_${plugin}/translations/" -l "$LOCALE"
    fi
    popd >/dev/null
done
