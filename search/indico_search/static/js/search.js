/* This file is part of Indico.
 * Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
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
    var $t = $T.domain('search');

    type('IntelligentSearchBox', ['RealtimeTextBox'], {
        _highlight: function(elem, token) {
            // Code for highlighting the matched part of the string
            var idx = elem.toLowerCase().indexOf(token.toLowerCase());
            if (idx >= 0) {
                var before = elem.slice(0, idx);
                var after = elem.slice(idx + token.length, elem.length);
                return [before, Html.span('highlight', elem.slice(idx, idx + token.length)), after];
            }
        },

        _truncateTitle: function(title) {
            var max = 27;
            if (title.length > max) {
                return title.slice(0, max / 2) + ' ... ' + title.slice(-max / 2);
            } else {
                return title;
            }
        },

        _showSuggestions: function(text, suggList, totalNumber) {
            var self = this;
            if (!this.suggestionBox) {
                // Create the suggestion box only once

                // totalNumber will change during time
                this.totalNumber = new WatchValue(totalNumber);
                this.suggestionList = Html.ul();

                var infoBox = Html.div('help', $t.gettext("Some category suggestions..."));

                // Create the suggestion box
                this.suggestionBox = Html.div({
                    style: {
                        position: 'absolute',
                        top: pixels(23),
                        left: 0
                    },
                    className: 'suggestion-box'
                },
                infoBox,
                this.suggestionList,
                $B(Html.div('other-results'), this.totalNumber, function(number) {
                    return number === 0 ? '' : number + ' ' + $t.gettext('other results - please write more...');
                }));

                this.container.append(this.suggestionBox);
            }

            // Prepare regular expression for highlighting
            var tokens = _.filter(escapeHTML(text).split(' '), function(t) {
                return t !== '';
            });
            var tokenRE = new RegExp('(' + tokens.join('|') + ')', 'gi');


            // Bind the list to the DOM element
            var counter = 0;

            $B(this.suggestionList, suggList, function(elem) {
                var titleHtml = escapeHTML(self._truncateTitle(elem.title)).replace(tokenRE, '<span class="highlight">$1</span>');
                var index = counter;
                var title = Html.span('title');
                title.dom.innerHTML = titleHtml;
                var pathText = Util.truncateCategPath(elem.path).join(' >> ');
                var path = Html.div('path', pathText);
                var liItem = Html.li({}, title, path);

                // Use mouse to control selector as well

                liItem.observeEvent('mouseover', function() {
                    if (self.selectorPos != index) {
                        self._clearSelector();
                        self.selectorPos = index;
                        self._setSelector();
                    }
                });

                liItem.observeClick(function() {
                    window.location = elem.url;
                });

                counter++;
                return liItem;
            });

            this.suggestionList.observeEvent('mouseout', function() {
                self._clearSelector();
                self.selectorPos = -1;
            });

            // Update
            this.totalNumber.set(totalNumber);
        },

        _hideSuggestions: function() {
            this.container.remove(this.suggestionBox);
            this.suggestionBox = null;
            this.selectorPos = -1;
            this.suggestions = null;
        },

        _retrieveOptions: function(expression) {
            var self = this;
            this.querying = true;

            $.ajax({
                url: self.searchUrl,
                type: 'GET',
                data: {
                    term: expression
                },
                dataType: 'json',
                complete: function() {
                    self.querying = false;
                    self.timeOfLastQuery = (new Date()).getTime();
                },
                success: function(data) {
                    if (handleAjaxError(data)) {
                        return;
                    }

                    if (data.results.length) {
                        self.suggestions = data.results;
                        self._showSuggestions(expression, data.results, data.count - data.results.length);
                    } else {
                        self._hideSuggestions();
                    }

                    var currentText = trim(self.get());

                    // if the text changed meanwhile and it
                    // is still long enough
                    if (currentText != expression && currentText.length > 1) {
                        // request
                        self._textTyped();
                    } else if (currentText.length <= 1) {
                        // if it is not long enough
                        self._hideSuggestions();
                    }
                }
            });
        },

        _getTimeSinceLastQuery: function() {
            var now = new Date();
            return now.getTime() - this.timeOfLastQuery;
        },

        _waitForRequestTime: function() {
            var self = this;
            if (!this.queuedRequest) {
                // This should never happen...
                return;
            }

            if (this._getTimeSinceLastQuery() > 1000) {
                this._textTyped();
                this.queuedRequest = false;
            } else {
                setTimeout(function() {
                    self._waitForRequestTime();
                }, 300);
            }
        },

        /*
         * Called each time a new character is typed
         * strips white spaces, and calls for a request if needed
         */
        _textTyped: function(key) {

            var self = this;
            var text = trim(this.get());

            if (text.length > 1) {

                // if we're not already querying and enough time has passed
                // since the last request
                if (!this.querying && this._getTimeSinceLastQuery() > 1000) {
                    this._retrieveOptions(text);
                } else if (!this.queuedRequest) {
                    // otherwise, if we can't do a request right now
                    // and no other request is queued
                    this.queuedRequest = true;

                    setTimeout(function() {
                        self._waitForRequestTime();
                    }, 300);
                }
            } else if (this.suggestionBox) {
                this._hideSuggestions();
            }
        },

        _openSelection: function(event) {
            if (this.selectorPos >= 0) {
                window.location = this.suggestions[this.selectorPos].url;
                return false;
            }
            return true;
        },

        /*
         * Move the selector (gray area) up or down
         */
        _moveSelector: function(direction) {

            if (this.suggestionBox) {
                var suggNum = this.suggestionList.length.get();

                if (this.selectorPos < 0) {
                    this.selectorPos = direction == 'down' ? 0 : suggNum - 1;
                } else {
                    this._clearSelector();
                    this.selectorPos += direction == 'up' ? -1 : 1;

                    if (this.selectorPos >= suggNum) {
                        this.selectorPos = -1;
                    } else if (this.selectorPos < 0) {
                        this.selectorPos = -1;
                    }
                }
            }

            this._setSelector();
        },

        _setSelector: function() {
            if (this.selectorPos >= 0) {
                this.suggestionList.item(this.selectorPos).dom.className = 'selected';
            }
        },

        _clearSelector: function() {
            if (this.selectorPos >= 0) {
                this.suggestionList.item(this.selectorPos).dom.className = '';
            }
        },

        isAnyItemSelected: function() {
            return this.selectorPos > 0;
        }

    }, function(args, container, searchUrl) {
        args.autocomplete = 'off';
        this.RealtimeTextBox(args);
        this.selectorPos = -1;
        this.querying = false;
        this.container = container;
        this.timeOfLastQuery = 0;
        this.searchUrl = searchUrl;

        var self = this;

        this.observe(function(key, event) {
            self._textTyped(key);
            return true;
        });

        this.observeOtherKeys(function(text, key, event) {
            if (key == 38 || key == 40) {
                self._moveSelector(key == 38 ? 'up' : 'down');
                return false;
            } else if (key == 27) {
                self._hideSuggestions();
                return false;
            } else if (key == 13) {
                return self._openSelection(event);
            } else {
                return true;
            }
        });

        $E(document.body).observeClick(function(event) {
            // Close box if a click is done outside of it

            /* for some unknown reason, onclick is called on the submit button,
             * as soon as the return key is pressed in any of the textfields.
             * To make it even better, onclick is called before onkeyup,
             * which forces us to do the last two checks.
             */

            if (self.suggestionBox && !self.suggestionList.ancestorOf($E(eventTarget(event))) && $E(eventTarget(event)) != self.input) {
                self._hideSuggestions();
            }
        });
    });


    $.widget('indico.search_tag', {
        options: {
            categ_title: 'Home',
            everywhere: true,
            search_category_url: '#',
            search_url: '#',
            form: null
        },

        _transition: function(title, no_check) {
            var $tag = this.$tag;
            var old_width = $tag.width();

            $tag.fadeTo('fast', 0.3).width('').find('.where').html(title);
            var new_width = $tag.width();

            // store target width
            $tag.fadeTo('fast', 0.5).width(old_width).data('target-width', new_width);

            $tag.animate({
                width: ((new_width < old_width) && !no_check) ? old_width : new_width
            }, 200, 'linear');

        },

        _create: function() {
            var self = this;

            var tag_template = _.template('<div class="search-tag">' +
            '<div class="cross">x</div>' +
            '<div class="where"><%= categ_title %></div>' +
            '</div>');

            var $tag = this.$tag = $(tag_template({
                categ_title: this.options.everywhere ? $t.gettext('Everywhere') : this.options.categ_title
            }));

            $(this.element).replaceWith($tag);
            var $where = $('.where', $tag);

            if (this.options.everywhere) {
                $tag.addClass('everywhere');
                $('.cross', this.$tag).hide();
            } else {
                $tag.addClass('in-category');
                $('.cross', this.$tag).show();
            }

            $('.cross', $tag).on('click', function() {
                self.search_everywhere();
            });

            var $parent = $tag.parent();

            $parent.on('mouseenter', '.search-tag.everywhere', function() {
                self.show_categ();
            });
            $parent.on('mouseover', '.search-tag.everywhere', function(e) {
                self.show_tip(e);
            });
            $parent.on('mouseleave', '.search-tag.everywhere', function() {
                $where.removeData('hasFocus');
            });
            $parent.on('click', '.search-tag.in-category-over', function() {
                self.confirm_tip();
            });
            $parent.on('mouseleave', '.search-tag.in-category-over', function() {
                self.back_to_everywhere();
            });
        },

        confirm_tip: function() {
            var $where = $('.where', this.$tag);
            var $tag = this.$tag;

            $tag.qtip('destroy');
            $where.fadeOut('fast', function() {
                $(this).fadeIn('fast');
            });

            this.$tag.addClass('in-category').removeClass('everywhere').removeClass('in-category-over');
            this.options.form.attr('action', this.options.search_category_url);

            // use target-width as search-tag may still be growing
            $tag.animate({
                width: $tag.data('target-width') + $('.cross', $tag).width() + 10
            }, 200, 'swing', function() {
                $('.cross', $tag).fadeIn('fast');
            });
        },

        search_everywhere: function() {
            $('.cross', this.$tag).hide();
            this.$tag.addClass('everywhere').removeClass('in-category');
            this._transition($t.gettext('Everywhere'), true);
            this.options.form.attr('action', this.options.search_url);
        },

        show_categ: function() {
            var $tag = this.$tag;
            var $where = $('.where', $tag);
            var self = this;
            $where.data('hasFocus', true);
            setTimeout(function() {
                if ($where.data('hasFocus')) {
                    self._transition(self.options.categ_title);
                    $tag.addClass('in-category-over');
                }
            }, 200);
        },

        show_tip: function(event) {
            this.$tag.qtip({
                content: format($t.gettext('Click to search inside <span class="label">{title}</span>'), {title: this.options.categ_title}),
                position: {
                    at: 'bottom center',
                    my: 'top center'
                },
                show: {
                    event: event.type,
                    ready: true
                }
            }, event);
        },

        back_to_everywhere: function() {
            var $where = $('.where', this.$tag);
            var self = this;

            this.$tag.removeClass('in-category-over');
            $where.removeData('hasFocus');
            setTimeout(function() {
                if (!$where.data('hasFocus')) {
                    self._transition($t.gettext('Everywhere'), true);
                    self.$tag.addClass('everywhere');
                }
            }, 200);
        }
    });


    global.categorySearchBox = function categorySearchBox(options) {
        // expected options: categoryNamesUrl, searchUrl, searchCategoryUrl, categoryName, isRoot
        var form = $('#category-search-form');
        var extra = form.find('.extra-options');
        var controls = form.find('.search-controls');
        var extraConfigured = false;
        $('#category-search-expand').on('click', function() {
            if (extra.is(':visible')) {
                extra.slideUp('fast');
            } else {
                extra.slideDown('fast');
                if (!extraConfigured) {
                    extraConfigured = true;
                    extra.css('display', 'table').position({
                        of: controls,
                        my: 'right top',
                        at: 'right bottom'
                    });
                }
            }
        });

        function verifyForm() {
            var startDate = $('#search-start_date').val();
            var endDate = $('#search-end_date').val();
            return (!startDate || Util.parseDateTime(startDate, IndicoDateTimeFormats.DefaultHourless)) &&
                    (!endDate || Util.parseDateTime(endDate, IndicoDateTimeFormats.DefaultHourless));
        }

        var intelligentSearchBox = new IntelligentSearchBox({
            name: 'search-phrase',
            id: 'search-phrase',
            style: {backgroundColor: 'transparent', outline: 'none'}
        }, $E('category-search-box'), options.categoryNamesUrl);

        $('#search-start_date, #search-end_date').datepicker();
        $E('search-phrase').replaceWith(intelligentSearchBox.draw());

        $('.search-button').on('click', function() {
            if (verifyForm()) {
                $('#category-search-form').submit();
            }
        });

        $('#search-phrase').on('keypress', function(e) {
            if (e.which == 13 && !intelligentSearchBox.isAnyItemSelected()) {
                if (verifyForm()) {
                    $('#category-search-form').submit();
                }
            }
        });

        if (!options.isRoot) {
            $('#category-search-form .search-button').before($('<div class="search-tag">'));
            $('.search-tag').search_tag({
                everywhere: true,
                categ_title: options.categoryName,
                form: $('#category-search-form'),
                search_url: options.searchUrl,
                search_category_url: options.searchCategoryUrl
            });
        }
    }
})(window);
