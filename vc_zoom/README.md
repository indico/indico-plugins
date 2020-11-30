# Indico Plugin for Zoom

## Features

 * Creating Zoom meetings from Indico;
 * Sharing Zoom meetings between more than one Indico event;
 * Creating meetings on behalf of others;
 * Changes of host possible after creation;
 * Protection of Zoom link (only logged in, everyone or no one)
 * Webinar mode;

## Implementation details

Rooms are created under the account of an *assistant user* which can be set using the **Assistant Zoom ID**
configuration setting. This account will also be added automatically as an assistant to every meeting host.
This is needed in order to allow for the host to be changed ([`scheduled_for`](https://marketplace.zoom.us/docs/api-reference/zoom-api/meetings/meetingcreate#request-body) property in the Zoom API). The *assistant user* owns every Zoom meeting, with the `scheduled_for` property being
used to grant the required privileges to the desired hosts.

## Zoom App Configuration

### Webhook (optional)

**URL:** `https://yourserver/api/plugin/zoom/webhook`

(write down the "Verification Token", as you will need it in the plugin configuration below)

Select the following "Event types":
 * `Meeting has been updated`
 * `Meeting has been deleted`
 * `Webinar has been updated`
 * `Webinar has been deleted`


## Plugin Configuration

These are the most relevant configuration options:

 * **Notification email addresses** - Additional e-mails which will receive notifications
 * **E-mail domains** - Comma-separated list of e-mail domains which can be used for the Zoom API (e.g. `cern.ch`)
 * **Asistant Zoom ID** - Zoom ID (or e-mail) of the account which shall be used as an assistant to all hosts and
shall own all meetings
 * **Webhook token** (optional) - the token which Zoom requests will authenticate with (get it from Zoom Marketplace)


### Zoom API key/secret (JWT)

To obtain API key and API secret, please visit [https://marketplace.zoom.us/docs/guides/auth/jwt](https://marketplace.zoom.us/docs/guides/auth/jwt).


## Intellectual Property

Developed by Giovanni Mariano @ **ENEA Frascati**, based on the Vidyo Plugin by the Indico Team at **CERN**. Further
improvements and modifications added by the Indico Team.

This package is Open Source Software licensed under the [MIT License](https://opensource.org/licenses/MIT).

**© Copyright 2020 CERN and ENEA**
