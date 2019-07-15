// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2019 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import './main.scss';

(function(global) {
  const $t = $T.domain('chat');

  global.eventManageChat = function eventManageChat() {
    $('.toggle-details').on('click', function(e) {
      e.preventDefault();
      const toggler = $(this);
      toggler
        .closest('tr')
        .next('tr')
        .find('.details-container')
        .slideToggle({
          start() {
            toggler.toggleClass('icon-next icon-expand');
          },
        });
    });

    $('.js-chat-remove-room').on('click', function(e) {
      e.preventDefault();
      const $this = $(this);
      let msg = $t.gettext('Do you really want to remove this chatroom from the event?');
      if ($this.data('numEvents') == 1) {
        msg += '<br>';
        if ($this.data('customServer')) {
          msg += $t.gettext(
            'Since it is on an external server, it will not be deleted on that server.'
          );
        } else {
          msg += $t.gettext(
            'Since it is only used in this event, it will be deleted from the Jabber server, too!'
          );
        }
      }
      confirmPrompt(msg, $t.gettext('Delete this chatroom?')).then(function() {
        const form = $('<form>', {
          action: $this.data('href'),
          method: 'post',
        });
        const csrf = $('<input>', {
          type: 'hidden',
          name: 'csrf_token',
          value: $('#csrf-token').attr('content'),
        });
        form
          .append(csrf)
          .appendTo('body')
          .submit();
      });
    });

    $('.js-chat-refresh-room').on('click', function(e) {
      e.preventDefault();
      $.ajax({
        url: $(this).data('href'),
        type: 'POST',
        dataType: 'json',
        complete: IndicoUI.Dialogs.Util.progress(),
        success(data) {
          if (handleAjaxError(data)) {
            return;
          }
          if (data.result == 'not-found') {
            new AlertPopup(
              $t.gettext('Chatroom not found'),
              $t.gettext(
                'The chatroom does not exist on the Jabber server anymore. We recommend you to delete it chatroom from Indico as well.'
              )
            ).open();
          } else if (data.result == 'changed') {
            new AlertPopup(
              $t.gettext('Chatroom updated'),
              $t.gettext('The chatroom data has been updated.'),
              function() {
                window.location.href = window.location.href;
              }
            ).open();
          }
        },
      });
    });
  };

  global.eventManageChatLogs = function eventManageChatLogs() {
    const container = $('#chat-log-display-container');
    const iframe = $('#chat-log-display');
    const materialWidget = $('#chat-log-material');
    let killProgress, logParams;

    $('#chat-log-form').ajaxForm({
      dataType: 'json',
      beforeSubmit() {
        container.hide();
        materialWidget.hide();
        killProgress = IndicoUI.Dialogs.Util.progress();
      },
      error: handleAjaxError,
      success(data) {
        if (handleAjaxError(data)) {
          return;
        } else if (!data.success) {
          new AlertPopup($t.gettext('No logs available'), data.msg).open();
          return;
        }
        const doc = iframe[0].contentWindow.document;
        doc.write(data.html);
        doc.close();
        logParams = data.params;
        $('#chat-log-material')
          .find('input, button')
          .prop('disabled', false);
        container.show();
        materialWidget.show();
      },
      complete() {
        killProgress();
      },
    });

    $('#chat-create-material').on('click', function(e) {
      e.preventDefault();
      const $this = $(this);
      const materialName = $('#chat-material-name')
        .val()
        .trim();
      if (!materialName) {
        return;
      }
      const params = $.extend({}, logParams, {
        material_name: materialName,
      });
      $.ajax({
        url: $this.data('href'),
        type: 'POST',
        data: params,
        dataType: 'json',
        error: handleAjaxError,
        complete: IndicoUI.Dialogs.Util.progress(),
        success(data) {
          if (handleAjaxError(data)) {
            return;
          } else if (!data.success) {
            new AlertPopup($t.gettext('Could not create material'), data.msg).open();
            return;
          }
          $('#chat-log-material')
            .find('input, button')
            .prop('disabled', true)
            .blur();
          new AlertPopup(
            $t.gettext('Material created'),
            $t.gettext('The chat logs have been attached to the event.')
          ).open();
        },
      });
    });

    const rangeWidget = $('#chat-log-range');
    rangeWidget.daterange({
      allowPast: true,
      fieldNames: ['start_date', 'end_date'],
      startDate: rangeWidget.data('startDate'),
      endDate: rangeWidget.data('endDate'),
      pickerOptions: {
        yearRange: 'c-1:c+1',
      },
    });
  };
})(window);
