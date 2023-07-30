import json
import os
import configparser


config = configparser.ConfigParser()
config.read(os.path.abspath(os.path.join(".ini")))
