# Osu!IRC Bot Discord
A self-host discord bot that works like chat4osu, but in discord.  
Which means you can now ref on your phone directly from discord. Yay
## Table of contents
- [Installation](#installation)
- [Template](#template)
- [Hosting](#hosting)
## Installation <a name = "installation"></a>
- Download and install python (>=3.13)
- Clone this project or download as ZIP
- Extract and enter information into `configs.json`, template [Here](#template)
- Run DiscordIRCBot.py by doing Right click -> Open with -> Python (or just double click)
## Template <a name = "template"></a>
```json
{
    "token": "your_bot_token",
    "nick": "your_irc_username",
    "pass": "your_irc_password",
    "prefix": "idk_just_put_something_random",
    "irc_channel_id": discord_text_channel_id
}
```
## Hosting <a name = "hosting"></a>
- In case you don't want to run your pc 24/7, you can host the bot for free on [Replit](https://replit.com/) and use [UptimeRobot](https://uptimerobot.com/) to monitor it  
- [Here](https://github.com/DevSpen/24-7_hosting_replit) is a link to a tutorial. I already make a file named `DiscordIRCBot_host.py`, you only need to run that file on Replit and do the UptimeRobot part of the tutorial.