# URL Shortener Plugin (ursh)

This plugin adds the ability to create shortcut URLs using the external
[ursh][ursh] URL shortening microservice to Indico.

Please note that you need to deploy your own instance of ursh in order to
use this plugin.

Ideally you also have a very short domain name for the short URLs; if you do
not own such a domain, it is not recommended to use this plugin but rather use
the builtin shortcut URL feature of Indico which lets event organizers define
human-friendly shortcuts pointing to an event (such as `https://indico.example.com/e/cool-event`).

## Changelog

### 3.2.2

- Support Python 3.11

### 3.2.1

- Stop using deprecated URL utils from werkzeug

### 3.2

- Update translations

### 3.1

- Adapt to Indico 3.1 changes

### 3.0

- Initial release for Indico 3.0


[ursh]: https://github.com/indico/ursh
