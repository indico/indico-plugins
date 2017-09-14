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


APPEND = object()


class RecordConverter(object):
    """
    Converts a dictionary or list of dictionaries into another list of dictionaries. The goal
    is to alter data fetched from connector class into a format that can be easily read by importer
    plugin. The way dictionaries are converted depends on the 'conversion' variable.

    conversion = [ (sourceKey, destinationKey, conversionFuncion(optional), converter(optional))... ]

    It's a list tuples in which a single element represents a translation that will be made. Every
    element of the list is a tuple that consists of from 1 to 4 entries.

    The first one is the key name in the source dictionary, the value that applies to this key will
    be the subject of the translation. The second is the key in the destination dictionary at which
    translated value will be put. If not specified its value will be equal the value of the first
    element. If the second element is equal *append* and the converted element is a dictionary or a
    list of dictionaries, destination dictionary will be updated by the converted element.Third,
    optional, element is the function that will take the value from the source dictionary and return
    the value which will be inserted into result dictionary. If the third element is empty
    defaultConversionMethod will be called.  Fourth, optional, element is a RecordConverter class
    which will be executed with converted value as an argument.
    """

    conversion = []

    @staticmethod
    def default_conversion_method(attr):
        """
        Method that will be used to convert an entry in dictionary unless other method is specified.
        """
        return attr

    @classmethod
    def convert(cls, record):
        """
        Converts a single dictionary or list of dictionaries into converted list of dictionaries.
        """
        if isinstance(record, list):
            return [cls._convert(r) for r in record]
        else:
            return [cls._convert(record)]

    @classmethod
    def _convert_internal(cls, record):
        """
        Converts a single dictionary into converted dictionary or list of dictionaries into converted
        list of dictionaries. Used while passing dictionaries to another converter.
        """
        if isinstance(record, list):
            return [cls._convert(r) for r in record]
        else:
            return cls._convert(record)

    @classmethod
    def _convert(cls, record):
        """
        Core method of the converter. Converts a single dictionary into another dictionary.
        """
        if not record:
            return {}

        converted_dict = {}
        for field in cls.conversion:
            key = field[0]
            if len(field) >= 2 and field[1]:
                converted_key = field[1]
            else:
                converted_key = key
            if len(field) >= 3 and field[2]:
                conversion_method = field[2]
            else:
                conversion_method = cls.default_conversion_method
            if len(field) >= 4:
                converter = field[3]
            else:
                converter = None
            try:
                value = conversion_method(record[key])
            except KeyError:
                continue
            if converter:
                value = converter._convert_internal(value)
            if converted_key is APPEND:
                if isinstance(value, list):
                    for v in value:
                        converted_dict.update(v)
                else:
                    converted_dict.update(value)
            else:
                converted_dict[converted_key] = value
        return converted_dict
