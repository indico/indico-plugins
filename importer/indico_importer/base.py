# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask_pluginengine import depends

from indico.core.plugins import IndicoPlugin, PluginCategory

from indico_importer.plugin import ImporterPlugin


@depends('importer')
class ImporterSourcePluginBase(IndicoPlugin):
    """Base class for importer engine plugins"""

    importer_engine_classes = None
    category = PluginCategory.importers

    def init(self):
        super(ImporterSourcePluginBase, self).init()
        for engine_class in self.importer_engine_classes:
            importer_engine = engine_class()
            ImporterPlugin.instance.register_importer_engine(importer_engine, self)


class ImporterEngineBase(object):
    """Base class for data importers"""

    _id = ''
    name = ''

    def import_data(self, query, size):
        """Fetch and converts data from external source.

        :param query: A search phrase send to the importer.
        :param size: Number of records to fetch from external source.
        :return: List of dictionaries with the following format (all keys are optional)
            [{"recordId" : idOfTheRecordInExternalSource,
              "title": eventTitle,
              "primaryAuthor": {"firstName": primaryAuthorFirstName,
                                "familyName": primaryAuthorFamilyName,
                                "affiliation": primaryAuthorAffiliation},
               "speaker": {"firstName": speakerFirstName,
                           "familyName": speakerFamilyName,
                           "affiliation": speakerAffiliation},
               "secondaryAuthor": {"firstName": secondaryAuthorFirstName,
                                   "familyName": secondaryAuthorFamilyName,
                                   "affiliation": secondaryAuthorAffiliation},
               "summary": eventSummary,
               "meetingName": nameOfTheEventMeeting,
               "materials": [{"name": nameOfTheLink,
                              "url": linkDestination},
                              ...],
               "reportNumbers": [reportNumber, ...]
               "startDateTime": {"time" : eventStartTime,
                                 "date" : eventStartDate},
               "endDateTime": {"time" : eventEndTime,
                               "date" : eventEndDate}
               "place": eventPlace},
               ...]
        """
        raise NotImplementedError
