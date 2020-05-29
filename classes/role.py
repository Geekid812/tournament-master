# Role Object

# Importing libraries
import discord.utils
import core
from time import sleep

guildid = core.ReadJSON("config.json")["guild_id"]

class Role:
    def __init__(self, client):
        for i in range(5):
            guild = client.get_guild(guildid)
            self.t_organizer = discord.utils.get(guild.roles, id=554385062313852968)
            self.schedule = discord.utils.get(guild.roles, id=555429481972498472)
            self.tournament = discord.utils.get(guild.roles, id=554309332418691083)
            self.participant = discord.utils.get(guild.roles, id=554308520481390643)
            self.spectator = discord.utils.get(guild.roles, id=692735821832519801)
            self.temp_host = discord.utils.get(guild.roles, id=554385586954305558)
            self.t_banned = discord.utils.get(guild.roles, id=553894764504678400)
            self.t_host_blacklist = discord.utils.get(guild.roles, id=559395242063953932)

            all_roles = [getattr(self, r) for r in dir(self) if not r.startswith("_")]

            if None not in all_roles: break
            if i < 4:
                print(f"Failed to load roles, retrying in 5 seconds. ({str(4 - i)} attempts left)")
                sleep(5)
            else:
                print("Failed to load roles!")