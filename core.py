# Core Functions

# Importing libraries
import json
from datetime import datetime
from time import strftime
import discord
import requests
from classes.channel import Channel


def ReadJSON(file):
    """
    Reads a JSON file in the data directory.
    """
    with open("data/"+file, 'r') as f:
        o = json.load(f)
        return o


def Overwrite(data, file):
    """
    Overwrites the JSON file with the data provided.
    """
    with open("data/"+file, 'w') as f:
        json.dump(data, f)
        return


def Save(data, file):
    """
    Safely overwrites saves and logs warnings in case of a fail.
    """
    path = "data/"+file
    stime = strftime("%H'%M'%S (%d.%m.%y)")
    with open(path, 'r') as f:
        o = json.load(f)
    if len(data) >= len(o):
        with open(path, 'w') as f:
            json.dump(data, f)
        print("Data saved at "+stime)
        return
    fname = path[:-5]
    with open(fname + f" - backup ({stime}).json", "w") as w:
        json.dump(o, w)
    with open(path, 'w') as f:
        json.dump(data, f)
    dlen = str(len(data))
    olen = str(len(o))
    print(
        f"WARNING: Backup created due to loss of data at {stime} ({olen} to {dlen})")
    Log("Backup Created", description="Loss of data at " + stime, color=discord.Color.orange(),
        fields=[{"name": "Original Data Size", "value": olen}, {"name": "New Data Size", "value": dlen}])
    return


def OnlineIn(members):
    """
    Returns the amount of members from a member list who are not in Offline status.
    """
    c = 0
    for member in members:
        if member.status != discord.Status.offline:
            c += 1
    return c


def Log(title, description=None, color=0xaaaaaa, fields=None):
    """
    Logs an action or error in the appropriate Discord channel.
    """
    fields = fields or []
    embed = discord.Embed(title=title, description=description,
                          color=color, timestamp=datetime.utcnow())
    for field in fields:
        embed.add_field(name=field['name'], value=field['value'])
    e = embed.to_dict()
    body = {"embeds": [e]}
    headers = {"Content-Type": "application/json"}
    url = ReadJSON("config.json")["webhook_url"]
    url += ReadJSON("tokens.json")["webhook_token"]
    requests.post(data=json.dumps(body), headers=headers, url=url)


def UpdatedPresence(client):
    """
    Returns the updated client activity.
    """
    config = ReadJSON("config.json")
    members = client.get_guild(config['guild_id']).members
    online = OnlineIn(members)
    activity = discord.Activity(name=str(len(
        members)) + " members | " + str(online) + " online", type=discord.ActivityType.watching)
    return activity


def TimeUntil(dt):
    """
    Returns the time from now until the datetime as a string.
    """
    t = datetime.utcnow()
    tdelta = dt - t
    s = tdelta.total_seconds()
    if s < 0:
        raise ValueError
    d, r = divmod(s, 86400)
    h = r // 3600
    if d > 7:
        w, d = divmod(d, 7)
        ft = f"{w} week and {d} day"
        if w > 1:
            i = ft.find(" a")
            ft = ft[:i] + "s" + ft[i:]
        if d > 1:
            ft += "s"
    elif d == 7:
        ft = "1 week"
    elif d > 2:
        ft = f"{d} days"
    elif d > 0:
        ft = f"{d} day and {h} hour"
        if d > 1:
            i = ft.find(" a")
            ft = ft[:i] + "s" + ft[i:]
        if h > 1:
            ft += "s"
    elif h > 0:
        ft = f"{h} hour"
        if h > 1:
            ft += "s"
    else:
        ft = "less than 1 hour"
    ft = ft.replace(".0", "")  # Remove floats
    return ft


def ModifierCheck(mod, iterable):
    """
    Checks if the modifier is in the iterable. Returns their index if predicate is valid.
    """
    try:
        index = iterable.index(mod)
    except ValueError:
        index = next((index for (index, d) in enumerate(iterable)
                      if isinstance(d, dict) and d['name'] == mod), False)
    return index

async def SendFirstTournamentMessage(ctx):
    user = ctx.author
    embed = discord.Embed(title="Welcome to your first tournament!",
                          description=(f"Hey {user.mention}, you have joined a tournament for the"
                                       " first time! If you are confused, don't worry! I'm here"
                                       " to remind you of the essential steps of a tournament."),
                          color=discord.Color.green())

    embed.add_field(name="Before the game starts, you can chat with fellow participants.",
                    value=("When you join a tournament, you get access to "
                           f" {Channel(ctx.bot).t_chat.mention} (`{Channel(ctx.bot).t_chat.name}`)"
                           ", where you can discuss with other players while waiting for the game"
                           " to fill up!"),
                           inline=False)
    
    embed.add_field(name="Once the host is ready, you will be able to join the game.",
                    value=("In the channel, you will be given the name and password of a custom"
                    " game to join in the Werewolf Online app! Open the Main Menu of the game,"
                    " then go to Play > Custom Games. Find the game in the list and click it, then"
                    " type the password you were given."),
                    inline=False)
    
    embed.add_field(name="Once everyone has joined, the battle will begin!",
                    value="Good luck and happy hunting!",
                    inline=False)
    
    await user.send(embed=embed)

def UpdatedEmbed(tournament):
    embed = tournament.embed_message()
    embed.title = tournament.name
    if tournament.status == 3:
        index = ModifierCheck("MaxParticipants", tournament.modifiers)
        if index is not False:
            limit = tournament.modifiers[index]['value']
        else:
            limit = 15
        count = len(tournament.participants)
        if count >= limit:
            embed.colour = discord.Color.gold()
            embed.set_author(name="Tournament Full")
        else:
            embed.colour = discord.Color.green()
            embed.set_author(name="Tournament Open")
    else:
        embed.colour = discord.Color.dark_orange()
        embed.set_author(name="Tournament Started")
    
    return embed