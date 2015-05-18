class Plugin(object):
    def __init__(self, compilation_database, pkg_config, threading_manager, configuration):
        self.compilation_database = compilation_database
        self.pkg_config = pkg_config
        self.threading_manager = threading_manager
        self.configuration = configuration
