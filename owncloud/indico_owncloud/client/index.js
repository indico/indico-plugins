// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2022 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

window.setupOwncloudFilePickerWidget = function setupOwncloudFilePickerWidget({
  filepicker_url,
  fieldId,
}) {
  window.addEventListener('message', function(message) {
    const iframe = document.querySelector('#owncloud_filepicker-file-picker');
    if (
      message.origin === filepicker_url &&
      message.source === iframe.contentWindow &&
      message.data &&
      message.data.files
    ) {
      document.getElementById(`${fieldId}-files`).value = message.data.files.join('\n');
    }
  });
};
