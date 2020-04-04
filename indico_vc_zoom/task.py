

from __future__ import unicode_literals

from datetime import timedelta

from celery.schedules import crontab

from indico.core.celery import celery
from indico.core.db import db
from indico.core.plugins import get_plugin_template_module
from indico.modules.events import Event
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomStatus
from indico.modules.vc.notifications import _send
from indico.util.date_time import now_utc
from indico.util.struct.iterables import committing_iterator

from indico_vc_zoom.api import APIException, RoomNotFoundAPIException


def find_old_zoom_rooms(max_room_event_age):
    """Finds all Zoom rooms that are:
       - linked to no events
       - linked only to events whose start date precedes today - max_room_event_age days
    """
    recently_used = (db.session.query(VCRoom.id)
                     .filter(VCRoom.type == 'zoom',
                             Event.end_dt > (now_utc() - timedelta(days=max_room_event_age)))
                     .join(VCRoom.events)
                     .join(VCRoomEventAssociation.event)
                     .group_by(VCRoom.id))

    # non-deleted rooms with no recent associations
    return VCRoom.find_all(VCRoom.status != VCRoomStatus.deleted, ~VCRoom.id.in_(recently_used))


def notify_owner(plugin, vc_room):
    """Notifies about the deletion of a Zoom room from the Zoom server."""
    user = vc_room.zoom_meeting.owned_by_user
    tpl = get_plugin_template_module('emails/remote_deleted.html', plugin=plugin, vc_room=vc_room, event=None,
                                     vc_room_event=None, user=user)
    _send('delete', user, plugin, None, vc_room, tpl)


@celery.periodic_task(run_every=crontab(minute='0', hour='3', day_of_week='monday'), plugin='vc_zoom')
def zoom_cleanup(dry_run=False):
    from indico_vc_zoom.plugin import ZoomPlugin
    max_room_event_age = ZoomPlugin.settings.get('num_days_old')

    ZoomPlugin.logger.info('Deleting Zoom rooms that are not used or linked to events all older than %d days',
                            max_room_event_age)
    candidate_rooms = find_old_zoom_rooms(max_room_event_age)
    ZoomPlugin.logger.info('%d rooms found', len(candidate_rooms))

    if dry_run:
        for vc_room in candidate_rooms:
            ZoomPlugin.logger.info('Would delete Zoom room %s from server', vc_room)
        return

    for vc_room in committing_iterator(candidate_rooms, n=20):
        try:
            ZoomPlugin.instance.delete_room(vc_room, None)
            ZoomPlugin.logger.info('Room %s deleted from Zoom server', vc_room)
            notify_owner(ZoomPlugin.instance, vc_room)
            vc_room.status = VCRoomStatus.deleted
        except RoomNotFoundAPIException:
            ZoomPlugin.logger.warning('Room %s had been already deleted from the Zoom server', vc_room)
            vc_room.status = VCRoomStatus.deleted
        except APIException:
            ZoomPlugin.logger.exception('Impossible to delete Zoom room %s', vc_room)
