/* This file is part of Indico.
 * Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

(function(global) {
    'use strict';

    global.eventChatInfo = function eventChatInfo() {
        var menu = null;
        var links = $('#chat-info-container').data('chatLinks');

        $('.chat-toggle-details').on('click', function(e) {
            e.preventDefault();
            $(this).siblings('.chat-details').slideToggle();
        });

        $('.js-chat-join').on('click', function(e) {
            e.preventDefault();
            var $this = $(this);
            var menuItems = {};
            $.each(links, function(i, link) {
                var action = link.link;
                action = action.replace(/\{server\}/g, $this.data('server'));
                action = action.replace(/\{room\}/g, $this.data('room'));
                menuItems[i] = {display: link.title, action: action};
            });

            if (menu && menu.isOpen()) {
                menu.close();
                if (menu._link == this) {
                    return;
                }
            }
            menu = new PopupMenu(menuItems, [$E(this)], 'categoryDisplayPopupList', true, false, null, null, true);
            menu._link = this;
            var pos = $this.offset();
            menu.open(pos.left - 3, pos.top + $this.height());
        });
    };

    global.eventManageChat = function eventManageChat() {

        $('.toggle-details').on('click', function(e) {
            e.preventDefault();
            var toggler = $(this);
            toggler.closest('tr').next('tr').find('.details-container').slideToggle({
                start: function() {
                    toggler.toggleClass('icon-next icon-expand');
                }
            });
        });

        $('.js-chat-remove-room').on('click', function(e) {
            e.preventDefault();
            var $this = $(this);
            var msg = $T('Do you really want to remove this chatroom from the event?');
            if ($this.data('numEvents') == 1) {
                msg += '<br>';
                if ($this.data('customServer')) {
                    msg += $T('Since it is on an external server, it will not be deleted on that server.');
                } else {
                    msg += $T('Since it is only used in this event, it will be deleted from the Jabber server, too!');
                }
            }
            new ConfirmPopup($T('Delete this chatroom?'), msg, function(confirmed) {
                if (!confirmed) {
                    return;
                }

                $('<form>', {
                    action: $this.data('href'),
                    method: 'post'
                }).appendTo('body').submit();
            }).open();
        });

        $('.js-chat-refresh-room').on('click', function(e) {
            e.preventDefault();
            $.ajax({
                url: $(this).data('href'),
                type: 'POST',
                dataType: 'json',
                complete: IndicoUI.Dialogs.Util.progress(),
                success: function(data) {
                    if (handleAjaxError(data)) {
                        return;
                    }
                    if (data.result == 'not-found') {
                        new AlertPopup($T('Chatroom not found'), $T('The chatroom does not exist on the Jabber server anymore. We recommend you to delete it chatroom from Indico as well.')).open();
                    } else if (data.result == 'changed') {
                        new AlertPopup($T('Chatroom updated'), $T('The chatroom data has been updated.'), function() {
                            window.location.href = window.location.href;
                        }).open();
                    }
                }
            });
        });
    };

    global.eventManageChatLogs = function eventManageChatLogs() {
        var container = $('#chat-log-display-container');
        var iframe = $('#chat-log-display');
        var materialWidget = $('#chat-log-material');
        var killProgress;
        var logParams;

        $('#chat-log-form').ajaxForm({
            dataType: 'json',
            beforeSubmit: function() {
                container.hide();
                materialWidget.hide();
                killProgress = IndicoUI.Dialogs.Util.progress();
            },
            success: function(data) {
                if (handleAjaxError(data)) {
                    return;
                }
                else if (!data.success) {
                    new AlertPopup($T('No logs available'), data.msg).open();
                    return;
                }
                var doc = iframe[0].contentWindow.document;
                doc.write(data.html);
                doc.close();
                logParams = data.params;
                $('#chat-log-material').find('input, button').prop('disabled', false);
                container.show();
                materialWidget.show();
            },
            complete: function() {
                killProgress();
            }
        });

        $('#chat-create-material').on('click', function(e) {
            e.preventDefault();
            var $this = $(this);
            var materialName = $('#chat-material-name').val().trim();
            if (!materialName) {
                return;
            }
            var params = $.extend({}, logParams, {
                material_name: materialName
            });
            $.ajax({
                url: $this.data('href'),
                type: 'POST',
                data: params,
                dataType: 'json',
                success: function(data) {
                    if (handleAjaxError(data)) {
                        return;
                    }
                    else if (!data.success) {
                        new AlertPopup($T('Could not create material'), data.msg).open();
                        return;
                    }
                    $('#chat-log-material').find('input, button').prop('disabled', true).blur();
                    new AlertPopup($T('Material created'), $T('The chat logs have been attached to the event.')).open();
                }
            });
        });

        var rangeWidget = $('#chat-log-range');
        rangeWidget.daterange({
            allowPast: true,
            fieldNames: ['start_date', 'end_date'],
            startDate: rangeWidget.data('startDate'),
            endDate: rangeWidget.data('endDate'),
            pickerOptions: {
                yearRange: 'c-1:c+1'
            }
        });
    };
})(window);
