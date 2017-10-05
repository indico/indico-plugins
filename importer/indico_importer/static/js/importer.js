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

(function() {
    var $t = $T.domain('importer');

    /** Namespace for importer utility functions and variables */
    var ImporterUtils = {
         /** Possible extensions for resources */
         resourcesExtensionList : {'pdf' : 1, 'doc' : 1, 'docx' : 1, 'ppt' : 1},

         /** Maps importer name into report number system name */
         reportNumberSystems: {"invenio" : "cds",
                               "dummy" : "Dummy"},

         /** Short names of the months. */
         shortMonthsNames : [$t.gettext("Jan"),
                             $t.gettext("Feb"),
                             $t.gettext("Mar"),
                             $t.gettext("Apr"),
                             $t.gettext("May"),
                             $t.gettext("Jun"),
                             $t.gettext("Jul"),
                             $t.gettext("Aug"),
                             $t.gettext("Sep"),
                             $t.gettext("Oct"),
                             $t.gettext("Nov"),
                             $t.gettext("Dec")],
        /**
         * Converts minutes to the hour string (format HH:MM).
         * If minutes are greater than 1440 (24:00) value '00:00' is returned.
         * @param minutes Integer containing number of minutes.
         * @return hour string.
         */
         minutesToTime: function(minutes) {
            if (minutes <= 1440) {
                return ((minutes - minutes % 60)/ 60 < 10 ? "0" + (minutes  - minutes % 60) / 60:(minutes  - minutes % 60) / 60)
                         + ":" + (minutes % 60 < 10 ? "0" + minutes % 60:minutes % 60);
            } else {
                return '00:00';
            }
        },

        /**
         * Standard sorting function comparing start times of events.
         * @param a first event.
         * @param b second event.
         * @return true if the first event starts later than the second. If not false.
         */
        compareStartTime: function (a, b) {
            return a.startDate.time > b.startDate.time;
        },

        /**
         * Returns array containing sorted keys of the dictionary.
         * @param dict Dictionary to be sorted.
         * @param sortFunc Function comparing keys of the dictionary.
         * @return Array containg sorted keys.
         */
        sortedKeys: function(dict, sortFunc) {
            var array = [];
            each(dict, function(item) {
                array.push(item);
            });
            return array.sort(sortFunc);
        },

        /**
         * Checks if a dictionary contains empty person data.
         */
        isPersonEmpty: function(person) {
            return !person || (!person.firstName && !person.familyName);
        },

        /**
         * Send a POST request to indico.
         * @param url The url where to post the data.
         * @param data The data to POST.
         * @param onSuccess Called when the request succeeds.
         * @param onError Called when an error is encountered while performing the request.
         */
        _sendRequest: function(url, args, onSuccess, onError) {
            $.ajax({
                // There's no synchronisation on the server side yet thus make sure requests are sent serially
                async: false,
                url: url,
                method: 'POST',
                data: args,
                success: function(data, textStatus) {
                    if ($.isFunction(onSuccess)) {
                        onSuccess(data, textStatus);
                    }
                },
                error: function(xhr) {
                    if ($.isFunction(onError)) {
                        onError({
                            title: $t.gettext('Something went wrong'),
                            message: '{0} ({1})'.format(xhr.statusText.toLowerCase(), xhr.status),
                            suggest_login: false,
                            report_url: null
                        });
                    }
                }
            });
        }
    };


    /**
     * Imitates dictionary with keys ordered by the time element insertion.
     */
    type("QueueDict", [], {

            /**
             * Inserts new element to the dictionary. If element's value is null removes an element.
             * @param key element's key
             * @param value element's value
             */
            set: function(key, value) {
                var existed = false;
                for (var i in this.keySequence) {
                    if (key == this.keySequence[i]) {
                        existed = true;
                        if (value !== null) {
                            this.keySequence[i] = value;
                        } else {
                            this.keySequence.splice(i, 1);
                        }
                    }
                }
                if (!existed) {
                    this.keySequence.push(key);
                }
                this.dict[key] = value;
            },

            /**
             * Gets list of keys. The list is sorted by an element insertion time.
             */
            getKeys: function() {
                return this.keySequence;
            },

            /**
             * Gets elements with the specified key.
             */
            get: function(key) {
                return this.dict[key];
            },

            /**
             * Gets list of values. The list is sorted by an element insertion time.
             */
            getValues: function() {
                var tmp = [];
                for (var index in this.keySequence) {
                    tmp.push(this.get(this.keySequence[index]));
                }
                return tmp;
            },

            /**
             * Returns number of elements in the dictionary.
             */
            getLength: function() {
                return this.keySequence.length;
            },

            /**
             * Removes all elements from the dictionary
             */
            clear: function() {
                this.keySequence = [];
                this.dict = {};
            },

            /**
             * Moves the key one position towards the begining of the key list.
             */
            shiftTop: function(idx) {
                if (idx > 0) {
                    var tmp = this.keySequence[idx];
                    this.keySequence[idx] = this.keySequence[idx - 1];
                    this.keySequence[idx - 1] = tmp;
                }
            },

            /**
             * Moves the key one position towards the end of the key list.
             */
            shiftBottom: function(idx) {
                if (idx < this.keySequence.length - 1) {
                    var tmp = this.keySequence[idx];
                    this.keySequence[idx] = this.keySequence[idx + 1];
                    this.keySequence[idx + 1] = tmp;
                }
            }
        },

        function() {
            this.keySequence = [];
            this.dict = {};
        }
    );


    type("ImportDialog", ["ExclusivePopupWithButtons", "PreLoadHandler"], {
            _preload: [
                /** Loads a list of importers from the server */
                function(hook) {
                    var self = this;
                    $.ajax({
                        url: build_url(ImporterPlugin.urls.importers, {}),
                        type: 'GET',
                        dataType: 'json',
                        success: function(data) {
                            if (handleAjaxError(data)) {
                                return;
                            }
                            self.importers = data;
                            hook.set(true);
                        }
                    });
                }
            ],

            /**
             * Hides importer list and timetable list and shows information to type a new query.
             */
            _hideLists: function() {
                this.importerList.hide();
                this.timetableList.hide();
                this.emptySearchDiv.show();
            },

            /**
             * Shows importer list and timetable list and hides information to type a new query.
             */
            _showLists: function() {
                this.importerList.show();
                this.timetableList.refresh();
                this.timetableList.show();
                this.emptySearchDiv.hide();
            },

            /**
             * Draws the content of the dialog.
             */
            drawContent : function() {
                var self = this;
                var search = function() {
                    self.importerList.search(query.dom.value, importFrom.dom.value, 20, [function() {
                        self._showLists();
                    }]);
                };
                var searchButton = Html.input('button', {}, $t.gettext('search'));
                searchButton.observeClick(search);
                var importFrom = Html.select({});
                for (var importer in this.importers)
                    importFrom.append(Html.option({value:importer}, this.importers[importer]));
                var query = Html.input('text', {});
                query.observeEvent('keypress', function(event) {
                    if (event.keyCode == 13) {
                        search();
                    }
                });

                this.emptySearchDiv = new PresearchContainer(this.height, function() {
                    self._showLists();
                });

                /** Enables insert button whether some elements are selected at both importer and timetable list */
                var _observeInsertButton =  function() {
                    if (self.importerList.getSelectedList().getLength() > 0 && self.timetableList.getSelection()) {
                        self.insertButton.disabledButtonWithTooltip('enable');
                    } else {
                        self.insertButton.disabledButtonWithTooltip('disable');
                    }
                };
                this.importerList = new ImporterList([],
                        {"height" : this.height - 80, "width" : this.width / 2 - 20, "cssFloat" : "left"},
                        'entryList', 'entryListSelected', true, _observeInsertButton);
                this.timetableList = new TableTreeList(this.topTimetable,
                        {"height" : this.height - 80, "width" : this.width / 2 - 20, "cssFloat" : "right"},
                        'treeList', 'treeListDayName', 'treeListEntry', true, _observeInsertButton);
                return Html.div({},
                        Html.div({className:'importDialogHeader', style:{width:pixels(this.width * 0.9)}}, query, searchButton, ' ', $t.gettext("in"), ' ', importFrom),
                        this.emptySearchDiv.draw(), this.importerList.draw(), this.timetableList.draw());
            },

            _getButtons: function() {
                var self = this;
                return [
                    [$t.gettext('Proceed...'), function() {
                        var destination = self.timetableList.getSelection();
                        var entries = self.importerList.getSelectedList();
                        var importer = self.importerList.getLastImporter();
                        new ImporterDurationDialog(entries, destination,  self.confId, self.timetable, importer, function(redirect) {
                            if (!redirect) {
                                self._hideLists();
                                self.timetableList.clearSelection();
                                self.importerList.clearSelection();
                                self.emptySearchDiv.showAfterSearch();
                            }
                            self.reloadPage = true;
                        });
                    }],
                    [$t.gettext('Close'), function() {
                        self.close();
                    }]
                ];
            },

            draw: function() {
                this.insertButton = this.buttons.eq(0);
                this.insertButton.disabledButtonWithTooltip({
                    tooltip: $t.gettext('Please select contributions to be added and their destination.'),
                    disabled: true
                });
                return this.ExclusivePopupWithButtons.prototype.draw.call(this, this.drawContent());
            },

            _onClose: function(evt) {
                if (this.reloadPage) {
                    location.reload();
                    IndicoUI.Dialogs.Util.progress();
                }
                return self.ExclusivePopupWithButtons.prototype._onClose.call(this, evt);
            }
        },

        /**
         * Importer's main tab. Contains inputs for typing a query and select the importer type.
         * After making a query imported entries are displayed at the left side of the dialog, while
         * at the right side list of all entries in the event's timetable will be shown. User can add
         * new contributions to the timetable's entry by simply selecting them and clicking at 'proceed'
         * button.
         * @param timetable Indico timetable object. If it's undefined constructor will try to fetch
         * window.timetable object.
         */
        function(timetable) {
            var self = this;
            this.ExclusivePopupWithButtons($t.gettext("Import Entries"));
            this.timetable = timetable?timetable:window.timetable;
            this.topTimetable = this.timetable.parentTimetable ? this.timetable.parentTimetable : this.timetable;
            this.confId = this.topTimetable.contextInfo.id;
            this.height = document.body.clientHeight - 200;
            this.width = document.body.clientWidth - 200;
            this.PreLoadHandler(
                this._preload,
                function() {
                    self.open();
                });
            this.execute();
        }
    );


    type("PresearchContainer", [], {
            /**
             * Shows a widget.
             */
            show: function() {
                this.contentDiv.dom.style.display = 'block';
            },

            /**
             * Hides a widget.
             */
            hide: function() {
                this.contentDiv.dom.style.display = 'none';
            },

            /**
             * Changes a content of the widget. It should be used after making a first successful import.
             */
            showAfterSearch: function() {
                this.firstSearch.dom.style.display = 'none';
                this.afterSearch.dom.style.display = 'inline';
            },

            draw: function() {
                this.firstSearch = Html.span({style:{display:"inline"}}, $t.gettext("Please type your search phrase and press 'search'."));
                var hereLink = Html.span({className: 'fake-link'}, $t.gettext("here"));
                hereLink.observeClick(this.afterSearchAction);
                this.afterSearch = Html.span(
                    {style: {display: 'none'}},
                    $t.gettext("Your entries were inserted successfully. Please specify a new query or click"), ' ', hereLink, ' ', $t.gettext("to see the previous results.")
                );
                this.contentDiv = Html.div({className:'presearchContainer', style:{"height" : pixels(this.height - 130)}}, this.firstSearch, this.afterSearch);
                return this.contentDiv;
            }
        },

        /**
         * A placeholder for importer and timetable list widgets. Contains user's tips about what to do right now.
         * @param widget's height
         * @param function executed afer clicking 'here' link.
         */
        function(height, afterSearchAction) {
            this.height = height;
            this.afterSearchAction = afterSearchAction;
        }
    );


    type("ImporterDurationDialog", ["ExclusivePopupWithButtons", "PreLoadHandler"], {
            _preload: [
                /**
                 * Fetches the default start time of the first inserted contribution.
                 * Different requests are used for days, sessions and contributions.
                 */
                function(hook) {
                    var self = this;
                    //If the destination is a contribution, simply fetch the contribution's start time.
                    if (this.destination.entryType == 'Contribution') {
                        self.info.set("startTime", this.destination.startDate.time.substr(0, 5));
                        hook.set(true);
                    } else {
                        var url;
                        if (this.destination.entryType == 'Day') {
                            url = build_url(ImporterPlugin.urls.day_end_date, {
                                importer_name: 'indico_importer',
                                confId: this.confId
                            });
                        }
                        if (this.destination.entryType == 'Session') {
                            url = build_url(ImporterPlugin.urls.block_end_date, {
                                importer_name: 'indico_importer',
                                confId: this.confId,
                                entry_id: this.destination.scheduleEntryId
                            });
                        }
                        $.ajax({
                            url: url,
                            data: {
                                sessionId: this.destination.sessionId,
                                slotId: this.destination.sessionSlotId,
                                selectedDay: this.destination.startDate.date.replace(/-/g, '/')
                            },
                            success: function(data) {
                                self.info.set('startTime', data);
                                hook.set(true);
                            }
                        });
                    }
                }
            ],

            drawContent: function() {
                var durationField = Html.input('text', {}, this.destination.contribDuration?this.destination.contribDuration:20);
                var timeField = Html.input('text', {});
                var redirectCheckbox = Html.input('checkbox', {});

                this.parameterManager.add(durationField, 'unsigned_int', false);
                this.parameterManager.add(timeField, 'time', false);

                $B(this.info.accessor("duration"), durationField);
                $B(timeField, this.info.accessor("startTime"));
                $B(this.info.accessor("redirect"), redirectCheckbox);

                return IndicoUtil.createFormFromMap([
                    [$t.gettext("Duration time of every inserted contribution:"), durationField],
                    [$t.gettext("Start time of the first contribution:"), timeField],
                    [$t.gettext("Show me the destination:"), redirectCheckbox]
                ]);
            },

            /* Redirect to the timetable containing the created entry. */
            _performRedirect: function() {
                var fragment = this.destination.startDate.date.replace(/-/g, '');
                if (this.destination.entryType == 'Session') {
                    fragment += '.' + this.destination.id;
                }
                location.hash = fragment;
                location.reload(); // Reload needed since only the fragment is changed
            },

            _getUrl: function(eventId, day, destination) {
                var params = {
                    'confId': eventId
                };
                if (destination.entryType == 'Day') {
                    params.day = day;
                    return build_url(ImporterPlugin.urls.add_contrib, params);
                }
                if (destination.entryType == 'Session') {
                    params.day = day;
                    params.session_block_id = destination.sessionSlotId;
                    return build_url(ImporterPlugin.urls.add_contrib, params);
                }
                if (destination.entryType == 'Contribution') {
                    params.contrib_id = destination.contributionId;
                    return build_url(ImporterPlugin.urls.create_subcontrib_rest, params);
                }
            },

            _personLinkData: function(entry) {
                var authorType = {
                    'none': 0,
                    'primary': 1,
                    'secondary': 2
                };
                var linkDataEntry = function(author, authorType, speaker) {
                    if (speaker === undefined) {
                        speaker = !!author.isSpeaker;
                    }
                    return $.extend({
                        'authorType': authorType,
                        'isSpeaker': speaker,
                        'isSubmitter': false
                    }, author);
                };
                var linkData = [];
                if (!ImporterUtils.isPersonEmpty(entry.primaryAuthor)) {
                    linkData.push(linkDataEntry(entry.primaryAuthor, authorType.primary));
                }
                if (!ImporterUtils.isPersonEmpty(entry.secondaryAuthor)) {
                    linkData.push(linkDataEntry(entry.secondaryAuthor, authorType.secondary));
                }
                if (!ImporterUtils.isPersonEmpty(entry.speaker)) {
                    linkData.push(linkDataEntry(entry.speaker, authorType.none, true));
                }

                if (!this.timetable.eventInfo.isConference) {
                    // Only speakers are allowed in this type of event
                    var speakersLinkData = [];
                    $.each(linkData, function() {
                        if (this.isSpeaker) {
                            this.authorType = authorType.none;
                            speakersLinkData.push(this);
                        }
                    });
                    return speakersLinkData;
                }
                return linkData;
            },

            _addContributionMaterial: function(title, link_url, eventId, contributionId, subContributionId) {
                var requestUrl;
                if (subContributionId !== undefined) {
                    requestUrl = build_url(ImporterPlugin.urls.add_link, {
                        'confId': eventId,
                        'contrib_id': contributionId,
                        'subcontrib_id': subContributionId,
                        'object_type': 'subcontribution'
                    });
                } else {
                    requestUrl = build_url(ImporterPlugin.urls.add_link, {
                        'confId': eventId,
                        'contrib_id': contributionId,
                        'object_type': 'contribution'
                    });
                }
                var params = {
                    'csrf_token': $('#csrf-token').attr('content'),
                    'link_url': link_url,
                    'title': title,
                    'folder': '__None',
                    'acl': '[]'
                };
                ImporterUtils._sendRequest(requestUrl, params);
            },

            _addReference: function(type, value, eventId, contributionId, subContributionId) {
                var url;
                if (subContributionId !== undefined) {
                    url = build_url(ImporterPlugin.urls.create_subcontrib_reference_rest, {
                        'confId': eventId,
                        'contrib_id': contributionId,
                        'subcontrib_id': subContributionId
                    });
                } else {
                    url = build_url(ImporterPlugin.urls.create_contrib_reference_rest, {
                        'confId': eventId,
                        'contrib_id': contributionId
                    });
                }
                var params = {
                    'csrf_token': $('#csrf-token').attr('content'),
                    'type': type,
                    'value': value
                };
                ImporterUtils._sendRequest(url, params);
            },

            _getButtons: function() {
                var self = this;
                return [
                    [$t.gettext('Insert'), function() {
                        if (!self.parameterManager.check()) {
                            return;
                        }
                        //Converts string containing contribution's start date(HH:MM) into a number of minutes.
                        //Using parseFloat because parseInt('08') = 0.
                        var time = parseFloat(self.info.get('startTime').split(':')[0]) * 60 + parseFloat(self.info.get('startTime').split(':')[1]);
                        var duration = parseInt(self.info.get('duration'));
                        //If last contribution finishes before 24:00
                        if (time + duration * self.entries.getLength() <= 1440) {
                            var hasError = false;
                            var killProgress = IndicoUI.Dialogs.Util.progress();
                            var errorCallback = function(error) {
                                if (error) {
                                    hasError = true;
                                    showErrorDialog(error);
                                }
                            };
                            var date = self.destination.startDate.date.replace(/-/g, '/');
                            var args = [];
                            each(self.entries.getValues(), function(entry) {
                                entry = entry.getAll();
                                var timeStr = ImporterUtils.minutesToTime(time);
                                var params = {
                                    'csrf_token': $('#csrf-token').attr('content'),
                                    'title': entry.title ? entry.title : "Untitled",
                                    'description': entry.summary,
                                    'duration': [duration, 'minutes'],
                                    'references': '[]'
                                };
                                if (self.destination.entryType == 'Contribution') {
                                    $.extend(params, {
                                        'speakers': Json.write(self._personLinkData(entry))
                                    });
                                } else {
                                    $.extend(params, {
                                        'time': timeStr,
                                        'person_link_data': Json.write(self._personLinkData(entry)),
                                        'location_data': '{"address": "", "inheriting": true}',
                                        'type': '__None'
                                    });
                                }
                                var url = self._getUrl(self.confId, date, self.destination);
                                var successCallback = function(result) {
                                    var materials = entry.materials || {};
                                    var reportNumbers = entry.reportNumbers || [];
                                    var reportNumbersLabel = ImporterUtils.reportNumberSystems[self.importer];
                                    if (self.destination.entryType == 'Contribution') {
                                        $.each(materials, function(title, url) {
                                            self._addContributionMaterial(title, url, result.event_id,
                                                                          result.contribution_id, result.id);
                                        });
                                        $.each(reportNumbers, function(idx, number) {
                                            self._addReference(reportNumbersLabel, number, self.confId,
                                                               result.contribution_id, result.id);
                                        });
                                    } else {
                                        var contribution = result.entries[0].entry;
                                        $.each(materials, function(title, url) {
                                            self._addContributionMaterial(title, url, self.confId, contribution.contributionId);
                                        });
                                        $.each(reportNumbers, function(idx, number) {
                                            self._addReference(reportNumbersLabel, number, self.confId, contribution.contributionId);
                                        });
                                    }
                                };
                                ImporterUtils._sendRequest(url, params, successCallback, errorCallback);
                                time += duration;
                            });
                            if (self.successFunction) {
                                self.successFunction(self.info.get('redirect'));
                            }
                            if (self.info.get('redirect')) {
                                self._performRedirect();
                            }
                            self.close();
                            killProgress();
                        }
                        else {
                            new WarningPopup("Warning", "Some contributions will end after 24:00. Please modify start time and duration.").open();
                        }
                    }],
                    [$t.gettext('Cancel'), function() {
                        self.close();
                    }]
                ];
            },

            draw: function() {
                return this.ExclusivePopupWithButtons.prototype.draw.call(this, this.drawContent());
            }
        },

        /**
         * Dialog used to set the duration of the each contribution and the start time of the first on.
         * @param entries List of imported entries
         * @param destination Place into which entries will be inserted
         * @param confId Id of the current conference
         * @param timetable Indico timetable object of the current conference.
         * @param importer Name of the used importer.
         * @param successFunction Function executed after inserting events.
         */
        function(entries, destination, confId, timetable, importer, successFunction) {
            var self = this;
            this.ExclusivePopupWithButtons($t.gettext('Adjust entries'));
            this.confId = confId;
            this.entries = entries;
            this.destination = destination;
            this.timetable = timetable;
            this.successFunction = successFunction;
            this.importer = importer;
            this.parameterManager = new IndicoUtil.parameterManager();
            this.info = new WatchObject();
            this.PreLoadHandler(
                this._preload,
                function() {
                    self.open();
                });
            this.execute();
        }
    );

    type("ImporterListWidget", ["SelectableListWidget"], {
            /**
             * Removes all entries from the list
             */
            clearList: function() {
                this.SelectableListWidget.prototype.clearList.call(this);
                this.recordDivs = [];
            },

            /**
             * Removes all selections.
             */
            clearSelection: function() {
                this.SelectableListWidget.prototype.clearSelection.call(this);
                this.selectedObserver(this.selectedList);
            },

            /**
             * Returns number of entries in the list.
             */
            getLength: function() {
                return this.recordDivs.length;
            },

            /**
             * Returns the last query.
             */
            getLastQuery: function() {
                return this.lastSearchQuery;
            },

            /**
             * Returns the name of the last used importer.
             */
            getLastImporter: function() {
                return this.lastSearchImporter;
            },

            /**
             * Returns true if it's possible to import more entries, otherwise false.
             */
            isMoreToImport: function() {
                return this.moreToImport;
            },

            /**
             * Base search method. Sends a query to the importer.
             * @param query A query string send to the importer
             * @param importer A name of the used importer.
             * @param size Number of fetched objects.
             * @param successFunction Method executed after successful request.
             * @param callbacks List of methods executed after request (doesn't matter if successful).
             */
            _searchBase: function(query, importer, size, successFunc, callbacks) {
                var self = this;
                $.ajax({
                    // One more entry is fetched to be able to check if it's possible to fetch
                    // more entries in case of further requests.
                    url: build_url(ImporterPlugin.urls.import_data, {'importer_name': importer,
                                                                     'query': query,
                                                                     'size': size + 1}),
                    type: 'POST',
                    dataType: 'json',
                    complete: IndicoUI.Dialogs.Util.progress(),
                    success: function(data) {
                        if (handleAjaxError(data)) {
                            return;
                        }
                        successFunc(data.records);
                        _.each(callbacks, function(callback) {
                            callback();
                        });
                    }
                });
                //Saves last request data
                this.lastSearchImporter = importer;
                this.lastSearchQuery = query;
                this.lastSearchSize = size;
            },

            /**
             * Clears the list and inserts new imported entries.
             * @param query A query string send to the importer
             * @param importer A name of the used importer.
             * @param size Number of fetched objects.
             * @param callbacks List of methods executed after request (doesn't matter if successful).
             */
            search: function(query, importer, size, callbacks) {
                var self = this;
                var successFunc = function(result) {
                    self.clearList();
                    var importedRecords = 0;
                    self.moreToImport = false;
                    for (var record in result) {
                        //checks if it's possible to import more entries
                        if (size == importedRecords++) {
                            self.moreToImport = true;
                            break;
                        }
                        self.set(record, $O(result[record]));
                    }
                };
                this._searchBase(query, importer, size, successFunc, callbacks);
            },

            /**
             * Adds more entries to the current list. Uses previous query and importer.
             * @param size Number of fetched objects.
             * @param callbacks List of methods executed after request (doesn't matter if successful).
             */
            append: function(size, callbacks) {
                var self = this;
                var lastLength = this.getLength();
                var successFunc = function(result) {
                    var importedRecords = 0;
                    self.moreToImport = false;
                    for (var record in result) {
                        // checks if it's possible to import more entries
                        if (lastLength + size == importedRecords) {
                            self.moreToImport = true;
                            break;
                        }
                        // Some entries are already in the list so we don't want to insert them twice.
                        // Entries with indexes greater or equal lastLength - 1 are not yet in the list.
                        if (lastLength - 1 < importedRecords) {
                            self.set(record, $O(result[record]));
                        }
                        ++importedRecords;
                    }
                };
                this._searchBase(this.getLastQuery(), this.getLastImporter(), this.getLength() + size, successFunc, callbacks);
            },

            /**
             * Extracts person's name, surname and affiliation
             */
            _getPersonString: function(person) {
                return person.firstName + " " + person.familyName +
                    (person.affiliation? " (" + person.affiliation + ")" : "");
            },

            /**
             * Draws sequence number attached to the item div
             */
            _drawSelectionIndex: function() {
                var self = this;
                var selectionIndex = Html.div({className:'entryListIndex', style:{display:'none', cssFloat:'left'}});
                //Removes standard mouse events to enable custom right click event
                var stopMouseEvent = function(event) {
                    event.cancelBubble = true;
                    if (event.preventDefault) {
                        event.preventDefault();
                    } else {
                        event.returnValue = false;
                    }
                    return false;
                };
                selectionIndex.observeEvent('contextmenu', stopMouseEvent);
                selectionIndex.observeEvent('mousedown', stopMouseEvent);
                selectionIndex.observeEvent('click', stopMouseEvent);
                selectionIndex.observeEvent('mouseup', function(event) {
                    //Preventing event propagation
                    event.cancelBubble = true;
                    if (event.which === null) {
                        /* IE case */
                        var button = event.button == 1 ? "left" : "notLeft";
                    } else {
                        /* All others */
                        var button = event.which == 1 ? "left" : "notLeft";
                    }
                    var idx = parseInt(selectionIndex.dom.innerHTML.substr(0, selectionIndex.dom.innerHTML.length - 2) - 1);
                    if (button == "left") {
                        self.selectedList.shiftTop(idx);
                    } else {
                        self.selectedList.shiftBottom(idx);
                    }
                    self.observeSelection(self.selectedList);
                });
                return selectionIndex;
            },

            /**
             * Converts list of materials into a dictionary
             */
            _convertMaterials: function(materials) {
                var materialsDict = {};
                each(materials, function(mat) {
                    var key = mat.name || '';
                    if (!materialsDict[key]) {
                        materialsDict[key] = [];
                    }
                    materialsDict[key].push(mat.url);
                });
                return materialsDict;
            },

            /**
             * Converts resource link into a name.
             */
            _getResourceName: function(resource) {
                var splittedName = resource.split('.');
                if (splittedName[splittedName.length - 1] in ImporterUtils.resourcesExtensionList) {
                    return splittedName[splittedName.length - 1];
                } else {
                    return 'resource';
                }
            },

            /**
             * Draws a div containing entry's data.
             */
            _drawItem : function(record) {
                var self = this;
                var recordDiv = Html.div({});
                var key = record.key;
                record = record.get();
                // Empty fields are not displayed.
                if (record.get("reportNumbers")) {
                    var reportNumber = Html.div({}, Html.em({}, $t.gettext("Report number(s)")), ":");
                    each(record.get("reportNumbers"), function(id) {
                        reportNumber.append(" " + id);
                    });
                    recordDiv.append(reportNumber);
                }
                if (record.get("title")) {
                    recordDiv.append(Html.div({}, Html.em({}, $t.gettext("Title")), ": ", record.get("title")));
                }
                if (record.get("meetingName")) {
                    recordDiv.append(Html.div({}, Html.em({}, $t.gettext("Meeting")), ": ", record.get("meetingName")));
                }
                // Speaker, primary and secondary authors are stored in dictionaries. Their property have to be checked.
                if (!ImporterUtils.isPersonEmpty(record.get('primaryAuthor'))) {
                    recordDiv.append(Html.div({}, Html.em({}, $t.gettext("Primary author")), ": ", this._getPersonString(record.get("primaryAuthor"))));
                }
                if (!ImporterUtils.isPersonEmpty(record.get('secondaryAuthor'))) {
                    recordDiv.append(Html.div({}, Html.em({}, $t.gettext("Secondary author")), ": ", this._getPersonString(record.get("secondaryAuthor"))));
                }
                if (!ImporterUtils.isPersonEmpty(record.get('speaker'))) {
                    recordDiv.append(Html.div({}, Html.em({}, $t.gettext("Speaker")), ": ", this._getPersonString(record.get("speaker"))));
                }
                if (record.get("summary")) {
                    var summary = record.get("summary");
                    //If summary is too long it need to be truncated.
                    if (summary.length < 200) {
                        recordDiv.append(Html.div({}, Html.em({}, $t.gettext("Summary")), ": " , summary));
                    } else {
                        var summaryBeg = Html.span({}, summary.substr(0, 200));
                        var summaryEnd = Html.span({style:{display:'none'}}, summary.substr(200));
                        var showLink = Html.span({className:'fake-link'}, $t.gettext(" (show all)"));
                        showLink.observeClick(function(evt) {
                            summaryEnd.dom.style.display = "inline";
                            showLink.dom.style.display = "none";
                            hideLink.dom.style.display = "inline";
                            //Preventing event propagation
                            evt.cancelBubble=true;
                            //Recalculating position of the selection number
                            self.observeSelection(self.selectedList);
                        });
                        var hideLink = Html.span({className:'fake-link', style:{display:'none'}}, $t.gettext(" (hide)"));
                        hideLink.observeClick(function(evt) {
                            summaryEnd.dom.style.display = "none";
                            showLink.dom.style.display = "inline";
                            hideLink.dom.style.display = "none";
                            //Preventing event propagation
                            evt.cancelBubble=true;
                            //Recalculating position of the selection number
                            self.observeSelection(self.selectedList);
                        });
                        var sumamaryDiv = Html.div({}, Html.em({}, $t.gettext("Summary")), ": " , summaryBeg, showLink, summaryEnd, hideLink);
                        recordDiv.append(sumamaryDiv);
                    }
                }
                if (record.get("place")) {
                    recordDiv.append(Html.div({}, Html.em({}, $t.gettext("Place")), ": ", record.get("place")));
                }
                if (record.get("materials")) {
                    record.set("materials", this._convertMaterials(record.get("materials")));
                    var materials = Html.div({}, Html.em({}, $t.gettext("Materials")), ":");
                    for (var mat in record.get("materials")) {
                        var materialType = Html.div({}, mat ? (mat + ":") : '');
                        each(record.get("materials")[mat], function(resource) {
                            var link = Html.a({href:resource, target: "_new"}, self._getResourceName(resource));
                            link.observeClick(function(evt) {
                                //Preventing event propagation
                                evt.cancelBubble = true;
                            });
                            materialType.append(" ");
                            materialType.append(link);
                        });
                        materials.append(materialType);
                    }
                    recordDiv.append(materials);
                }
                recordDiv.append(this._drawSelectionIndex());
                this.recordDivs[key] = recordDiv;
                return recordDiv;
            },

            /**
             * Observer function executed when selection is made. Draws a number next to the item div, which
             * represents insertion sequence of entries.
             */
            observeSelection: function(list) {
                var self = this;
                //Clears numbers next to the all divs
                for (var entry in this.recordDivs) {
                    var record = this.recordDivs[entry];
                    record.dom.lastChild.style.display = 'none';
                    record.dom.lastChild.innerHTML = '';
                }
                var seq = 1;
                each(list.getKeys(), function(entry) {
                    var record = self.recordDivs[entry];
                    record.dom.lastChild.style.display = 'block';
                    record.dom.lastChild.style.top = pixels(-(record.dom.clientHeight + 23) / 2);
                    record.dom.lastChild.innerHTML = seq;
                    switch(seq) {
                        case 1:
                            record.dom.lastChild.innerHTML += $t.gettext('st');
                            break;
                        case 2:
                            record.dom.lastChild.innerHTML += $t.gettext('nd');
                            break;
                        case 3:
                            record.dom.lastChild.innerHTML += $t.gettext('rd');
                            break;
                        default:
                            record.dom.lastChild.innerHTML += $t.gettext('th');
                            break;
                    }
                    ++seq;
                });
            }
        },

        /**
         * Widget containing a list of imported contributions. Supports multiple selections of results and
         * keeps selection order.
         * @param events List of events to be inserted during initialization.
         * @param listStyle Css class name of the list.
         * @param selectedStyle Css class name of a selected element.
         * @param customObserver Function executed while selection is made.
         */
        function(events, listStyle, selectedStyle, customObserver) {
            var self = this;
            // After selecting/deselecting an element two observers are executed.
            // The first is a default one, used to keep selected elements order.
            // The second one is a custom observer passed in the arguments list.
            var observer = function(list) {
                this.observeSelection(list);
                if (customObserver) {
                    customObserver(list);
                }
            };
            this.SelectableListWidget(observer, false, listStyle, selectedStyle);
            this.selectedList = new QueueDict();
            this.recordDivs = {};
            for (var record in events) {
                this.set(record, $O(events[record]));
            }
        }
    );


    type("ImporterList", [], {
            /**
             * Show the widget.
             */
            show: function() {
                this.contentDiv.dom.style.display = 'block';
            },

            /**
             * Hides the widget.
             */
            hide: function() {
                this.contentDiv.dom.style.display = 'none';
            },

            /**
             * Returns list of the selected entries.
             */
            getSelectedList: function() {
                return this.importerWidget.getSelectedList();
            },

            /**
             * Removes all entries from the selection list.
             */
            clearSelection: function() {
                this.importerWidget.clearSelection();
            },

            /**
             * Returns last used importer.
             */
            getLastImporter: function() {
                return this.importerWidget.getLastImporter();
            },

            /**
             * Changes widget's header depending on the number of results in the list.
             */
            handleContent: function() {
                if (this.descriptionDiv && this.emptyDescriptionDiv) {
                    if (this.importerWidget.getLength() === 0) {
                        this.descriptionDiv.dom.style.display = 'none';
                        this.emptyDescriptionDiv.dom.style.display = 'block';
                        this.moreEntriesDiv.dom.style.display = 'none';
                    } else {
                        this.entriesCount.dom.innerHTML = $t.ngettext("One entry was found. ", "{0} entries were found. ", this.importerWidget.getLength()).format(this.importerWidget.getLength());
                        this.descriptionDiv.dom.style.display = 'block';
                        this.emptyDescriptionDiv.dom.style.display = 'none';
                        if (this.importerWidget.isMoreToImport()) {
                            this.moreEntriesDiv.dom.style.display = 'block';
                        } else {
                            this.moreEntriesDiv.dom.style.display = 'none';
                        }
                    }
                }
            },

            /**
             * Adds handleContent method to the callback list. If callback list is empty, creates a new one
             * containing only handleContent method.
             * @return list with inserted handleContent method.
             */
            _appendCallbacks: function(callbacks) {
                var self = this;
                if (callbacks) {
                    callbacks.push(function() {
                        self.handleContent();
                    });
                } else {
                    callbacks = [function() {
                        self.handleContent();
                    }];
                }
                return callbacks;
            },

            /**
             * Calls search method from ImporterListWidget object.
             */
            search: function(query, importer, size, callbacks) {
                this.importerWidget.search(query, importer, size, this._appendCallbacks(callbacks));
            },

            /**
             * Calls append method from ImporterListWidget object.
             */
            append: function(size, callbacks) {
                this.importerWidget.append(size, this._appendCallbacks(callbacks));
            },

            draw: function() {
                var importerDiv = this._drawImporterDiv();
                this.contentDiv = Html.div({className:'entryListContainer'}, this._drawHeader(), importerDiv);

                for (var style in this.style) {
                    this.contentDiv.setStyle(style, this.style[style]);
                    if (style == 'height') {
                        importerDiv.setStyle('height', this.style[style] - 76); //76 = height of the header
                    }
                }

                if (this.hidden) {
                    this.contentDiv.dom.style.display = 'none';
                }

                return this.contentDiv;
            },

            _drawHeader: function() {
                this.entriesCount = Html.span({}, '0');
                this.descriptionDiv = Html.div({className:'entryListDesctiption'}, this.entriesCount, $t.gettext("Please select the results you want to insert."));
                this.emptyDescriptionDiv = Html.div({className:'entryListDesctiption'}, $t.gettext("No results were found. Please change the search phrase."));
                return Html.div({}, Html.div({className:'entryListHeader'}, $t.gettext("Step 1: Search results:")), this.descriptionDiv, this.emptyDescriptionDiv);
            },

            _drawImporterDiv: function() {
                var self = this;
                this.moreEntriesDiv = Html.div({className:'fake-link', style:{paddingBottom:pixels(15), textAlign:'center', clear: 'both', marginTop: pixels(15)}}, $t.gettext("more results"));
                this.moreEntriesDiv.observeClick(function() {
                    self.append(20);
                });
                return Html.div({style:{overflow:'auto'}}, this.importerWidget.draw(), this.moreEntriesDiv);
            }
        },

        /**
         * Encapsulates ImporterListWidget. Adds a header depending on the number of entries in the least.
         * Adds a button to fetch more entries from selected importer.
         * @param events List of events to be inserted during initialization.
         * @param style Dictionary of css styles applied to the div containing the list. IMPORTANT pass 'height'
         * attribute as an integer not a string, because some further calculations will be made.
         * @param listStyle Css class name of the list.
         * @param selectedStyle Css class name of a selected element.
         * @param hidden If true widget will not be displayed after being initialized.
         * @param observer Function executed while selection is made.
         */
        function(events, style, listStyle, selectedStyle, hidden, observer) {
            this.importerWidget = new ImporterListWidget(events, listStyle, selectedStyle, observer);
            this.style = style;
            this.hidden = hidden;
        }
    );


    type("TimetableListWidget", ["ListWidget"], {
            /**
             * Highlights selected entry and calls an observer method.
             */
            setSelection: function(selected, div) {
                if (this.selectedDiv) {
                    this.selectedDiv.dom.style.fontWeight = "normal";
                    this.selectedDiv.dom.style.boxShadow = "";
                    this.selectedDiv.dom.style.MozBoxShadow = "";
                }
                if (this.selected != selected) {
                    this.selectedDiv = div;
                    this.selected = selected;
                    this.selectedDiv.dom.style.fontWeight = "bold";
                    this.selectedDiv.dom.style.boxShadow = "3px 3px 15px #000000";
                    this.selectedDiv.dom.style.MozBoxShadow = "3px 3px 15px #000000";
                } else {
                    this.selected = null;
                    this.selectedDiv = null;
                }
                if (this.observeSelection) {
                    this.observeSelection();
                }
            },

            /**
             * Deselects current entry.
             */
            clearSelection: function() {
                if (this.selectedDiv) {
                    this.selectedDiv.dom.style.backgroundColor = "";
                }
                this.selected = null;
                this.selectedDiv = null;
                if (this.observeSelection) {
                    this.observeSelection();
                }
            },

            /**
             * Returns selected entry
             */
            getSelection: function() {
                return this.selected;
            },

            /**
             * Recursive function drawing timetable hierarchy.
             * @param item Entry to be displayed
             * @param level Recursion level. Used to set margins properly.
             */
            _drawItem : function(item, level) {
                var self = this;
                level = level?level:0;
                // entry is a Day
                switch(item.entryType) {
                    case 'Contribution':
                        item.color = "#F8F2E8";
                        item.textColor = "#000000";
                    case 'Session':
                        var titleDiv = Html.div({className:"treeListEntry", style:{backgroundColor: item.color, color: item.textColor}},
                                item.title + (item.startDate && item.endDate?" (" + item.startDate.time.substr(0, 5) + " - " + item.endDate.time.substr(0, 5) + ")":""));
                        var entries = ImporterUtils.sortedKeys(item.entries, ImporterUtils.compareStartTime);
                        break;
                    case 'Break':
                        if (this.displayBreaks) {
                            var titleDiv = Html.div({className:"treeListEntry", style:{backgroundColor: item.color, color: item.textColor}},
                                    item.title + (item.startDate && item.endDate?" (" + item.startDate.time.substr(0, 5) + " - " + item.endDate.time.substr(0, 5) + ")":""));
                            var entries = ImporterUtils.sortedKeys(item.entries, ImporterUtils.compareStartTime);
                        } else {
                            return null;
                        }
                        break;
                    case undefined:
                        item.entryType = 'Day';
                        item.startDate = {date : item.key.substr(0, 4) + "-" + item.key.substr(4, 2) + "-" + item.key.substr(6, 2)};
                        item.color = "#FFFFFF";
                        item.textColor = "#000000";
                        var titleDiv = Html.div({className:"treeListDayName"},
                                item.key.substr(6, 2) + " " + ImporterUtils.shortMonthsNames[parseFloat(item.key.substr(4, 2)) - 1] +
                                " " + item.key.substr(0, 4));
                        var entries = ImporterUtils.sortedKeys(item.get().getAll(), ImporterUtils.compareStartTime);
                        break;
                }
                titleDiv.observeClick(function() {
                    self.setSelection(item, titleDiv);
                });
                var itemDiv = Html.div({style:{marginLeft:pixels(level * 20), clear:"both", padding:pixels(5)}}, titleDiv);
                var entriesDiv = Html.div({style:{display:"none"}});

                //Draws subentries
                for (var entry in entries) {
                    entriesDiv.append(this._drawItem(entries[entry], level + 1));
                }

                //If there are any subentries, draws buttons to show/hide them on demand.
                if (entries.length) {
                    titleDiv.append(this._drawShowHideButtons(entriesDiv));
                    itemDiv.append(entriesDiv);
                }

                return itemDiv;
            },

            /**
             * Attaches buttons to the dom object which hide/show it when clicked.
             */
            _drawShowHideButtons: function(div) {
                var showButton = Html.img({src: imageSrc("collapsd"), style: {display: 'block'}});
                var hideButton = Html.img({src: imageSrc("exploded"), style: {display: 'none'}});
                showButton.observeClick(function(evt) {
                    div.dom.style.display = "block";
                    showButton.dom.style.display = "none";
                    hideButton.dom.style.display = "block";
                    evt.cancelBubble = true;
                });
                hideButton.observeClick(function(evt) {
                    div.dom.style.display = "none";
                    showButton.dom.style.display = "block";
                    hideButton.dom.style.display = "none";
                    evt.cancelBubble = true;
                });
                return Html.div({className: 'expandButtonsDiv'}, showButton, hideButton);
            },

            /**
             * Inserts entries from the timetable inside the widget.
             */
            _insertFromTimetable: function() {
                var self = this;
                var timetableData = this.timetable.getData();
                each(this.timetable.sortedKeys, function(day) {
                    self.set(day, $O(timetableData[day]));
                });
            },

            /**
             * Clears the list and inserts entries from the timetable inside the widget.
             */
            refresh: function() {
                this.clear();
                this._insertFromTimetable();
            }
        },

        /**
         * Draws event's timetable as a hierarchical expandable list.
         * @param timetable Indico timetable object to be drawn
         * @param listStyle Css class name of the list.
         * @param dayStyle Css class name of day entries.
         * @param eventStyle Css class name of session and contributions entries.
         * @param observeSelection Funtcion executed after changing selection state.
         * @param displayBreaks If true breaks will be displayed in the list. If false breaks are hidden.
         */
        function(timetable, listStyle, dayStyle, eventStyle, observeSelection, displayBreaks) {
            this.timetable = timetable;
            this.displayBreaks = displayBreaks;
            this.observeSelection = observeSelection;
            var self = this;
            this.ListWidget(listStyle);
            this._insertFromTimetable();
        }
    );


    type("TableTreeList", [], {

            /**
             * Show the widget.
             */
            show: function() {
                this.contentDiv.dom.style.display = 'block';
            },

            /**
             * Hides the widget
             */
            hide: function() {
                this.contentDiv.dom.style.display = 'none';
            },

            /**
             * Returns selected entry. TimetableListWidget method wrapper.
             */
            getSelection: function() {
                return this.timetableList.getSelection();
            },

            /**
             * Deselects current entry. TimetableListWidget method wrapper.
             */
            clearSelection: function() {
                return this.timetableList.clearSelection();
            },

            /**
             * Highlights selected entry and calls an observer method. TimetableListWidget method wrapper.
             */
            setSelection: function(selected, div) {
                return this.timetableList.setSelection(selected, div);
            },

            /**
             * Clears the list and inserts entries from the timetable inside the widget.
             */
            refresh: function() {
                this.timetableList.refresh();
            },

            draw: function() {
                this.contentDiv = Html.div({className:'treeListContainer'}, Html.div({className:'treeListHeader'}, $t.gettext("Step 2: Choose destination:")),
                        Html.div({className:'treeListDescription'}, $t.gettext("Please select the place in which the contributions will be inserted.")));
                var treeDiv = Html.div({style:{overflow:'auto'}}, this.timetableList.draw());
                for (var style in this.style) {
                    this.contentDiv.setStyle(style, this.style[style]);
                    if (style == 'height') {
                        treeDiv.setStyle('height', this.style[style] - 76);
                    }
                }
                this.contentDiv.append(treeDiv);
                if (this.hidden) {
                    this.contentDiv.dom.style.display = 'none';
                }
                return this.contentDiv;
            }
        },

        /**
         * Draws event's timetable as a hierarchical expandable list.
         * @param timetable Indico timetable object to be drawn
         * @param style Dictionary of css styles applied to the div containing the list. IMPORTANT pass 'height'
         * attribute as an integer not a string, because some further calculations will be made.
         * @param listStyle Css class name of the list.
         * @param dayStyle Css class name of day entries.
         * @param eventStyle Css class name of session and contributions entries.
         * @param observer Funtcion executed after changing selection state.
         */
        function(timetable, style, listStyle, dayStyle, eventStyle, hidden, observer) {
            this.timetableList = new TimetableListWidget(timetable, listStyle, dayStyle, eventStyle, observer);
            this.style = style;
            this.hidden = hidden;
        }
    );


    $(function() {
        $('#timetable').on('click', '.js-create-importer-dialog', function() {
            var timetable = $(this).data('timetable');
            new ImportDialog(timetable);
        });
    });
})();
