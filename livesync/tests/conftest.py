# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.


import pytest

from indico_livesync.models.agents import LiveSyncAgent


@pytest.fixture
def dummy_agent(db):
    agent = LiveSyncAgent(backend_name='dummy', name='dummy')
    db.session.add(agent)
    return agent
