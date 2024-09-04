# Official Indico Plugins

This package is a meta-package that installs the most common Indico plugins
that are developed by the core Indico development team.

It does not have any functionality by itself; its sole purpose is to provide
a single package that can be installed and updated easily.

## Changelog

### 3.3.1

- Update `indico-plugin-piwik`
- Update `indico-plugin-jupyter`

### 3.3

- Support (and require) Python 3.12

The major/minor version of this package should match the Indico version you
are using. So if you have Indico 3.0.x, then you should install version 3.0.x
of the `indico-plugins` package.

Note that we only make new releases of the plugin package as needed, so It would
be perfectly fine to have Indico 3.0.2 while still on `indico-plugins` 3.0.
