# Statistics Cog

# Importing Libraries
import discord
from discord.ext import commands
from classes.perms import allowed_channels
from classes.user import User


class Stats(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    @allowed_channels(["bot_cmds", "t_chat"])
    async def ping(self, ctx):
        msg = await ctx.send(":ping_pong: Calculating latency...")
        latency = round(self.client.latency, 4) * 1000
        raw_response_time = (
            msg.created_at - ctx.message.created_at).total_seconds()
        response_time = round(raw_response_time, 4) * 1000

        await msg.edit(content=f":link: Websocket Latency: `{latency}ms`\n:speech_balloon: Response Time: `{response_time}ms`")

    @commands.command(aliases=['statistics', 'status', 'stat', 'profile'])
    @allowed_channels(["bot_cmds"])
    async def stats(self, ctx, target: discord.Member = None):
        if target is None:
            target = ctx.author

        user = await User.fetch_by_id(ctx, target.id)
        losses = user.participations - user.wins

        if user.participations > 0:
            raw_win_rate = user.wins / user.participations * 100
            win_rate = str(round(raw_win_rate, 2)) + "%"
        else:
            win_rate = None
        
        if user.ign is not None:
            ign_text = user.ign
        else:
            ign_text = "`None`"
        
        xp_required = user.level * 100
        xp_percentage = int(user.xp / xp_required * 100)
        full_progress = f"{user.progress_bar} `{xp_percentage}%`"
        xp_info = f"Level **{user.level}**\n{user.xp}/{xp_required}\n"

        embed = discord.Embed(
            title="Tournament Statistics",
            color=target.color)
        username = target.name + "#" + target.discriminator
        embed.set_author(name=username)
        embed.set_thumbnail(url=target.avatar_url)

        embed.add_field(name="In-Game Name", value=ign_text)
        embed.add_field(name="Tournaments Joined", value=user.participations)
        embed.add_field(name="Tournaments Hosted", value=user.hosted)
        embed.add_field(name="Wins", value=user.wins)
        embed.add_field(name="Losses", value=losses)
        embed.add_field(name="Win Rate", value=win_rate)
        embed.add_field(name="Current Win Streak", value=user.streak)
        embed.add_field(name="Max Win Streak", value=user.max_streak)
        embed.add_field(name="Experience", value=xp_info + full_progress, inline=False)

        await ctx.send(embed=embed)
