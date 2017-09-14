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

from indico.util.console import cformat
from indico.util.struct.iterables import grouper

from indico_livesync import LiveSyncBackendBase, MARCXMLGenerator, SimpleChange, Uploader, process_records


def _change_str(change):
    return ','.join(flag.name for flag in SimpleChange if change & flag)


class LiveSyncDebugBackend(LiveSyncBackendBase):
    """Debug

    This backend simply dumps all changes to stdout or the logger.
    """

    def _print(self, msg=''):
        print msg

    def run(self):
        records = self.fetch_records()
        if not records:
            self._print(cformat('%{yellow!}No records%{reset}'))
            return

        self._print(cformat('%{white!}Raw changes:%{reset}'))
        for record in records:
            self._print(record)

        self._print()
        self._print(cformat('%{white!}Simplified/cascaded changes:%{reset}'))
        for obj, change in process_records(records).iteritems():
            self._print(cformat('%{white!}{}%{reset}: {}').format(_change_str(change), obj))

        self._print()
        self._print(cformat('%{white!}Resulting MarcXML:%{reset}'))
        uploader = DebugUploader(self)
        uploader.run(records)
        self.update_last_run()

    def run_initial_export(self, events):
        uploader = DebugUploader(self)
        uploader.run_initial(events)
        for i, batch in enumerate(grouper(events, 10, skip_missing=True), 1):
            print
            print cformat('%{white!}Batch {}:%{reset}').format(i)
            print MARCXMLGenerator.objects_to_xml(event for event in batch if event is not None)
            print


class DebugUploader(Uploader):
    BATCH_SIZE = 5

    def __init__(self, *args, **kwargs):
        super(DebugUploader, self).__init__(*args, **kwargs)
        self.n = 0

    def upload_records(self, records, from_queue):
        self.n += 1
        self.backend._print(cformat('%{white!}Batch {}:%{reset}').format(self.n))
        xml = MARCXMLGenerator.records_to_xml(records) if from_queue else MARCXMLGenerator.objects_to_xml(records)
        self.backend._print(xml if xml else '(no changes)')
