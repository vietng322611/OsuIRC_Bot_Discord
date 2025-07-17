from time import sleep

from . import Utils
from .IrcManager import ircManager
from .Parser import parse
from .Exceptions import ConnectionError, OsuCredentialsIncorrect, NoSuchChannel
from .Channel import Channel

import socket
import asyncio
import logging

class OsuSocket:
    def __init__(self) -> None:
        self.socket                       = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger                       = logging.getLogger('OsuSocket')
        self.threadLoop                   = Utils.ThreadLoop()
        self._stop_event                  = asyncio.Event()
        self._pending_messages: list[str] = []

    def start(self, nick: str, passw: str):
        try:
            self.threadLoop.start_async()
            task = self.threadLoop.submit_async(self.connect(nick, passw))
            if task:
                task.result() # ensure `connect`` finished before submit `monitor_connection`
            self.threadLoop.submit_async(self.monitor_connection())

            for message in self._pending_messages:
                self.send(message)
            self._pending_messages.clear()
        except Exception as e:
            self.logger.error(e, exc_info=True)
            raise e

    def start_blocking(self, nick: str, passw: str):
        async def  _():
            while True:
                await asyncio.sleep(30)

        self.start(nick, passw)
        try:
            asyncio.run(_())
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
    
    def cleanup(self):
        self._stop_event.set()
        self.threadLoop.stop_async()
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except Exception as e:
            self.logger.exception(e, exc_info=True)
        finally:
            self.socket.close()
        self._stop_event = asyncio.Event()

    async def connect(self, nick: str, passw: str) -> int:
        def try_connect(retry_count: int):
            try:
                self.socket.connect(("irc.ppy.sh", 6667))
            except socket.timeout as e:
                if retry_count <= 5:
                    sleep(3)
                    return try_connect(retry_count + 1)
            except socket.error as err:
                raise ConnectionError(str(err))
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        await asyncio.to_thread(try_connect, 0)
        await self.authenticate(nick, passw)

        self.logger.info("Osu!IRC authenticated")

        self.start_services(self.recv, self.keep_alive)

        chat_list = ircManager.chat_list.copy()
        ircManager.clear()
        ircManager.nick = nick
        ircManager.passw = passw

        for chat, _ in chat_list.items():
            await self.join(chat)
        await self.join("BanchoBot")

        return 0

    async def monitor_connection(self):
        while True:
            if self._stop_event.is_set():
                self.logger.info("Disconnected, trying to reconnect")
                try:
                    await self.reconnect()
                except Exception as e:
                    self.logger.exception(e, exc_info=True)
                    return
                self.logger.info("Reconnected successfully")
            await asyncio.sleep(1)

    async def authenticate(self, nick: str, passw: str):
        self.send("PASS %s" % passw)
        self.send("NICK %s" % nick)
        remain = ""
        while not self._stop_event.is_set():
            try:
                response: str = self.socket.recv(1024).decode("utf-8")
                response = remain + response
                data = response.split("\r\n")
                for i in range(len(data) - 1):
                    line = data[i].split(" ")
                    match line[1]:
                        case "464":
                            raise OsuCredentialsIncorrect
                        case "376":
                            return
                remain = data.pop()
                await asyncio.sleep(0.05)
            except Exception as e:
                self._stop_event.set()
                raise e
        raise ConnectionError("Disconnected during authentication")
    
    def start_services(self, *args):
        if len(args) > 0:
            for service in args:
                self.threadLoop.submit_async(service())

    async def reconnect(self):
        self.cleanup()
        await self.connect(ircManager.nick, ircManager.passw)

    async def recv(self):
        remain = ""
        while not self._stop_event.is_set():
            try:
                response: str = remain + self.socket.recv(1024).decode("utf-8")
                data = response.split("\n")
                remain = data.pop()
                for msg in data:
                    msg = msg.strip()
                    if (msg == ""): continue
                    parsed_msg = parse(msg)
                    if len(parsed_msg) != 0:self.logger.debug(msg)
                    ircManager.update(parsed_msg)
                    if hasattr(self, '_join_events'):
                        if parsed_msg[2] != ircManager.nick: continue
                        chat_added_event, _ = self._join_events
                        chat_added_event.set()
                await asyncio.sleep(0.05)
            except NoSuchChannel as e:
                if hasattr(self, '_join_events'):
                    _, exception_event = self._join_events
                    exception_event.set()
                self.logger.error(e, exc_info=True)
                await asyncio.sleep(0.05)
                continue
            except asyncio.CancelledError:
                self.logger.debug("Cancelling recv")
                return
            except Exception as e:
                self.logger.exception(e, exc_info=True)
                self._stop_event.set()
                return

    async def keep_alive(self):
        while not self._stop_event.is_set():
            try:
                self.send("KEEP_ALIVE")
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                self.logger.debug("Cancelling keep_alive")
                return
            except Exception as e:
                self._stop_event.set()
                self.logger.exception(e, exc_info=True)
                return

    def send(self, message: str):
        try:
            self.socket.sendall(bytes(message + '\n', encoding="utf-8"))
        except Exception as e:
            self._stop_event.set()
            self.logger.exception(e, exc_info=True)
            self._pending_messages.append(message)

    async def join(self, chat: str) -> (Channel | None):
        if not ircManager.get_chat(chat):
            if chat.startswith('#'):
                self.send(f"JOIN {chat}")
                chat_added_event = asyncio.Event()
                exception_event = asyncio.Event()
                self._join_events = (chat_added_event, exception_event)
                
                try:
                    _, pending = await asyncio.wait(
                        [
                            asyncio.create_task(chat_added_event.wait()),
                            asyncio.create_task(exception_event.wait())
                        ],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task in pending:
                        task.cancel()
                    
                    if exception_event.is_set():
                        return None
                finally:
                    del self._join_events
            else:
                ircManager.add_chat(chat)
        return ircManager.get_chat(chat)
        
    
    def part(self, chat: str):
        if ircManager.get_chat(chat):
            self.send(f"PART {chat}")
            ircManager.remove_chat(chat)

    async def privmsg(self, chat: str, message: str):
        if not ircManager.get_chat(chat):
            await self.join(chat)
        self.send(f"PRIVMSG {chat} {message}")
        