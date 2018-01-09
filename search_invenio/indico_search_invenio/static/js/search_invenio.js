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

(function(global) {
    'use strict';

    var $t = $T.domain('search_invenio');

    global.invenioSearchResults = function invenioSearchResults(options) {
        // expected options: queryData, url, hasEvents, hasContribs

        var tabList = [];
        if (options.hasEvents) {
            tabList.push([$t.gettext('Events'), $E('results-events')]);
        }
        if (options.hasContribs) {
            tabList.push([$t.gettext('Contributions'), $E('results-contribs')]);
        }
        var tabCtrl = new JTabWidget(tabList);
        $E('result-tabs').set(tabCtrl.draw());
        $('#result-tabs > div').css({display: 'table', width: '100%'});

        $('#result-tabs').on('click', '.js-show-full-desc', function(e) {
            e.preventDefault();
            var desc = $(this).next().remove().text();
            $(this).parent().html(desc);
        });

        $('.js-load-more').on('click', function(e) {
            e.preventDefault();
            var $this = $(this);
            var collection = $this.data('collection');
            $.ajax({
                url: options.url,
                type: 'POST',
                data: $.extend({}, options.queryData, {
                    'offset': $this.data('offset'),
                    'search-collection': collection
                }),
                dataType: 'json',
                complete: IndicoUI.Dialogs.Util.progress(),
                success: function(data) {
                    if (handleAjaxError(data)) {
                        return;
                    }
                    var resultList = $this.closest('.js-results-container').find('.result-list');
                    var lastOld = resultList.children().last();
                    resultList.append(data.html);
                    $('html, body').animate({
                        scrollTop: lastOld.next().offset().top
                    }, 250);
                    lastOld.nextAll().effect('highlight', 1000);
                    $this.data('offset', data.offset);
                    if (!data.has_more) {
                        $this.parent().hide();
                    }
                }
            });
        });
    };
})(window);
