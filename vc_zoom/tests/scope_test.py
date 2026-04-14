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
    # When no webinar scopes are present at all, the function should propose the modern set
    # (legacy/broad variants are only suggested when the app already uses some of them).
    missing = _get_missing_auto_registration_scopes(set(AUTO_REGISTRATION_MEETING_SCOPES), allow_webinars=True)
    assert set(missing) == set(AUTO_REGISTRATION_WEBINAR_SCOPES)


def test_auto_registration_scope_check_proposes_legacy_when_already_in_use():
    # User has one legacy meeting scope; the function should propose only the missing legacy one,
    # not the modern set.
    granted = {AUTO_REGISTRATION_LEGACY_MEETING_SCOPES[0]}
    missing = _get_missing_auto_registration_scopes(granted, allow_webinars=False)
    assert set(missing) == set(AUTO_REGISTRATION_LEGACY_MEETING_SCOPES) - granted


def test_auto_registration_scope_check_proposes_modern_when_no_overlap():
    # User has no auto-registration scopes at all: must propose the modern set, never legacy.
    missing = _get_missing_auto_registration_scopes(set(), allow_webinars=False)
    assert set(missing) == set(AUTO_REGISTRATION_MEETING_SCOPES)


def test_auto_registration_scope_check_only_reports_actually_missing_scopes():
    # User has all modern meeting scopes except the status update one — only that one should appear
    partial_meeting_scopes = set(AUTO_REGISTRATION_MEETING_SCOPES) - {'meeting:update:registrant_status:admin'}
    missing = _get_missing_auto_registration_scopes(partial_meeting_scopes, allow_webinars=False)
    assert missing == ('meeting:update:registrant_status:admin',)
