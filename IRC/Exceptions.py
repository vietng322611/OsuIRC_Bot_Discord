class NoSuchChannel(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f"No such channel: {self.message}"

class ConnectionError(Exception):
    def __init__(self, message) -> None:
        super().__init__(message)
        self.message = message
    
    def __str__(self) -> str:
        return f"Failed to establish a connection to osu!irc server: {self.message}"
    
class OsuCredentialsIncorrect(Exception):
    def __init__(self, *arg) -> None:
        super().__init__(arg)
    
    def __str__(self) -> str:
        return "Failed to login using provided credentials"

class AuthenticationError(Exception):
    def __init__(self, message) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f"Failed to login: {self.message}"