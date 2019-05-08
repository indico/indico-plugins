# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask_pluginengine import current_plugin

from indico.modules.events import Event
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.util.date_time import as_utc
from indico.web.flask.util import url_for


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
        return Event.get(int(self.event_id), is_deleted=False)

    @property
    def start_date(self):
        if not self._start_date:
            return None
        return self._start_date.astimezone(self.event.display_tzinfo)

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
            current_plugin.logger.warning('referenced element %s does not exist', self.compound_id)
            return False
        return obj.can_access(user)

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
        return self.event.get_contribution(self.id) if self.event else None


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
        return (SubContribution.query
                .filter(SubContribution.id == self.id,
                        ~SubContribution.is_deleted,
                        SubContribution.contribution.has(id=self.parent, event=self.event, is_deleted=False))
                .first())


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
