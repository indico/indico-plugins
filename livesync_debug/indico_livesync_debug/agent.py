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

from indico.core.db import db
from indico.util.console import cformat
from indico.util.struct.iterables import grouper

from indico_livesync import LiveSyncAgentBase, SimpleChange, MARCXMLGenerator, process_records
from indico_livesync.util import obj_deref


def _change_str(change):
    return ','.join(flag.name for flag in SimpleChange if change & flag)


class LiveSyncDebugAgent(LiveSyncAgentBase):
    """Debug Agent

    This agent simply dumps all changes to stdout.
    """

    def run(self):
        records = self.fetch_records()
        if not records:
            print cformat('%{yellow!}No records%{reset}')
            return

        print cformat('%{white!}Raw changes:%{reset}')
        for record in records:
            print record

        print
        print cformat('%{white!}Simplified/cascaded changes:%{reset}')
        for ref, change in process_records(records).iteritems():
            obj = obj_deref(ref)
            print cformat('%{white!}{}%{reset}: {}').format(_change_str(change), obj or ref)

        print
        print cformat('%{white!}Resulting MarcXML:%{reset}')
        print MARCXMLGenerator.records_to_xml(records)

        for record in records:
            record.processed = True
        db.session.commit()

    def run_initial_export(self, events):
        for i, batch in enumerate(grouper(events, 10), 1):
            print
            print cformat('%{white!}Batch {}:%{reset}').format(i)
            print MARCXMLGenerator.objects_to_xml(event for event in batch if event is not None)
            print
