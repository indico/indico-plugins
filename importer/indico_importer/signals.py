from blinker import Namespace

_signals = Namespace()

register_importers = _signals.signal('add-importers', """
Called on plugin registering importers. Expects a list of `DataImporter`
objects the plugin will keep track of.
""")
