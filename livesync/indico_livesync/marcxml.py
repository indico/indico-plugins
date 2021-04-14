# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask_pluginengine import current_plugin

from indico.legacy.common.output import outputGenerator
from indico.legacy.common.xmlGen import XMLGen
from indico.modules.categories.models.categories import Category
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.models.events import Event
from indico.modules.users import User

from indico_livesync.simplify import SimpleChange
from indico_livesync.util import compound_id, obj_ref


class MARCXMLGenerator:
    """Generate MARCXML based on Indico objects."""

    @classmethod
    def records_to_xml(cls, records):
        mg = MARCXMLGenerator()
        for entry, change in records.items():
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
        self.xml_generator.openTag('collection', [['xmlns', 'http://www.loc.gov/MARC21/slim']])
        # This is horrible. but refactoring all the code in the indico core would be just as bad.
        admin = User.query.filter_by(is_admin=True).first()
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
            xg.openTag('record')
            xg.openTag('datafield', [['tag', '970'], ['ind1', ' '], ['ind2', ' ']])
            xg.writeTag('subfield', f'INDICO.{compound_id(obj)}', [['code', 'a']])
            xg.closeTag('datafield')
            xg.openTag('datafield', [['tag', '980'], ['ind1', ' '], ['ind2', ' ']])
            xg.writeTag('subfield', 'DELETED', [['code', 'c']])
            xg.closeTag('datafield')
            xg.closeTag('record')
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
            raise ValueError(f'unknown object ref: {obj}')
        return self.xml_generator.getXml()

    def get_xml(self):
        if not self.closed:
            self.xml_generator.closeTag('collection')
        return self.xml_generator.getXml()

    def _event_to_marcxml(self, obj):
        xg = XMLGen(init=False)
        xg.openTag('record')
        self.output_generator.confToXMLMarc21(obj, out=xg)
        xg.closeTag('record')
        return xg.xml

    def _contrib_to_marcxml(self, obj):
        xg = XMLGen(init=False)
        xg.openTag('record')
        self.output_generator.contribToXMLMarc21(obj, out=xg)
        xg.closeTag('record')
        return xg.xml

    def _subcontrib_to_marcxml(self, obj):
        xg = XMLGen(init=False)
        xg.openTag('record')
        self.output_generator.subContribToXMLMarc21(obj, out=xg)
        xg.closeTag('record')
        return xg.xml
