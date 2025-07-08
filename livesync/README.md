# LiveSync Plugin

The LiveSync plugin provides a framework for exporting Indico event data to
external services, typically to provide advanced search functionality.

## Changelog

### 3.3.3

- Do not register Celery task unless the plugin is enabled

### 3.3.2

- Update translations

### 3.3.1

- Update translations

### 3.3

- Support (and require) Python 3.12

### 3.2.1

- Adapt to Indico 3.2.6 changes
- Support Python 3.11

### 3.2

- Adapt to Indico 3.2 changes

### 3.1

- Adapt to Indico 3.1 changes

### 3.0.1

- Add `indico livesync enqueue` CLI to manually add queue entries

### 3.0

- Initial release for Indico 3.0
- Major changes to improve efficiency and correctness of the data sent both
  during an initial data export and during queue runs
