// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2024 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

// eslint-disable-next-line import/unambiguous
window.setupOwncloudFilePickerWidget = ({filepickerUrl, fieldId}) => {
  window.addEventListener('message', message => {
    const iframe = document.querySelector('#owncloud_filepicker-file-picker');
    const submitButton = document.querySelector(
      '#attachment-owncloudfilepicker-form input[type=submit]'
    );

    if (
      iframe &&
      message.origin === filepickerUrl &&
      message.source === iframe.contentWindow &&
      message.data &&
      message.data.files
    ) {
      document.getElementById(`${fieldId}-files`).value = message.data.files.join('\n');
      submitButton.disabled = !message.data.ready || !message.data.files.length;
    }
  });
};
