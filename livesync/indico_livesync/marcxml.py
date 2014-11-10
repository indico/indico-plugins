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

from MaKaC.accessControl import AccessWrapper, AdminList
from MaKaC.common.output import outputGenerator
from MaKaC.common.xmlGen import XMLGen

from indico_livesync import process_records, SimpleChange
from indico_livesync.util import make_compound_id, obj_deref


class MARCXMLGenerator:
    """Generates MARCXML based on Indico objects"""

    @classmethod
    def records_to_xml(cls, records):
        mg = MARCXMLGenerator()
        for ref, change in process_records(records).iteritems():
            try:
                mg.add_object(ref, bool(change & SimpleChange.deleted))
            except Exception:
                mg._remove_unfinished_record()
                current_plugin.logger.exception('Could not process {}'.format(ref))
        return mg.get_xml()

    def __init__(self):
        self.closed = False
        self.xml_generator = XMLGen()
        self.xml_generator.initXml()
        self.xml_generator.openTag('collection', [['xmlns', 'http://www.loc.gov/MARC21/slim']])
        # This is horrible. but refactoring all the code in the indico core would be just as bad.
        aw = AccessWrapper()
        aw.setUser(AdminList().getInstance().getList()[0])
        self.output_generator = outputGenerator(aw, self.xml_generator)

    def add_object(self, ref, deleted=False):
        if self.closed:
            raise RuntimeError('Cannot add object to closed xml generator')
        if deleted:
            self.xml_generator.openTag('record')

            self.xml_generator.openTag('datafield', [['tag', '970'], ['ind1', ' '], ['ind2', ' ']])
            self.xml_generator.writeTag('subfield', 'INDICO.{}'.format(make_compound_id(ref)), [['code', 'a']])
            self.xml_generator.closeTag('datafield')

            self.xml_generator.openTag('datafield', [['tag', '980'], ['ind1', ' '], ['ind2', ' ']])
            self.xml_generator.writeTag('subfield', 'DELETED', [['code', 'c']])
            self.xml_generator.closeTag('datafield')

            self.xml_generator.closeTag('record')
        elif ref['type'] in {'event', 'contribution', 'subcontribution'}:
            obj = obj_deref(ref)
            if obj is None:
                raise ValueError('Cannot add deleted object')
            elif not obj.getOwner():
                raise ValueError('Cannot add object without owner: {}'.format(obj))
            if ref['type'] == 'event':
                self._event_to_marcxml(obj)
            elif ref['type'] == 'contribution':
                self._contrib_to_marcxml(obj)
            elif ref['type'] == 'subcontribution':
                self._subcontrib_to_marcxml(obj)
        else:
            raise ValueError('unknown object ref: {}'.format(ref['type']))
        return self.xml_generator.getXml()

    def get_xml(self):
        if not self.closed:
            self.xml_generator.closeTag('collection')
        return self.xml_generator.getXml()

    def _remove_unfinished_record(self):
        # remove any line breaks, etc...
        while not self.xml_generator.xml[-1].strip():
            self.xml_generator.xml.pop()
        # remove '<record>'
        self.xml_generator.xml.pop()

    def _event_to_marcxml(self, obj):
        self.xml_generator.openTag('record')
        self.output_generator.confToXMLMarc21(obj, out=self.xml_generator, overrideCache=True)
        self.xml_generator.closeTag('record')

    def _contrib_to_marcxml(self, obj):
        self.xml_generator.openTag('record')
        self.output_generator.contribToXMLMarc21(obj, out=self.xml_generator, overrideCache=True)
        self.xml_generator.closeTag('record')

    def _subcontrib_to_marcxml(self, obj):
        self.xml_generator.openTag('record')
        self.output_generator.subContribToXMLMarc21(obj, out=self.xml_generator, overrideCache=True)
        self.xml_generator.closeTag('record')
