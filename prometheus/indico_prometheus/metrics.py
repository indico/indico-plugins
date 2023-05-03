# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2023 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import timedelta

from prometheus_client import metrics

from indico.core.cache import ScopedCache
from indico.core.db import db
from indico.core.db.sqlalchemy.protection import ProtectionMode
from indico.modules.attachments.models.attachments import Attachment, AttachmentFile
from indico.modules.auth.models.identities import Identity
from indico.modules.categories.models.categories import Category
from indico.modules.events.models.events import Event
from indico.modules.rb.models.reservation_occurrences import ReservationOccurrence
from indico.modules.rb.models.reservations import Reservation
from indico.modules.rb.models.rooms import Room
from indico.modules.users.models.users import User
from indico.util.date_time import now_utc

from indico_prometheus.queries import get_attachment_query, get_note_query


# Check for availability of the LiveSync plugin
LIVESYNC_AVAILABLE = True
try:
    from indico_livesync.models.queue import LiveSyncQueueEntry
except ImportError:
    LIVESYNC_AVAILABLE = False


num_active_events = metrics.Gauge('indico_num_active_events', 'Number of Active Events')
num_events = metrics.Gauge('indico_num_events', 'Number of Events')

num_active_users = metrics.Gauge('indico_num_active_users', 'Number of Active Users (logged in in the last 24h)')
num_users = metrics.Gauge('indico_num_users', 'Number of Users')

num_categories = metrics.Gauge('indico_num_categories', 'Number of Categories')

num_active_attachment_files = metrics.Gauge('indico_num_active_attachment_files', 'Number of attachment files')
num_attachment_files = metrics.Gauge(
    'indico_num_attachment_files',
    'Total number of attachment files, including older versions / deleted'
)

size_active_attachment_files = metrics.Gauge(
    'indico_size_active_attachment_files',
    'Total size of all active attachment files (bytes)'
)
size_attachment_files = metrics.Gauge(
    'indico_size_attachment_files',
    'Total size of all attachment files, including older versions / deleted (bytes)'
)

num_notes = metrics.Gauge('indico_num_notes', 'Number of notes')

num_active_rooms = metrics.Gauge('indico_num_active_rooms', 'Number of active rooms')
num_rooms = metrics.Gauge('indico_num_rooms', 'Number of rooms')
num_restricted_rooms = metrics.Gauge('indico_num_restricted_rooms', 'Number of restricted rooms')
num_rooms_with_confirmation = metrics.Gauge(
    'indico_num_rooms_with_confirmation',
    'Number or rooms requiring manual confirmation'
)

num_bookings = metrics.Gauge('indico_num_bookings', 'Number of bookings')
num_valid_bookings = metrics.Gauge('indico_num_valid_bookings', 'Number of valid bookings')
num_pending_bookings = metrics.Gauge('indico_num_pending_bookings', 'Number of pending bookings')

num_occurrences = metrics.Gauge('indico_num_booking_occurrences', 'Number of occurrences')
num_valid_occurrences = metrics.Gauge('indico_num_valid_booking_occurrences', 'Number of valid occurrences')

num_ongoing_occurrences = metrics.Gauge('indico_num_ongoing_booking_occurrences', 'Number of ongoing bookings')

if LIVESYNC_AVAILABLE:
    size_livesync_queues = metrics.Gauge('indico_size_livesync_queues', 'Items in Livesync queues')
    num_livesync_events_category_changes = metrics.Gauge(
        'indico_num_livesync_events_category_changes',
        'Number of event updates due to category changes queued up in Livesync'
    )


def get_attachment_stats():
    attachment_subq = db.aliased(Attachment, get_attachment_query().subquery('attachment'))

    return {
        'num_active': get_attachment_query().count(),
        'num_total': AttachmentFile.query.join(Attachment, AttachmentFile.attachment_id == Attachment.id).count(),
        'size_active': (
            db.session.query(db.func.sum(AttachmentFile.size))
            .filter(AttachmentFile.id == attachment_subq.file_id)
            .scalar() or 0
        ),
        'size_total': (
            db.session.query(db.func.sum(AttachmentFile.size))
            .join(Attachment, AttachmentFile.attachment_id == Attachment.id)
            .scalar() or 0
        )
    }


def update_metrics(active_user_age: timedelta, cache: ScopedCache, heavy_cache_ttl: timedelta):
    """Update all metrics."""
    now = now_utc()
    num_events.set(Event.query.filter(~Event.is_deleted).count())
    num_active_events.set(Event.query.filter(~Event.is_deleted, Event.start_dt <= now, Event.end_dt >= now).count())
    num_users.set(User.query.filter(~User.is_deleted).count())
    num_active_users.set(
        User.query
        .filter(Identity.last_login_dt > (now - active_user_age))
        .join(Identity).group_by(User).count()
    )
    num_categories.set(Category.query.filter(~Category.is_deleted).count())

    attachment_stats = cache.get('metrics_heavy')
    if not attachment_stats:
        attachment_stats = get_attachment_stats()
        cache.set('metrics_heavy', attachment_stats, timeout=heavy_cache_ttl)

    num_active_attachment_files.set(attachment_stats['num_active'])
    num_attachment_files.set(attachment_stats['num_total'])

    size_active_attachment_files.set(attachment_stats['size_active'])
    size_attachment_files.set(attachment_stats['size_total'])

    if LIVESYNC_AVAILABLE:
        size_livesync_queues.set(LiveSyncQueueEntry.query.filter(~LiveSyncQueueEntry.processed).count())
        num_livesync_events_category_changes.set(
            db.session.query(db.func.sum(Category.deep_events_count))
            .join(LiveSyncQueueEntry)
            .filter(~LiveSyncQueueEntry.processed, LiveSyncQueueEntry.type == 1)
            .scalar() or 0
        )

    num_notes.set(get_note_query().count())

    num_rooms.set(Room.query.filter(~Room.is_deleted).count())
    num_active_rooms.set(Room.query.filter(~Room.is_deleted, Room.is_reservable).count())
    num_restricted_rooms.set(
        Room.query.filter(~Room.is_deleted, Room.protection_mode == ProtectionMode.protected).count()
    )
    num_rooms_with_confirmation.set(Room.query.filter(~Room.is_deleted, Room.reservations_need_confirmation).count())

    num_bookings.set(Reservation.query.filter(~Room.is_deleted).join(Room).count())
    num_valid_bookings.set(Reservation.query.filter(~Room.is_deleted, ~Reservation.is_rejected).join(Room).count())
    num_pending_bookings.set(
        Reservation.query.filter(
            ~Room.is_deleted,
            Reservation.is_pending,
            ~Reservation.is_archived
        ).join(Room).count()
    )

    num_occurrences.set(ReservationOccurrence.query.count())
    num_valid_occurrences.set(
        ReservationOccurrence
        .query
        .filter(~Room.is_deleted, Reservation.is_accepted, ReservationOccurrence.is_valid)
        .join(Reservation)
        .join(Room)
        .count()
    )

    num_ongoing_occurrences.set(
        ReservationOccurrence
        .query
        .filter(
            ~Room.is_deleted,
            Reservation.is_accepted,
            ReservationOccurrence.is_valid,
            ReservationOccurrence.start_dt < now,
            ReservationOccurrence.end_dt > now
        ).join(Reservation)
        .join(Room)
        .count()
    )
