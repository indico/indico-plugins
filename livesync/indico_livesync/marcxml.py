# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

from MaKaC.accessControl import AccessWrapper
from MaKaC.common.output import outputGenerator
from MaKaC.common.xmlGen import XMLGen
from indico.modules.users import User

from indico_livesync import SimpleChange
from indico_livesync.util import make_compound_id, obj_deref, obj_ref


class MARCXMLGenerator:
    """Generates MARCXML based on Indico objects"""

    @classmethod
    def records_to_xml(cls, records):
        mg = MARCXMLGenerator()
        for ref, change in records.iteritems():
            mg.safe_add_object(ref, bool(change & SimpleChange.deleted))
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
        aw = AccessWrapper()
        aw.setUser(User.find_first(is_admin=True).as_avatar)
        self.output_generator = outputGenerator(aw, self.xml_generator)

    def safe_add_object(self, ref, deleted=False):
        try:
            self.add_object(ref, deleted)
        except Exception:
            current_plugin.logger.exception('Could not process {}'.format(ref))

    def add_object(self, ref, deleted=False):
        if self.closed:
            raise RuntimeError('Cannot add object to closed xml generator')
        if deleted:
            xg = XMLGen(init=False)
            xg.openTag(b'record')
            xg.openTag(b'datafield', [[b'tag', b'970'], [b'ind1', b' '], [b'ind2', b' ']])
            xg.writeTag(b'subfield', b'INDICO.{}'.format(make_compound_id(ref)), [[b'code', b'a']])
            xg.closeTag(b'datafield')
            xg.openTag(b'datafield', [[b'tag', b'980'], [b'ind1', b' '], [b'ind2', b' ']])
            xg.writeTag(b'subfield', b'DELETED', [[b'code', b'c']])
            xg.closeTag(b'datafield')
            xg.closeTag(b'record')
            self.xml_generator.xml += xg.xml
        elif ref['type'] in {'event', 'contribution', 'subcontribution'}:
            obj = obj_deref(ref)
            if obj is None:
                raise ValueError('Cannot add deleted object')
            elif not obj.getOwner():
                raise ValueError('Cannot add object without owner: {}'.format(obj))
            if ref['type'] == 'event':
                self.xml_generator.xml += self._event_to_marcxml(obj)
            elif ref['type'] == 'contribution':
                self.xml_generator.xml += self._contrib_to_marcxml(obj)
            elif ref['type'] == 'subcontribution':
                self.xml_generator.xml += self._subcontrib_to_marcxml(obj)
        elif ref['type'] == 'category':
            pass  # we don't send category updates
        else:
            raise ValueError('unknown object ref: {}'.format(ref['type']))
        return self.xml_generator.getXml()

    def get_xml(self):
        if not self.closed:
            self.xml_generator.closeTag(b'collection')
        return self.xml_generator.getXml()

    def _event_to_marcxml(self, obj):
        xg = XMLGen(init=False)
        xg.openTag(b'record')
        self.output_generator.confToXMLMarc21(obj, out=xg, overrideCache=True)
        xg.closeTag(b'record')
        return xg.xml

    def _contrib_to_marcxml(self, obj):
        xg = XMLGen(init=False)
        xg.openTag(b'record')
        self.output_generator.contribToXMLMarc21(obj, out=xg, overrideCache=True)
        xg.closeTag(b'record')
        return xg.xml

    def _subcontrib_to_marcxml(self, obj):
        xg = XMLGen(init=False)
        xg.openTag(b'record')
        self.output_generator.subContribToXMLMarc21(obj, out=xg, overrideCache=True)
        xg.closeTag(b'record')
        return xg.xml
