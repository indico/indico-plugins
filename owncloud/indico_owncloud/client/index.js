// This file is part of the Indico plugins.
// Copyright (C) 2014 - 2021 CERN
//
// The CERN Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License; see
// the LICENSE file for more details.

window.setupOwncloudFilePickerWidget = function setupOwncloudFilePickerWidget({
  filepicker_url,
  fieldId,
}) {
  window.addEventListener('message', function(message) {
    if (message.origin === filepicker_url) {
      document.getElementById(`${fieldId}-files`).value = message.data;
    }
  });
};
