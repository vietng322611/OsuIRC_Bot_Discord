from collections import defaultdict
from .Channel import Channel
from typing import Any

import logging
class IrcManager:
    def __init__(self):
        self.logger                        = logging.getLogger('IrcManager')
        self.chat_list: dict[str, Channel] = defaultdict()
        self.nick                          = ""
        self.passw                         = ""

    def clear(self):
        self.chat_list = {}
        self.nick      = ""
        self.passw     = ""

    def get_chat_list(self) -> list[Channel]:
        return list(self.chat_list.values())

    def get_chat(self, name: str) -> (Channel | None):
        return self.chat_list.get(name)

    def add_chat(self, name: str):
        if not self.chat_list.get(name):
            self.chat_list[name] = Channel(name)

    def remove_chat(self, name: str):
        if self.chat_list.get(name):
            del self.chat_list[name]

    def update(self, data: list[str]):
        if len(data) == 0: return

        name = data[1]
        try:
            match (data[0]):
                case "0": # join
                    if data[2] == self.nick:
                        self.add_chat(name)
                    self.chat_list[name].add_user(data[2:len(data)])

                case "1": # message
                    if name == self.nick:
                        name = data[2]
                    if not self.chat_list.get(name):
                        self.add_chat(name)
                    self.chat_list[name].update(data)

                case "2": # leave
                    if data[2] == self.nick:
                        self.remove_chat(name)
                    else:
                        self.chat_list[name].remove_user(data[2])
        except Exception as e:
            self.logger.error(e, exc_info=True)

    async def listen_for_pattern(self, chat_name: str, pattern: str) -> tuple[str | Any, ...]:
        chat = self.get_chat(chat_name)
        if not chat:
            return tuple()
        return await chat.listen_for_pattern(pattern)

ircManager = IrcManager()