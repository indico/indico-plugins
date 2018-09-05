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


function _showTip(element, msg) {
    element.qtip({
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
}

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

function _validateAndFormatURL(url) {
    const $t = $T.domain('ursh');
    if (!url) {
        throw Error($t.gettext('Please fill in a URL to shorten'));
    }

    // if protocol is missing, prepend it
    if (url.startsWith(location.hostname)) {
        url = `${location.protocol}//${url}`;
    }

    // regular expression, because I.E. does not like the URL class
    // provides minimal validation, leaving the serious job to the server
    const re = RegExp(`^([\\d\\w]+:)//([^/ .]+(?:\\.[^/ .]+)*)(/.*)?$`);
    const urlTokens = url.match(re);
    if (!urlTokens) {
        throw Error($t.gettext('This does not look like a valid URL'));
    }

    // extract tokens
    let protocol = urlTokens[1];
    const hostname = urlTokens[2];
    const path = urlTokens[3] ? urlTokens[3] : '/';

    protocol = location.protocol;  // patch protocol to match server
    if (hostname !== location.hostname) {
        throw Error($t.gettext('Invalid host: only Indico URLs are allowed'));
    }

    return `${protocol}//${hostname}${path}`;
}

function _getUrshInput(input) {
    const inputURL = input.val().trim();
    input.val(inputURL);

    try {
        const formattedURL = _validateAndFormatURL(inputURL);
        input.val(formattedURL);
        return formattedURL;
    } catch (err) {
        _showTip(input, err.message);
        input.focus().select();
        return null;
    }
}

async function _handleUrshPageInput(evt) {
    evt.preventDefault();
    const $t = $T.domain('ursh');

    const input = $('#ursh-shorten-input');
    const originalURL = _getUrshInput(input);
    if (originalURL) {
        const result = await _makeUrshRequest(originalURL);
        if (result) {
            const outputElement = $('#ursh-shorten-output');
            $('#ursh-shorten-response-form').slideDown();
            outputElement.val(result);
            outputElement.select();
        } else {
            _showTip(input, $t.gettext('This does not look like a valid URL'));
            input.focus().select();
        }
    }
}

async function _handleUrshClick(evt) {
    evt.preventDefault();
    const originalURL = $(evt.target).attr('data-original-url');
    const result = await _makeUrshRequest(originalURL);
    $(evt.target).copyURLTooltip(result);
}

$(document)
    .on('click', '#ursh-shorten-button', _handleUrshPageInput)
    .on('keydown', '#ursh-shorten-input', (evt) => {
        if (evt.key === 'Enter') {
            _handleUrshPageInput(evt);
        }
    })
    .on('click', '.ursh-get', _handleUrshClick);
