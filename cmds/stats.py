# Statistics Cog

# Importing Libraries
from discord.ext import commands
from classes.perms import allowed_channels

class Stats(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.command()
    @allowed_channels(["bot_cmds","t_chat"])
    async def ping(self, ctx):
        msg = await ctx.send(":ping_pong: Calculating latency...")
        latency = round(self.client.latency,4) * 1000
        raw_response_time = (msg.created_at - ctx.message.created_at).total_seconds()
        response_time = round(raw_response_time,4) * 1000

        await msg.edit(content=f":link: Websocket Latency: `{latency}ms`\n:speech_balloon: Response Time: `{response_time}ms`")