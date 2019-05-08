# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.util.string import strip_tags

from indico_importer.converter import APPEND, RecordConverter
from indico_importer.util import convert_dt_tuple


class InvenioRecordConverterBase(RecordConverter):
    """
    Base class of every Invenio record converter. Data in Invenio records is always stored
    in the list (e.g. author's name is stored as ["Joe Doe"]), so defaultConversion method
    simply takes the first element form a list.
    """

    @staticmethod
    def default_conversion_method(attr):
        return attr[0]


class InvenioAuthorConverter(InvenioRecordConverterBase):
    """
    Converts author name, surname and affiliation.
    """

    conversion = [('a', 'firstName', lambda x: x[0].split(' ')[0]),
                  ('a', 'familyName', lambda x: ' '.join(x[0].split(' ')[1:])),
                  ('u', 'affiliation'),
                  ('e', APPEND, lambda x: {'isSpeaker': 'speaker' in x})]


class InvenioPlaceTimeConverter111(InvenioRecordConverterBase):
    """
    Extracts event's place and start/end time. Used for entry 111 in MARC 21.
    """

    conversion = [('9', 'startDateTime', convert_dt_tuple),
                  ('z', 'endDateTime', convert_dt_tuple),
                  ('c', 'place')]


class InvenioPlaceTimeConverter518(InvenioRecordConverterBase):
    """
    Extracts event's place and start/end time. Used for entry 518 in MARC 21.
    """

    conversion = [('d', 'startDateTime', convert_dt_tuple),
                  ('h', 'endDateTime', convert_dt_tuple),
                  ('r', 'place')]


class InvenioLinkConverter(InvenioRecordConverterBase):
    """
    Extracts link to the event.
    """

    conversion = [('y', 'name'),
                  ('u', 'url')]


class InvenioRecordConverter(InvenioRecordConverterBase):
    """
    Main converter class. Converts record from InvenioConverter in format readable by a plugin.
    """

    conversion = [('088', 'reportNumbers', lambda x: [number for number in x[0]['a'][0].split(' ') if number != '(Confidential)']),
                  ('100', 'primaryAuthor', lambda x: x[0] if 'Primary Author' in x[0].get('e', []) else {}, InvenioAuthorConverter),
                  ('100', 'speaker', lambda x: x[0] if 'Speaker' in x[0].get('e', []) else {}, InvenioAuthorConverter),
                  ('111', APPEND, None, InvenioPlaceTimeConverter111),
                  ('245', 'title', lambda x: x[0]['a'][0]),
                  ('518', APPEND, None, InvenioPlaceTimeConverter518),
                  ('520', 'summary', lambda x: strip_tags(x[0]['a'][0])),
                  ('700', 'secondaryAuthor', None, InvenioAuthorConverter),
                  ('61124', 'meetingName', lambda x: str(x[0]['a'][0])),
                  ('8564', 'materials', lambda x: x, InvenioLinkConverter)]
