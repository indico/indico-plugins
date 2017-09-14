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

from flask_pluginengine import current_plugin

from indico.legacy.common.output import outputGenerator
from indico.legacy.common.xmlGen import XMLGen
from indico.modules.categories.models.categories import Category
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.models.events import Event
from indico.modules.users import User

from indico_livesync import SimpleChange
from indico_livesync.util import compound_id, obj_ref


class MARCXMLGenerator:
    """Generate MARCXML based on Indico objects."""

    @classmethod
    def records_to_xml(cls, records):
        mg = MARCXMLGenerator()
        for entry, change in records.iteritems():
            mg.safe_add_object(entry, bool(change & SimpleChange.deleted))
        return mg.get_xml()

    @classmethod
    def objects_to_xml(cls, objs, change_type=SimpleChange.created):
        mg = MARCXMLGenerator()
        for obj in objs:
            mg.safe_add_object(obj_ref(obj), bool(change_type & SimpleChange.deleted))
        return mg.get_xml()

    def __init__(self):
        self.closed = False
        self.xml_generator = XMLGen()
        self.xml_generator.initXml()
        self.xml_generator.openTag(b'collection', [[b'xmlns', b'http://www.loc.gov/MARC21/slim']])
        # This is horrible. but refactoring all the code in the indico core would be just as bad.
        admin = User.find_first(is_admin=True)
        self.output_generator = outputGenerator(admin, self.xml_generator)

    def safe_add_object(self, obj, deleted=False):
        try:
            self.add_object(obj, deleted)
        except Exception:
            current_plugin.logger.exception('Could not process %s', obj)

    def add_object(self, obj, deleted=False):
        if self.closed:
            raise RuntimeError('Cannot add object to closed xml generator')
        if deleted:
            xg = XMLGen(init=False)
            xg.openTag(b'record')
            xg.openTag(b'datafield', [[b'tag', b'970'], [b'ind1', b' '], [b'ind2', b' ']])
            xg.writeTag(b'subfield', b'INDICO.{}'.format(compound_id(obj)), [[b'code', b'a']])
            xg.closeTag(b'datafield')
            xg.openTag(b'datafield', [[b'tag', b'980'], [b'ind1', b' '], [b'ind2', b' ']])
            xg.writeTag(b'subfield', b'DELETED', [[b'code', b'c']])
            xg.closeTag(b'datafield')
            xg.closeTag(b'record')
            self.xml_generator.xml += xg.xml
        elif isinstance(obj, (Event, Contribution, SubContribution)):
            if obj.is_deleted or obj.event.is_deleted:
                pass
            elif isinstance(obj, Event):
                self.xml_generator.xml += self._event_to_marcxml(obj)
            elif isinstance(obj, Contribution):
                self.xml_generator.xml += self._contrib_to_marcxml(obj)
            elif isinstance(obj, SubContribution):
                self.xml_generator.xml += self._subcontrib_to_marcxml(obj)
        elif isinstance(obj, Category):
            pass  # we don't send category updates
        else:
            raise ValueError('unknown object ref: {}'.format(obj))
        return self.xml_generator.getXml()

    def get_xml(self):
        if not self.closed:
            self.xml_generator.closeTag(b'collection')
        return self.xml_generator.getXml()

    def _event_to_marcxml(self, obj):
        xg = XMLGen(init=False)
        xg.openTag(b'record')
        self.output_generator.confToXMLMarc21(obj, out=xg)
        xg.closeTag(b'record')
        return xg.xml

    def _contrib_to_marcxml(self, obj):
        xg = XMLGen(init=False)
        xg.openTag(b'record')
        self.output_generator.contribToXMLMarc21(obj, out=xg)
        xg.closeTag(b'record')
        return xg.xml

    def _subcontrib_to_marcxml(self, obj):
        xg = XMLGen(init=False)
        xg.openTag(b'record')
        self.output_generator.subContribToXMLMarc21(obj, out=xg)
        xg.closeTag(b'record')
        return xg.xml
