// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2019 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

$(function() {
  $('.vc-toolbar').dropdown({
    positioning: {
      level1: {my: 'right top', at: 'right bottom', offset: '0px 0px'},
    },
  });

  $('.vc-toolbar .action-make-owner').click(function() {
    const $this = $(this);

    $.ajax({
      url: $this.data('href'),
      method: 'POST',
      complete: IndicoUI.Dialogs.Util.progress(),
    })
      .done(function(result) {
        if (handleAjaxError(result)) {
          return;
        } else {
          location.reload();
        }
      })
      .fail(function(error) {
        handleAjaxError(error);
      });
  });
});
