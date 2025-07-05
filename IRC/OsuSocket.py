from time import sleep

from . import Utils
from .Manager import manager
from .Parser import parse
from .Exceptions import ConnectionError, OsuCredentialsIncorrect, NoSuchChannel

import socket
import asyncio
import logging

class OsuSocket:
    def __init__(self) -> None:
        self.socket                    = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger                    = logging.getLogger('OsuSocket')
        self.queue: asyncio.Queue[str] = asyncio.Queue(128)
        self.disconnect                = False

    def start(self, nick: str, passw: str):
        try:
            asyncio.run(self.connect(nick, passw))
        except OsuCredentialsIncorrect as e:
            self.logger.error(e, exc_info=True)
            raise e
        except ConnectionError as e:
            self.logger.exception(e, exc_info=True)
            raise e
        
        self.logger.info("Osu!IRC authenticated")

        async def monitor_connection():
            while True:
                if self.disconnect:
                    self.logger.info("Disconnected, trying to reconnect")
                    try:
                        await self.reconnect()
                    except Exception as e:
                        self.logger.exception(e, exc_info=True)
                        return
                await asyncio.sleep(1)

        try:
            asyncio.run(monitor_connection())
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
    
    def cleanup(self):
        self.disconnect = True
        Utils.stop_async()
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except Exception as e:
            self.logger.exception(e, exc_info=True)
        finally:
            self.socket.close()
        self.disconnect = False

    async def connect(self, nick: str, passw: str):
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

        try_connect(0)
        await self.authenticate(nick, passw)

        self.start_services(self.recv, self.keep_alive, self.read_line)

        manager.clear()
        manager.nick = nick
        manager.passw = passw
        
        await self.join("BanchoBot")
        await self.join("#thisisnotarealchat")

    async def authenticate(self, nick: str, passw: str):
        self.send("PASS %s" % passw)
        self.send("NICK %s" % nick)
        remain = ""
        while not self.disconnect:
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
                            for j in range(i+1, len(data)):
                                await self.queue.put(data[j])
                            return
                remain = data.pop()
                await asyncio.sleep(0.05)
            except Exception as e:
                self.disconnect = True
                raise e
        raise ConnectionError("Disconnected during authentication")
    
    def start_services(self, *args):
        if len(args) < 1: return

        for service in args:
            Utils.submit_async(service())

    async def logout(self):
        try:
            self.send("QUIT")
        except Exception as e:
            self.logger.exception(e, exc_info=True)
            raise e

    async def reconnect(self):
        self.cleanup()
        await self.connect(manager.nick, manager.passw)

    async def recv(self):
        remain = ""
        while not self.disconnect:
            try:
                response: str = remain + self.socket.recv(1024).decode("utf-8")
                data = response.split("\n")
                remain = data.pop()
                for line in data:
                    line = line.strip()
                    if (line == ""): continue
                    await self.queue.put(line)
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                self.logger.debug("Cancelling recv")
                return
            except Exception as e:
                self.logger.exception(e, exc_info=True)
                self.disconnect = True
                return

    async def read_line(self):
        while not self.disconnect:
            try:
                msg = await self.queue.get()
                if msg != "":
                    if msg.find("QUIT") == -1: self.logger.debug(msg)
                    if msg == "PING cho.ppy.sh":
                        self.send(msg)
                    parsed_msg = parse(msg)
                    manager.update(parsed_msg)
                await asyncio.sleep(0.05)
            except NoSuchChannel as e:
                self.logger.error(e, exc_info=True)
                await asyncio.sleep(0.05)
                continue
            except asyncio.CancelledError:
                self.logger.debug("Cancelling read_line")
                return
            except Exception as e:
                self.disconnect = True
                self.logger.exception(e, exc_info=True)
                return

    async def keep_alive(self):
        while not self.disconnect:
            try:
                self.send("KEEP_ALIVE")
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                self.logger.debug("Cancelling keep_alive")
                return
            except Exception as e:
                self.disconnect = True
                self.logger.exception(e, exc_info=True)
                return

    def send(self, message: str):
        try:
            self.socket.sendall(bytes(message + '\n', encoding="utf-8"))
        except Exception as e:
            self.disconnect = True
            self.logger.exception(e, exc_info=True)

    async def join(self, chat: str):
        if not manager.get_chat(chat):
            if chat.startswith('#'):
                self.send(f"JOIN {chat}")
            else:
                manager.add_chat(chat)
        
    
    def part(self, chat: str):
        if manager.get_chat(chat):
            self.send(f"PART {chat}")
            manager.remove_chat(chat)

    async def privmsg(self, chat: str, message: str):
        if not manager.get_chat(chat):
            await self.join(chat)
        self.send(f"PRIVMSG {chat} {message}")