# Indico Plugin for Zoom

## Features

 * Creating Zoom meetings from Indico;
 * Sharing Zoom meetings between more than one Indico event;
 * Creating meetings on behalf of others;
 * Changes of host possible after creation;
 * Protection of Zoom link (only logged in, everyone or no one)
 * Webinar mode;

## Changelog

### 2.3b3

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


### Zoom API key/secret (JWT)

To obtain API key and API secret, please visit [https://marketplace.zoom.us/docs/guides/auth/jwt](https://marketplace.zoom.us/docs/guides/auth/jwt).


## Intellectual Property

Developed by Giovanni Mariano @ **ENEA Frascati**, based on the Vidyo Plugin by the Indico Team at **CERN**. Further
improvements and modifications added by the Indico Team.

This package is Open Source Software licensed under the [MIT License](https://opensource.org/licenses/MIT).

**© Copyright 2020 CERN and ENEA**
