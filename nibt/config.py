import configparser
import os
import logging

class Configuration(object):
    def __init__(self, config_files_list):
        if config_files_list:
            self.config = configparser.ConfigParser()
            current_config_file = config_files_list[0]
            if isinstance(current_config_file, str):
                logging.info("Reading config from path %s", current_config_file)
                my_config_path = os.path.expanduser(current_config_file)
                if os.path.exists(my_config_path):
                    self.config.read(os.path.expanduser(my_config_path))
            else:
                logging.info("Reading config from stream %s", current_config_file)
                config_str =  ''.join([x.decode() for x in current_config_file.readlines()])
                self.config.read_string(config_str)
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
            return self.next_configuration.Get(section, key, raise_exception, default)

    def GetExpandedDir(self, *args, **kwargs):
        result = self.Get(*args, **kwargs)
        if result:
            return os.path.expanduser(result)
        else:
            return result
