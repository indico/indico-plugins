/* This file is part of Indico.
 * Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
 *
 * Indico is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 3 of the
 * License, or (at your option) any later version.
 *
 * Indico is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Indico; if not, see <http://www.gnu.org/licenses/>.
 */

import {handleAxiosError, indicoAxios} from 'indico/utils/axios';


async function _makeUrshRequest(originalURL) {
    const urshEndpoint = '/ursh';

    let response;
    try {
        response = await indicoAxios.post(urshEndpoint, {
            original_url: originalURL,
        });
    } catch (error) {
        handleAxiosError(error);
        return;
    }

    return response.data.url;
}

function _patchURL(url) {
    if (url.startsWith(window.location.hostname)) {
        return `${window.location.protocol}//${url}`;
    } else {
        return url;
    }
}

function _validateURL(url) {
    const re = RegExp(`^(${window.location.protocol}//)?${window.location.hostname}/`);
    return re.test(url);
}

function _getUrshInput() {
    const $t = $T.domain('ursh');
    const input = $('#ursh-shorten-input');
    const originalURL = input.val().trim();

    const tip = ((msg) => {
        input.qtip({
            content: {
                text: msg
            },
            hide: {
                event: 'mouseleave',
                fixed: true,
                delay: 700
            },
            show: {
                event: false,
                ready: true
            }
        });
    });

    if (!originalURL) {
        tip($t.gettext('Please fill in a URL to shorten'));
        input.focus();
        return null;
    } else if (!_validateURL(originalURL)) {
        tip($t.gettext('This does not look like a valid URL'));
        input.focus();
        return null;
    } else {
        const patchedURL = _patchURL(originalURL);
        input.val(patchedURL);
        return patchedURL;
    }
}

$(document)
    .on('click', '#ursh-shorten-button', async (evt) => {
        evt.preventDefault();
        const originalURL = _getUrshInput();
        if (originalURL) {
            const result = await _makeUrshRequest(originalURL);
            const outputElement = $('#ursh-shorten-output');
            $('#ursh-shorten-response-form').slideDown();
            outputElement.val(result);
            outputElement.select();
        }
    })
    .on('click', '.ursh-get', async (evt) => {
        evt.preventDefault();
        const originalURL = $(evt.target).attr('data-original-url');
        const result = await _makeUrshRequest(originalURL);
        $(evt.target).copyURLTooltip(result).show();
    });
