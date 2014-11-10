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

from MaKaC.conference import Conference, Contribution, SubContribution, Category, CategoryManager, ConferenceHolder
from werkzeug.datastructures import ImmutableDict


def obj_ref(obj, parent=None):
    """Returns a tuple identifying a category/event/contrib/subcontrib"""
    if isinstance(obj, Category):
        ref = {'type': 'category', 'category_id': obj.id}
    elif isinstance(obj, Conference):
        ref = {'type': 'event', 'event_id': obj.id}
    elif isinstance(obj, Contribution):
        event = parent or obj.getConference().id
        ref = {'type': 'contribution', 'event_id': event, 'contrib_id': obj.id}
    elif isinstance(obj, SubContribution):
        contrib = parent or obj.getContribution()
        ref = {'type': 'subcontribution',
               'event_id': contrib.getConference().id, 'contrib_id': contrib.id, 'subcontrib_id': obj.id}
    else:
        raise ValueError('Unexpected object: {}'.format(obj.__class__.__name__))
    return ImmutableDict(ref)


def obj_deref(ref):
    """Returns the object identified by `ref`"""
    if ref['type'] == 'category':
        try:
            return CategoryManager().getById(ref['category_id'])
        except KeyError:
            return None
    elif ref['type'] in {'event', 'contribution', 'subcontribution'}:
        event = ConferenceHolder().getById(ref['event_id'], quiet=True)
        if ref['type'] == 'event' or not event:
            return event
        contrib = event.getContributionById(ref['contrib_id'])
        if ref['type'] == 'contribution' or not contrib:
            return contrib
        return contrib.getSubContributionById(ref['subcontrib_id'])
    else:
        raise ValueError('Unexpected object type: {}'.format(ref['type']))


def make_compound_id(ref):
    """Returns the compound ID for the referenced object"""
    if ref['type'] == 'category':
        raise ValueError('Compound IDs are not supported for categories')
    elif ref['type'] == 'event':
        return ref['event_id']
    elif ref['type'] == 'contribution':
        return '{}.{}'.format(ref['event_id'], ref['contrib_id'])
    elif ref['type'] == 'subcontribution':
        return '{}.{}.{}'.format(ref['event_id'], ref['contrib_id'], ref['subcontrib_id'])
    else:
        raise ValueError('Unexpected object type: {}'.format(ref['type']))
