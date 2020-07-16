// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2020 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import './main.scss';

(function(global) {
  const $t = $T.domain('search');

  type(
    'IntelligentSearchBox',
    ['RealtimeTextBox'],
    {
      _highlight(elem, token) {
        // Code for highlighting the matched part of the string
        const idx = elem.toLowerCase().indexOf(token.toLowerCase());
        if (idx >= 0) {
          const before = elem.slice(0, idx);
          const after = elem.slice(idx + token.length, elem.length);
          return [before, Html.span('highlight', elem.slice(idx, idx + token.length)), after];
        }
      },

      _truncateTitle(title) {
        const max = 27;
        if (title.length > max) {
          return `${title.slice(0, max / 2)} ... ${title.slice(-max / 2)}`;
        } else {
          return title;
        }
      },

      _showSuggestions(text, suggList, totalNumber) {
        const self = this;
        if (!this.suggestionBox) {
          // Create the suggestion box only once

          // totalNumber will change during time
          this.totalNumber = new WatchValue(totalNumber);
          this.suggestionList = Html.ul();

          const infoBox = Html.div('help', $t.gettext('Some category suggestions...'));

          // Create the suggestion box
          this.suggestionBox = Html.div(
            {
              style: {
                position: 'absolute',
                top: pixels(23),
                left: 0,
              },
              className: 'suggestion-box',
            },
            infoBox,
            this.suggestionList,
            $B(Html.div('other-results'), this.totalNumber, function(number) {
              return number === 0
                ? ''
                : `${number} ${$t.gettext('other results - please write more...')}`;
            })
          );

          this.container.append(this.suggestionBox);
        }

        // Prepare regular expression for highlighting
        const tokens = _.filter(escapeHTML(text).split(' '), function(t) {
          return t !== '';
        });
        const tokenRE = new RegExp(`(${tokens.join('|')})`, 'gi');

        // Bind the list to the DOM element
        let counter = 0;

        $B(this.suggestionList, suggList, function(elem) {
          const titleHtml = escapeHTML(self._truncateTitle(elem.title)).replace(
            tokenRE,
            '<span class="highlight">$1</span>'
          );
          const index = counter;
          const title = Html.span('title');
          title.dom.innerHTML = titleHtml;
          const pathText = Util.truncateCategPath(elem.path).join(' >> ');
          const path = Html.div('path', pathText);
          const liItem = Html.li({}, title, path);

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

      _hideSuggestions() {
        this.container.remove(this.suggestionBox);
        this.suggestionBox = null;
        this.selectorPos = -1;
        this.suggestions = null;
      },

      _retrieveOptions(expression) {
        const self = this;
        this.querying = true;

        $.ajax({
          url: self.searchUrl,
          type: 'GET',
          data: {
            term: expression,
          },
          dataType: 'json',
          complete() {
            self.querying = false;
            self.timeOfLastQuery = new Date().getTime();
          },
          success(data) {
            if (handleAjaxError(data)) {
              return;
            }

            if (data.results.length) {
              self.suggestions = data.results;
              self._showSuggestions(expression, data.results, data.count - data.results.length);
            } else {
              self._hideSuggestions();
            }

            const currentText = trim(self.get());

            // if the text changed meanwhile and it
            // is still long enough
            if (currentText != expression && currentText.length > 1) {
              // request
              self._textTyped();
            } else if (currentText.length <= 1) {
              // if it is not long enough
              self._hideSuggestions();
            }
          },
        });
      },

      _getTimeSinceLastQuery() {
        const now = new Date();
        return now.getTime() - this.timeOfLastQuery;
      },

      _waitForRequestTime() {
        const self = this;
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
      _textTyped(key) {
        const self = this;
        const text = trim(this.get());

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

      _openSelection(event) {
        if (this.selectorPos >= 0) {
          window.location = this.suggestions[this.selectorPos].url;
          return false;
        }
        return true;
      },

      /*
       * Move the selector (gray area) up or down
       */
      _moveSelector(direction) {
        if (this.suggestionBox) {
          const suggNum = this.suggestionList.length.get();

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

      _setSelector() {
        if (this.selectorPos >= 0) {
          this.suggestionList.item(this.selectorPos).dom.className = 'selected';
        }
      },

      _clearSelector() {
        if (this.selectorPos >= 0) {
          this.suggestionList.item(this.selectorPos).dom.className = '';
        }
      },

      isAnyItemSelected() {
        return this.selectorPos > 0;
      },
    },
    function(args, container, searchUrl) {
      args.autocomplete = 'off';
      this.RealtimeTextBox(args);
      this.selectorPos = -1;
      this.querying = false;
      this.container = container;
      this.timeOfLastQuery = 0;
      this.searchUrl = searchUrl;

      const self = this;

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

        if (
          self.suggestionBox &&
          !self.suggestionList.ancestorOf($E(eventTarget(event))) &&
          $E(eventTarget(event)) != self.input
        ) {
          self._hideSuggestions();
        }
      });
    }
  );

  $.widget('indico.search_tag', {
    options: {
      categ_title: 'Home',
      everywhere: true,
      search_category_url: '#',
      search_url: '#',
      form: null,
    },

    _transition(title, no_check) {
      const $tag = this.$tag;

      $tag
        .fadeTo('fast', 0.3)
        .find('.where')
        .html(title);

      $tag
        .fadeTo('fast', 0.5)
    },

    _create() {
      const self = this;

      const tag_template = _.template(
        '<div class="search-tag">' +
          '<div class="where"><%= categ_title %></div>' +
          '<div class="cross">x</div>' +
          '</div>'
      );

      const $tag = (this.$tag = $(
        tag_template({
          categ_title: this.options.everywhere
            ? $t.gettext('Everywhere')
            : this.options.categ_title,
        })
      ));

      $(this.element).replaceWith($tag);
      const $where = $('.where', $tag);

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

      const $parent = $tag.parent();

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

    confirm_tip() {
      const $where = $('.where', this.$tag);
      const $tag = this.$tag;

      $tag.qtip('destroy');
      $where.fadeOut('fast', function() {
        $(this).fadeIn('fast');
      });

      this.$tag
        .addClass('in-category')
        .removeClass('everywhere')
        .removeClass('in-category-over');
      this.options.form.attr('action', this.options.search_category_url);

      $tag.animate(
        200,
        'swing',
        function() {
          $('.cross', $tag).fadeIn('fast');
        }
      );
    },

    search_everywhere() {
      $('.cross', this.$tag).hide();
      this.$tag.addClass('everywhere').removeClass('in-category');
      this._transition($t.gettext('Everywhere'), true);
      this.options.form.attr('action', this.options.search_url);
    },

    show_categ() {
      const $tag = this.$tag;
      const $where = $('.where', $tag);
      const self = this;
      $where.data('hasFocus', true);
      setTimeout(function() {
        if ($where.data('hasFocus')) {
          self._transition(self.options.categ_title);
          $tag.addClass('in-category-over');
        }
      }, 200);
    },

    show_tip(event) {
      this.$tag.qtip(
        {
          content: format($t.gettext('Click to search inside <span class="label">{title}</span>'), {
            title: this.options.categ_title,
          }),
          position: {
            at: 'bottom center',
            my: 'top center',
          },
          show: {
            event: event.type,
            ready: true,
          },
        },
        event
      );
    },

    back_to_everywhere() {
      const $where = $('.where', this.$tag);
      const self = this;

      this.$tag.removeClass('in-category-over');
      $where.removeData('hasFocus');
      setTimeout(function() {
        if (!$where.data('hasFocus')) {
          self._transition($t.gettext('Everywhere'), true);
          self.$tag.addClass('everywhere');
        }
      }, 200);
    },
  });

  global.categorySearchBox = function categorySearchBox(options) {
    // expected options: categoryNamesUrl, searchUrl, searchCategoryUrl, categoryName, isRoot
    const form = $('#category-search-form');
    const extra = form.find('.extra-options');
    const controls = form.find('.search-controls');
    let extraConfigured = false;
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
            at: 'right bottom',
          });
        }
      }
    });

    function verifyForm() {
      const startDate = $('#search-start_date').val();
      const endDate = $('#search-end_date').val();
      return (
        (!startDate || Util.parseDateTime(startDate, IndicoDateTimeFormats.DefaultHourless)) &&
        (!endDate || Util.parseDateTime(endDate, IndicoDateTimeFormats.DefaultHourless))
      );
    }

    const intelligentSearchBox = new IntelligentSearchBox(
      {
        name: 'search-phrase',
        id: 'search-phrase',
        style: {backgroundColor: 'transparent', outline: 'none'},
      },
      $E('category-search-box'),
      options.categoryNamesUrl
    );

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
        search_category_url: options.searchCategoryUrl,
      });
    }
  };
})(window);
