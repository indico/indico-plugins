// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2020 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

const sanitizeRoomName = text => text.trim().replace(/[^\w-]+/g, '_');

$(() => {
  $('.vc-toolbar').dropdown({
    positioning: {
      level1: { my: 'right top', at: 'right bottom', offset: '0px 0px' },
    },
  });

  $('.vc-toolbar .action-make-owner').click(function () {
    const $this = $(this);

    $.ajax({
      url: $this.data('href'),
      method: 'POST',
      complete: IndicoUI.Dialogs.Util.progress(),
    })
      .done(result => {
        if (handleAjaxError(result)) {
          return;
        } else {
          location.reload();
        }
      })
      .fail(error => {
        handleAjaxError(error);
      });
  });

  $('body').on('indico:dialogOpen', ({target}) => {
    const element = target.querySelector('form[data-vc-type="vidyo"] #vc-name');

    if (!element) {
      return;
    }

    element.addEventListener('change', ({target}) => {
      const currentText = target.value;
      const sanitizedText = sanitizeRoomName(currentText);

      if (currentText !== sanitizedText) {
        target.classList.add('highlight');
        target.value = sanitizedText;
        setTimeout(() => target.classList.remove('highlight'), 1000);
      }
    });
  });
});
