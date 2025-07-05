from typing import Any
from datetime import datetime

import re

class Channel:
    def __init__(self, name: str) -> None:
        self.name                                = name
        self.type                                = self.resolve_chat_type(name)
        self.id                                  = 0
        self.users:    set[str]                  = set()
        self.messages: list[str]                 = []
        self.staged_messages: list[str]          = []
        self.patterns: dict[str, Any]            = {
            r"BanchoBot : (.*) joined in slot \\d.": self.add_user,
            r"BanchoBot : (.*) left the game.": self.remove_user,
        }
    
    def resolve_chat_type(self, name: str):
        if name.startswith("#mp_"):
            self.id = int(name.split("_")[1])
            return "lobby"
        if name.startswith("#"):
            return "chat"
        return "DM"

    def add_user(self, names: list[str]):
        self.users.update(names)

    def remove_user(self, name: str) -> int:
        if name in self.users:
            self.users.remove(name)
            return 1
        return 0

    def update(self, data: list[str]):
        current_time = datetime.now().strftime("%H:%M:%S")
        message = "[%s] %s: %s" % (current_time, data[2], data[3])

        self.messages.append(message)
        self.staged_messages.append(message)

        for pattern, action in self.patterns.items():
            found = re.search(pattern, message)
            
            if found:
                action(found.group(1))
                return

    def get_all_messages(self) -> list[str]:
        return self.messages
    
    def get_staged_message(self) -> list[str]:
        messages = self.staged_messages.copy()
        self.staged_messages = []
        return messages