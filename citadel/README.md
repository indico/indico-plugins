# Citadel Search Plugin

The Citadel plugin integrates Indico with the [Citadel][citadel] microservice
to provide advanced search functionality using an Elasticsearch backend.

## Changelog

### 3.3

- Adapt to Indico 3.3 changes
- Support Python 3.12
- Add option to show a warning in large categories, encourating managers to use groups instead of
  individual ACL entries (to avoid having to re-send huge amounts of data to the backend)

### 3.2.2

- Adapt to Indico 3.2.6 changes
- Support Python 3.11

### 3.2.1

- Stop using deprecated URL utils from werkzeug

### 3.2

- Update translations

### 3.1

- Adapt to Indico 3.1 changes
- Correctly handle remote groups whose capitalization changed at some point

### 3.0

- Initial release


[citadel]: https://gitlab.cern.ch/webservices/cern-search/cern-search-rest-api
