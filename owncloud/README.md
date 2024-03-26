# OwnCloud integration plugin

This plugin enables integration with an ownCloud server, for the purpose of
attaching materials to an event or category. A new "from the cloud" button
shows up in the materials section which enables managers to log into their
ownCloud account and pick files from their personal storage. Those files will
be copied as attachments.

## Setting up the ownCloud File-picker

This plugin uses an external [File-picker](https://github.com/owncloud/file-picker)
iframe.

It is recommended to set up the File-picker server in the same domain as the
ownCloud instance, to facilitate authentication. CERNBox provides
[a wrapper](https://github.com/cernbox/file-picker-wrapper) with a slightly
modified File-picker which handles message passing to the parent app as well as
different styling and configuration options.

You can also check out [the docs](https://filepicker.cernbox.cern.ch/docs/) for
it.

## Changelog

### 3.3

- Adapt to changes in Indico 3.3
- Support (and require) Python 3.12

### 3.2.2

- Support Python 3.11

## 3.2.1

- Disable the confirmation button in the 'add files' dialog if the File-picker
  is working or selection is empty

### 3.2

- Initial release for Indico 3.2
