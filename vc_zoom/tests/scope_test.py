# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico_vc_zoom.plugin import (AUTO_REGISTRATION_BROAD_WEBINAR_SCOPES, AUTO_REGISTRATION_LEGACY_MEETING_SCOPES,
                                   AUTO_REGISTRATION_MEETING_SCOPES, AUTO_REGISTRATION_WEBINAR_SCOPES,
                                   _get_missing_auto_registration_scopes)


def test_auto_registration_scope_check_accepts_modern_meeting_scopes():
    assert _get_missing_auto_registration_scopes(set(AUTO_REGISTRATION_MEETING_SCOPES), allow_webinars=False) == ()


def test_auto_registration_scope_check_accepts_legacy_meeting_scopes():
    assert (_get_missing_auto_registration_scopes(set(AUTO_REGISTRATION_LEGACY_MEETING_SCOPES),
                                                  allow_webinars=False) == ())


def test_auto_registration_scope_check_accepts_broad_webinar_scopes():
    scopes = set(AUTO_REGISTRATION_MEETING_SCOPES) | set(AUTO_REGISTRATION_BROAD_WEBINAR_SCOPES)
    assert _get_missing_auto_registration_scopes(scopes, allow_webinars=True) == ()


def test_auto_registration_scope_check_requires_webinar_scopes_when_enabled():
    assert (_get_missing_auto_registration_scopes(set(AUTO_REGISTRATION_MEETING_SCOPES),
                                                  allow_webinars=True) == AUTO_REGISTRATION_WEBINAR_SCOPES)
