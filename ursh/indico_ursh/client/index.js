// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2020 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

/* global $T:false */

import {handleAxiosError, indicoAxios} from 'indico/utils/axios';

const $t = $T.domain('ursh');

function _showTip(element, msg, hideEvent = 'unfocus') {
  element.qtip({
    content: {
      text: msg,
    },
    hide: {
      event: hideEvent,
      fixed: true,
      delay: 700,
    },
    show: {
      event: false,
      ready: true,
    },
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
  const hostname = urlTokens[2];
  const path = urlTokens[3] ? urlTokens[3] : '/';

  const protocol = location.protocol; // patch protocol to match server
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
  const originalURL = evt.target.dataset.originalUrl;
  const result = await _makeUrshRequest(originalURL);
  $(evt.target).copyURLTooltip(result, 'unfocus');
}

function _validateUrshCustomShortcut(shortcut) {
  return shortcut.length >= 5;
}

$(document)
  .on('click', '#ursh-shorten-button', _handleUrshPageInput)
  .on('keydown', '#ursh-shorten-input', evt => {
    if (evt.key === 'Enter') {
      _handleUrshPageInput(evt);
    }
  })
  .on('click', '.ursh-get', _handleUrshClick)
  .on('input', '#ursh-custom-shortcut-input', evt => {
    const value = $(evt.target).val();
    $('#ursh-custom-shortcut-submit-button').prop('disabled', !_validateUrshCustomShortcut(value));
  })
  .on('mouseenter', '#ursh-custom-shortcut-submit-button', evt => {
    if (evt.target.disabled) {
      _showTip(
        $(evt.target),
        $t.gettext('Please check that the shortcut is correct'),
        'mouseleave'
      );
    }
  });

$(document).ready(() => {
  // keep dropdown menu open when clicking on an entry
  $('.ursh-dropdown')
    .next('ul')
    .find('li a')
    .on('menu_select', () => true);
});
