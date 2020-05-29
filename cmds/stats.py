# Statistics Cog

# Importing Libraries
import discord

from discord.ext import commands

from classes.perms import allowed_channels, is_authorized
from classes.user import User
from classes.emote import Emote
from core import Log

STATS_LIST = ('participations', 'hosted', 'wins', 'losses', 'streak', 'streak_age', 'max_streak', 'xp', 'level')

class Stats(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client = client
        print(self.__class__.__name__ + " cog initialized!")

    async def _eval(self, ctx, cmd):
        try:
            try:
                result = eval(cmd)
            except SyntaxError:
                result = exec(cmd)

            return result
        except Exception as e:
            raise commands.BadArgument("Eval raised an exception: `" + str(e) + "`")

    @commands.command()
    @allowed_channels(["bot_cmds", "t_chat"])
    async def ping(self, ctx):
        msg = await ctx.send(":ping_pong: Calculating latency...")
        latency = round(self.client.latency, 4) * 1000
        raw_response_time = (
                msg.created_at - ctx.message.created_at).total_seconds()
        response_time = round(raw_response_time, 4) * 1000

        await msg.edit(
            content=f":link: Websocket Latency: `{latency}ms`\n:speech_balloon: Response Time: `{response_time}ms`")

    @commands.command(aliases=['statistics', 'status', 'stat', 'profile'])
    @allowed_channels(["bot_cmds"])
    async def stats(self, ctx, target: discord.Member = None):
        if target is None:
            target = ctx.author

        user = User.fetch_by_id(ctx, target.id)
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

    @commands.command(aliases=['ing'])
    @allowed_channels(["bot_cmds", "t_chat"], level=1, to=True, mech=True)
    async def ign(self, ctx, ign=None):

        if ign is None:
            await ctx.send("Please provide your Werewolf Online in-game name: `;ign example_name`")
            return

        user = User.fetch_by_id(ctx, ctx.author.id)
        old_ign = user.ign

        user.ign = ign
        self.client.get_cog("TOrganizer").cache_ign(ctx.author, ign)

        await ctx.send(f"{Emote.check} {ctx.author.mention}, your Werewolf Online IGN has been set to `{ign}`.")

        Log("IGN Set",
            description=f"{ctx.author.mention} has set their IGN to `{ign}`.",
            color=0x6a0dad,
            fields=[{'name': 'Previous IGN', 'value': old_ign}])

    @commands.command(aliases=['seting'])
    @is_authorized(level=1, to=True, mech=True)
    async def setign(self, ctx, member: discord.Member, ign):

        user = User.fetch_by_id(ctx, member.id)
        old_ign = user.ign

        user.ign = ign
        self.client.get_cog("TOrganizer").cache_ign(ctx.author, ign)

        await ctx.send(f"{Emote.check} {ctx.author.mention}, **{member.name}**'s IGN has been set to `{ign}`.")

        Log("IGN Set (Staff)",
            description=f"{ctx.author.mention} has set {member.mention}'s IGN to `{ign}`.",
            color=0x4a0dff,
            fields=[{'name': 'Previous IGN', 'value': old_ign}])

    @commands.command()
    @is_authorized(level=1, to=True, mech=True)
    async def add(self, ctx, stat, user: discord.Member, amount: int):
        if stat not in STATS_LIST:
            raise commands.BadArgument(f"The `{stat}` stat doesn't exist! Check your spelling and"
                                       " make sure everything is lowercase!")

        profile = User.fetch_by_id(ctx, user.id)
        current = getattr(profile, stat)
        setattr(profile, stat, current + amount)

        await ctx.send(f"{Emote.check} Added {str(amount)} {stat} to **{user.name}**.")

        Log(title=f"{stat.capitalize()} Added",
            description=f"{ctx.author.mention} added {str(amount)} {stat} to {user.mention}.",
            fields=[{"name": "Value", "value": f"{str(current)} -> {str(current + amount)}"}],
            color=discord.Color.dark_green())

    @commands.command(aliases=["stats-set"])
    @is_authorized(level=1, to=True, mech=True)
    async def _set(self, ctx, stat, user: discord.Member, amount: int):
        if stat not in STATS_LIST:
            raise commands.BadArgument(f"The `{stat}` stat doesn't exist! Check your spelling and"
                                       " make sure everything is lowercase!")

        profile = User.fetch_by_id(ctx, user.id)
        current = getattr(profile, stat)
        setattr(profile, stat, amount)

        await ctx.send(f"{Emote.check} Set **{user.name}**'s {stat} to {str(amount)}.")

        Log(title=f"{stat.capitalize()} Set",
            description=f"{ctx.author.mention} set {user.mention}'s {stat} to {str(amount)}.",
            fields=[{"name": "Value", "value": f"{str(current)} -> {str(amount)}"}],
            color=discord.Color.orange())
