from Logger import logger
from IRC.OsuSocket import OsuSocket
from dotenv import load_dotenv

import os

load_dotenv()

nick = os.environ.get("NICK", "")
passw = os.environ.get("PASSW", "")
s = OsuSocket()
s.start(nick, passw)