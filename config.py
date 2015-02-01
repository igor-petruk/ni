import configparser
import os

class Configuration(object):
    def __init__(self, config_files_list):
        if config_files_list:
            self.config = configparser.ConfigParser()
            my_config_path = os.path.expanduser(config_files_list[0])
            if os.path.exists(my_config_path):
                self.config.read(os.path.expanduser(my_config_path))
            self.next_configuration = Configuration(config_files_list[1:])
        else:
            self.config = None

        
    def Get(self, section, key, raise_exception=True, default=None):
        if not self.config:
            if raise_exception:
                raise KeyError(
                    "Section '[%s]', Key '%s' is not "
                    "specified in configs" % (section, key))
            else:
                return default
        if (section in self.config) and (key in self.config[section]):
            return self.config[section][key]
        else:
            return self.next_configuration.Get(section, key)

    def GetExpandedDir(self, *args, **kwargs):
        result = self.Get(*args, **kwargs)
        if result:
            return os.path.expanduser(result)
        else:
            return result
