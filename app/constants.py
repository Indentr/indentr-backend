import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.abspath(os.path.join(".ini")))
