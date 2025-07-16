from typing import Any
from datetime import datetime

import re
import asyncio

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

        if hasattr(self, '_match_event'):
            _match_event, _pattern = self._match_event
            found = re.search(_pattern, message)
            if found:
                _match_event.set()
                self._match_result = found.groups()

        for pattern, action in self.patterns.items():
            found = re.search(pattern, message)
            if found:
                action(found.group(1))
                return

    def get_all_messages(self) -> list[str]:
        return self.messages
    
    def get_staged_messages(self) -> list[str]:
        messages = self.staged_messages.copy()
        self.staged_messages = []
        return messages
    
    async def listen_for_pattern(self, pattern: str) -> tuple[str | Any, ...]:
        match_event = asyncio.Event()
        self._match_event = (match_event, pattern)
        try:
            _, pending = await asyncio.wait(
                [
                    asyncio.create_task(match_event.wait())
                ],
                return_when = asyncio.FIRST_COMPLETED,
                timeout = 10
            )
            for task in pending:
                task.cancel()

            if not match_event.is_set():
                return tuple()
            
            if hasattr(self, '_match_result'):
                return self._match_result
            return tuple()
        finally:
            del self._match_event
            if hasattr(self, '_match_result'):
                del self._match_result