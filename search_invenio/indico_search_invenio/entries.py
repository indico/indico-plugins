# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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

from flask_pluginengine import current_plugin
from pytz import timezone

from indico.util.date_time import as_utc
from indico.web.flask.util import url_for
from MaKaC.accessControl import AccessWrapper
from MaKaC.common.timezoneUtils import DisplayTZ
from MaKaC.conference import ConferenceHolder


class Author(object):
    def __init__(self, name, role, affiliation):
        self.name = name
        self.role = role
        self.affiliation = affiliation


class SearchResult(object):
    def __init__(self, result_id, title, location, start_date, materials, authors, description):
        self.id = result_id
        self.title = title
        self.location = location
        self._start_date = as_utc(start_date) if start_date else None
        self.materials = materials
        self.authors = authors
        self.description = description

    @property
    def event(self):
        return ConferenceHolder().getById(self.event_id, quiet=True)

    @property
    def start_date(self):
        if not self._start_date:
            return None
        tz = DisplayTZ(conf=self.event).getDisplayTZ()
        return self._start_date.astimezone(timezone(tz))

    @property
    def object(self):
        raise NotImplementedError

    @property
    def event_id(self):
        raise NotImplementedError

    @property
    def compound_id(self):
        raise NotImplementedError

    def is_visible(self, user):
        obj = self.object
        if not obj:
            current_plugin.logger.warning('referenced element {} does not exist'.format(self.compound_id))
            return False
        return obj.canView(AccessWrapper(user))

    def __repr__(self):
        return '<{}({})>'.format(type(self).__name__, self.compound_id)


class ContributionEntry(SearchResult):
    def __init__(self, entry_id, title, location, start_date, materials, authors, description, parent):
        super(ContributionEntry, self).__init__(entry_id, title, location, start_date, materials, authors, description)
        self.parent = parent

    @property
    def event_id(self):
        return self.parent

    @property
    def url(self):
        return url_for('event.contributionDisplay', confId=self.event_id, contribId=self.id)

    @property
    def compound_id(self):
        return '{}:{}'.format(self.event_id, self.id)

    @property
    def object(self):
        event = self.event
        if not event:
            return None
        return event.getContributionById(self.id)


class SubContributionEntry(SearchResult):
    def __init__(self, entry_id, title, location, start_date, materials, authors, description, parent, event):
        super(SubContributionEntry, self).__init__(entry_id, title, location, start_date, materials, authors,
                                                   description)
        self.parent = parent
        self._event_id = event
        materials.append((url_for('event.conferenceDisplay', confId=event), 'Event details'))

    @property
    def event_id(self):
        return self._event_id

    @property
    def url(self):
        return url_for('event.subContributionDisplay', confId=self.event_id, contribId=self.parent, subContId=self.id)

    @property
    def compound_id(self):
        return '{}:{}:{}'.format(self.event_id, self.parent, self.id)

    @property
    def object(self):
        event = self.event
        if not event:
            return None
        contribution = event.getContributionById(self.parent)
        if not contribution:
            return None
        return contribution.getSubContributionById(self.id)


class EventEntry(SearchResult):
    @property
    def url(self):
        return url_for('event.conferenceDisplay', confId=self.id)

    @property
    def compound_id(self):
        return self.id

    @property
    def event_id(self):
        return self.id

    @property
    def object(self):
        return self.event
