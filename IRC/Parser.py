from .Exceptions import NoSuchChannel

def parse(message: str) -> list[str]:
    '''
        :cho.ppy.sh 353 [nick] = [channel_name] :[name_list]
        :[name]!cho@ppy.sh PRIVMSG [channel_name] :[message]
        :cho.ppy.sh 403 [nick] [channel_name] :No such channel
    '''
    if message.startswith("PING"): return []

    data = message.split(":")
    mData = data[1].split(" ")

    if (mData[1] == "QUIT"): return []

    retData = []
    match (mData[1]):
        case "401" | "403":
            raise NoSuchChannel(mData[3])
        case "323" |"353":
            # indicator, channel, username
            retData += ["0", mData[4], data[2].split(" ")]

        case "JOIN":
            # indicator, channel, username
            retData += ["0", data[2], mData[0].split("!")[0]]

        case "PRIVMSG":
            # indicator, channel, username, message
            retData += [
                "1",
                mData[2],
                mData[0].split("!")[0], 
                ":".join(data[2: len(data)])
            ]
        case "PART":
            # indicator, channel, username
            retData += ["2", data[2], mData[0].split("!")[0]]
    return retData