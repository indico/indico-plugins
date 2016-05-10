# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
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

from dateutil.relativedelta import relativedelta
from flask import jsonify, request
from flask_pluginengine import current_plugin
from pytz import timezone
from werkzeug.exceptions import NotFound

from indico.modules.events.timetable.controllers import RHManageTimetableBase
from indico.modules.events.timetable.models.entries import TimetableEntry, TimetableEntryType
from MaKaC.webinterface.rh.base import RHProtected


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
            lambda self: self.event_new
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
        return date.astimezone(timezone(self.event_new.timezone)).strftime('%H:%M')


class RHDayEndTime(RHEndTimeBase):
    """Get the end_dt of the latest timetable entry or the event start_dt if no entry exist on that date"""

    def _checkParams(self, params):
        RHEndTimeBase._checkParams(self, params)
        self.date = timezone(self.event_new.timezone).localize(datetime.strptime(request.args['selectedDay'],
                                                                                 '%Y/%m/%d'))

    def _process(self):
        end_date = self.date + relativedelta(days=1)
        entries = self.event_new.timetable_entries.filter(TimetableEntry.start_dt >= self.date,
                                                          TimetableEntry.start_dt < end_date)
        latest_end_dt = self._find_latest_end_dt(entries)
        if latest_end_dt is None:
            event_start = self.event_new.start_dt.astimezone(self.date.tzinfo)
            latest_end_dt = self.date.replace(hour=event_start.hour, minute=event_start.minute)
        print latest_end_dt
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

    def _checkParams(self, params):
        RHEndTimeBase._checkParams(self, params)
        self.date = timezone(self.event_new.timezone).localize(datetime.strptime(request.args['selectedDay'],
                                                                                 '%Y/%m/%d'))
        self.timetable_entry = self.event_new.timetable_entries.filter_by(type=TimetableEntryType.SESSION_BLOCK,
                                                                          id=request.view_args['entry_id']).first()
        if not self.timetable_entry:
            raise NotFound

    def _process(self):
        entries = self.timetable_entry.children
        latest_end_dt = self._find_latest_end_dt(entries)
        if latest_end_dt is None:
            latest_end_dt = self.timetable_entry.start_dt
        return self._format_date(latest_end_dt)
