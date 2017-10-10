# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from datetime import datetime

from flask import jsonify, request
from flask_pluginengine import current_plugin
from pytz import timezone, utc

from indico.core.db import db
from indico.modules.events.timetable.controllers import RHManageTimetableBase
from indico.modules.events.timetable.models.entries import TimetableEntry, TimetableEntryType
from indico.web.rh import RHProtected


class RHGetImporters(RHProtected):
    def _process(self):
        importers = {k: importer.name for k, (importer, _) in current_plugin.importer_engines.iteritems()}
        return jsonify(importers)


class RHImportData(RHProtected):
    def _process(self):
        size = request.args.get('size', 10)
        query = request.args.get('query')
        importer, plugin = current_plugin.importer_engines.get(request.view_args['importer_name'])
        with plugin.plugin_context():
            data = {'records': importer.import_data(query, size)}
        return jsonify(data)


class RHEndTimeBase(RHManageTimetableBase):
    """Base class for the importer operations"""
    normalize_url_spec = {
        'locators': {
            lambda self: self.event
        },
        'preserved_args': {
            'importer_name'
        }
    }

    @staticmethod
    def _find_latest_end_dt(entries):
        latest_dt = None
        for entry in entries:
            if latest_dt is None or entry.end_dt > latest_dt:
                latest_dt = entry.end_dt
        return latest_dt

    def _format_date(self, date):
        return date.astimezone(timezone(self.event.timezone)).strftime('%H:%M')


class RHDayEndTime(RHEndTimeBase):
    """Get the end_dt of the latest timetable entry or the event start_dt if no entry exist on that date"""

    def _process_args(self):
        RHEndTimeBase._process_args(self)
        self.date = self.event.tzinfo.localize(datetime.strptime(request.args['selectedDay'], '%Y/%m/%d')).date()

    def _process(self):
        event_start_date = db.cast(TimetableEntry.start_dt.astimezone(self.event.tzinfo), db.Date)
        entries = self.event.timetable_entries.filter(event_start_date == self.date)
        latest_end_dt = self._find_latest_end_dt(entries)
        if latest_end_dt is None:
            event_start = self.event.start_dt
            latest_end_dt = utc.localize(datetime.combine(self.date, event_start.time()))
        return self._format_date(latest_end_dt)


class RHBlockEndTime(RHEndTimeBase):
    """Return the end_dt of the latest timetable entry inside the block or the block start_dt if it is empty"""

    normalize_url_spec = {
        'locators': {
            lambda self: self.timetable_entry
        },
        'preserved_args': {
            'importer_name'
        }
    }

    def _process_args(self):
        RHEndTimeBase._process_args(self)
        self.date = timezone(self.event.timezone).localize(datetime.strptime(request.args['selectedDay'], '%Y/%m/%d'))
        self.timetable_entry = (self.event.timetable_entries
                                .filter_by(type=TimetableEntryType.SESSION_BLOCK,
                                           id=request.view_args['entry_id'])
                                .first_or_404())

    def _process(self):
        entries = self.timetable_entry.children
        latest_end_dt = self._find_latest_end_dt(entries)
        if latest_end_dt is None:
            latest_end_dt = self.timetable_entry.start_dt
        return self._format_date(latest_end_dt)
