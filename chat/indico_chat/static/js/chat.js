/*
 * This file is part of Indico.
 * Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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
            $(this).siblings('.js-chat-details').slideToggle();
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
    }
})(window);
