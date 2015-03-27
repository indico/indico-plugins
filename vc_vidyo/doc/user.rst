===========
Vidyo rooms
===========
Vidyo rooms are one of the types of videoconference rooms available in Indico. They are provided and managed by the
Vidyo plugin.

Event managers
==============
As an event manager, you have the possibility to create, add, edit and remove Vidyo rooms for your event, in the same
way as for any other kind of videoconference room.

Vidyo specific room options
---------------------------
In addition to the base options for videconference rooms: `name`, `linked to` and `show room`
(see ``VC_MODULE_VC_ROOM_OPTIONS``), a Vidyo room also possesses the following options:

========================= ============================================================================
Option                    Description
========================= ============================================================================
Description               the description of the room
Owner                     the owner of the room
Moderation PIN            code to gain moderation capabilities in the Vidyo room,
                          leave blank to disable (no one can gain moderation capabilities)
Room PIN                  code to enter the Vidyo room, leave blank to have a public room
Auto mute                 whether people will join with their web cam and mic disabled by default
Show PIN                  whether to show the `room PIN` on the Indico event page

                            **WARNING**: Showing the Vidyo room's pin on the event page is insecure.
                            Anyone could see the pin and join the room.
Show auto-join URL        whether to show the URL to auto-join the Vidyo room on the event page
Show phone access numbers whether to show a link to the list of phone access numbers on the event page
========================= ============================================================================


Creating a Vidyo room for an event
----------------------------------
To create a Vidyo room, go to the management area of your event and on the side menu on the left, select
`Videoconference`. Then click on the button `Create a new room`, a pop-up is displayed, prompting you to select the type
of video service you would like to use. Select the Vidyo badge. This will take you to the room creation form.

    **NOTE**: If only Vidyo is available as video service, then the `Create a new room` button is replaced with a
    `Create new Vidyo room` button which will take you directly to the room creation form.

In addition to the base options (see ``LINK_TO_VC_MODULE_CREATE_ROOM``), you can set the following Vidyo specific
options when creating the room:

- description
- owner
- moderation pin
- room pin
- auto mute
- show room
- show auto-join URL
- show phone access numbers

Add an existing Vidyo room to an event
--------------------------------------
To add an existing Vidyo room, go to the management area of your event and on the side menu on the left, select
`Videoconference`. Then click on the button `Add existing room`, a pop-up is displayed, prompting you to select the type
of video service you would like to use. Select the Vidyo badge. This will take you to the room attachment form.

    **NOTE**: If only Vidyo is available as video service, then the `Add existing room` button will not ask you to
    select a video service and instead display the room attachment form directly in the pop-up.

On the room attachment form, you can search for the name of the room you want to attach to the event; as well as set the
base options to attach any kind of videoconference room (see ``LINK_TO_VC_MODULE_ATTACH_ROOM``)

In addition you can set the following Vidyo options:

- show room
- show auto-join URL
- show phone access numbers

Review Vidyo rooms
------------------
Vidyo rooms are listed among the other videoconference rooms in the videconference section of your event's management
area. You can identify Vidyo rooms by the Vidyo logo on the left hand side of a room entry in the list (see
``LINK_TO_VC_MODULE_MANAGEMENT_ROOMS_LIST``).

You can see the Vidyo specific options by clicking on the arrow at the very left of the Vidyo logo.

Edit a Vidyo room
---------------------------
You can edit a Vidyo room like any other videoconference room by clicking on the pencil icon next to the room's name.
This will bring you to the room edit form, where you will be able to set all the base and Vidyo specific options.

Be aware that whilst the show room, show auto-join URL and show phone access numbers options can be set individually per
event for the same room, the other options are only specific to the room. That is if you change, for example the room
PIN, it will be changed for the room itself and people coming to the room from another event will have to know the new
PIN to access the room.

Delete a Vidyo room
-------------------
You can delete a Vidyo room like any other videoconference room by clicking on the trash icon next to the room's name.

Be aware that if the room is not attached to another event in Indico, it will be deleted from Vidyo as well and you will
not be able to add it back. But if a room is attached to many events, deleting it from one event will only remove it
from that event but not from the others or from Vidyo itself. In that case you can add the room back to the event with
the `Add existing room` button (see `Add an existing Vidyo room to an event`_)

Vidyo actions
=============
The Vidyo plugin also provides actions directly from an Indico event page or from the event's videoconference page in
the case of conferences (and from the management area as well for event managers).

Join
----
You can join a Vidyo room by clicking the blue Join button next to a room's name. This will connect you to the Vidyo
room through am available Vidyo client, usually the VidyoDesktop™ or VidyoMobile™ client.

Make me moderator
-----------------
This action is only available on the event page or from the event's videoconference page in the case of conferences. It
allows someone to replace the current moderator of a room with himself. This is equivalent to editing the room and set
the owner of the room as yourself.

The action is only be available to event managers who are not the moderator of the room. If available it will be shown
as a drop-down next to the `join`. Clicking on the drop-down arrow, a menu with the `Make me owner` will appear. Then
click on `Make me an owner` to set yourself as the owner of the room.

Vidyo room details
==================
Details regarding a Vidyo room are visible on the event page or from the event's videoconference page in the case of
conferences. They are accessible in the same way as any videoconference room details (see
``LINK_TO_VC_MODULE_SEE_ROOM_DETAILS``)

    **NOTE**: The auto-join URL is intended to be copied and pasted in emails and other places to give people a way to
    automatically join the Vidyo room. To join the room from the Indico page, you should instead use the `join`_ button.
    The link might appear to be cut if it is very long as it overflows, the easiest way to make sure you have copied the
    entire link correctly is to use the copy button to the right of the link.
