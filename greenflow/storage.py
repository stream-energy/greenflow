from tinydb import TinyDB
from munch import *

db = TinyDB("db.json", sort_keys=True, indent=4, separators=(",", ": "))
