# Zoom Videoconference Plugin

## Features

 * Creating Zoom meetings from Indico
 * Sharing Zoom meetings between more than one Indico event
 * Creating meetings on behalf of others
 * Changes of host possible after creation
 * Protection of Zoom link (only logged in, everyone or no one)
 * Webinar mode

## Changelog

### 3.2.4

- Adapt to Indico 3.2.6 changes
- Support Python 3.11

### 3.2.3

- Support Zoom's Server-to-Server OAuth in addition to the (deprecated) JWT

### 3.2.2

- Correctly show current "Mute video (host)" status when editing zoom meeting

### 3.2.1

- Do not break Zoom meetings that require registration when cloning or attaching to another event

### 3.2

- Adapt to Indico 3.2 changes
- Re-schedule (non-recurring) Zoom meetings when the event time gets changed

### 3.1.4

- Fix JS error on the dropdown for "make me co-host"

### 3.1.3

- Fix error with user identifiers (in "authenticators" lookup mode) containing a forward slash

### 3.1.2

- Do not include Zoom link in event descriptions returned by the HTTP API (iCalendar files for
  events and categories are no longer generated through the API and other consumers of the API
  typically do not expect Zoom links in there)

### 3.1.1

- Fix processing webhooks for Zoom meetings updated/deleted outside Indico

### 3.1

- Adapt to Indico 3.1 changes (include Zoom link in event reminder emails regardless of visibility)

### 3.0.2

- Fix JavaScript being included twice on conference VC page
- Fix JavaScript error breaking the "make me co-host" button

### 3.0.1

- Adapt to Indico 3.0.3 changes (option to show videoconference link on the main conference page)

### 3.0

- Adapt to Indico 3 (and thus Python 3)

### 2.3

- Fix deleting Zoom meetings that were already deleted on the Zoom side when running outside a web request context (e.g. during scheduled deletion of events)
- Fix overwriting co-hosts added via the Zoom client when using "make me co-host" in Indico
- Always refresh data from Zoom before editing via Indico to avoid saving with stale data
- Add option to link to an external page with phone-in instructions
- Fix showing the zoom join link in the info box

### 2.3b2

- Improve logging when a Zoom API request fails
- Fail more gracefully if no Zoom account could be found for a user
- Allow using the same name for multiple Zoom rooms
- Update the join url when changing the passcode
- Provide an alternative method of looking up the Zoom user corresponding to an Indico user
- Always show the full join link and passcode to event managers
- The meeting passcode can be restricted to registered participants
- Show "Make me host" button in the management area and in contributions/sessions as well
- Warn the user if they delete a Zoom meeting linked to multiple events if they aren't the host
- Change Zoom meeting to "recurring meeting" when cloning an event
- Show detailed error when deleting a meeting fails
- Do not allow passcodes that are too long for zoom
- Remove the "Assistant Zoom ID" logic due to problems with Zoom's API rate limits (all meetings created were counted against the assistant's rate limit instead of the host's); this means the host can no longer be changed, but Indico instead provides an option to event managers to make themselves a co-host.
- Fix an error when changing the linked object of a recurring Zoom room in Indico
- Include Zoom join links in the event's ical export (note: only Zoom meetings with a public passcode are displayed unless you have at least Indico v2.3.3)
- Skip deleted Zoom meetings when cloning events
- Mark Zoom meetings as deleted when receiving the corresponding webhook event
- Add missing admin-level settings for VC managers, creation ACL and notification email addresses

**Breaking change:** The email domains are now stored as a list of strings instead of a comma-separated list. You need to update them in the plugin settings.

### 2.3b1

- Initial beta release

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
 * **E-mail domains** - List of e-mail domains which can be used for the Zoom API (e.g. `cern.ch`)
 * **Webhook token** (optional) - the token which Zoom requests will authenticate with (get it from Zoom Marketplace)


### Zoom Server-to-Server OAuth

See the [zoom documentation](https://marketplace.zoom.us/docs/guides/build/server-to-server-oauth-app/#create-a-server-to-server-oauth-app) on how to get the credentials for authenticating with the Zoom servers.

The scopes to select when creating the app are:

- `meeting:read:admin`
- `meeting:write:admin`
- `user:read:admin`
- `webinar:read:admin` (optional, only needed when using webinars)
- `webinar:write:admin` (optional, only needed when using webinars)


### Zoom API key/secret (JWT, deprecated)

Zoom deprecated JWTs in June 2023, existing ones still work but no new ones can be created.
As soon as Zoom fully dropped them, JWT support will also be removed from this plugin.


## Intellectual Property

Developed by Giovanni Mariano @ **ENEA Frascati**, based on the Vidyo Plugin by the Indico Team at **CERN**. Further
improvements and modifications added by the Indico Team.

This package is Open Source Software licensed under the [MIT License](https://opensource.org/licenses/MIT).

**© Copyright 2020 CERN and ENEA**
