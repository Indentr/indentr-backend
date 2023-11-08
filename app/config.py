import configparser
import os

configParser = configparser.ConfigParser()
configParser.read(os.path.abspath(os.path.join(".ini")))


class Settings:
    def __init__(self, section):
        self.section = section

    def get(self, key):
        return configParser.get(self.section, key)


config = Settings("production")
