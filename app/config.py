import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.abspath(os.path.join(".ini")))


class Settings:
    def __init__(self, section):
        self.section = section

    def get(self, key):
        return config.get(self.section, key)

production_config = Settings("production")
testing_config = Settings("test")
