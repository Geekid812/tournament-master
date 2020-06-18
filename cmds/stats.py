# Statistics Cog

# Importing Libraries
import discord
import time

from discord.ext import commands

from classes.perms import allowed_channels, is_authorized
from classes.user import User
from classes.tournament import Tournament
from classes.role import Role
from classes.emote import Emote
from core import Log, ReadJSON, TimeUntil

STATS_LIST = ('participations', 'hosted', 'wins', 'losses', 'streak', 'streak_age', 'max_streak', 'xp', 'level')

config = ReadJSON("config.json")


class Stats(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client = client
        self.roles = Role(self.client)
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

    @commands.command()
    @allowed_channels(["bot_cmds"])
    async def help(self, ctx, sub=None):
        if sub is None:
            embed = discord.Embed(title=f"Command Help", color=discord.Color.dark_green())
            embed.set_thumbnail(url=ctx.guild.icon_url)

            embed.add_field(
                inline=False,
                name="Tournaments",
                value=(
                    "`;ign <ign>` Set your Werewolf Online in-game name to be able to join tournaments!"
                    "\n`;upcoming` Lists all the tournaments that will start soon!"
                    "\n`;join` Join an open tournament."
                    "\n`;spectate` Spectate an open tournament (If spectating is enabled)."
                    "\n`;leave` Leave a tournament (You will not recieve any participation rewards)."
                    "\n~~`;create` Create your own tournaments!~~ *This feature is being reworked!*"
                )
            )

            embed.add_field(
                inline=False,
                name="Statistics",
                value=(
                    "`;ping` Check the bot's latency."
                    "\n`;stats <member>` Display your/another member's tournament statistics."
                    "\n`;leaderboard <board>` Check your leaderboard position and view global rankings!"
                )
            )

            embed.add_field(
                inline=False,
                name="Games",
                value=(
                    "`;gnk` (aka Geek, Nou, King) A game similar to rock, paper, scissors but named after the members"
                    " of this server!"
                )
            )

            await ctx.send(embed=embed)

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

    @commands.command(aliases=["stats-add"])
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

    @commands.command(aliases=["stats-remove"])
    @is_authorized(level=1, to=True, mech=True)
    async def remove(self, ctx, stat, user: discord.Member, amount: int):
        if stat not in STATS_LIST:
            raise commands.BadArgument(f"The `{stat}` stat doesn't exist! Check your spelling and"
                                       " make sure everything is lowercase!")

        profile = User.fetch_by_id(ctx, user.id)
        current = getattr(profile, stat)
        setattr(profile, stat, current - amount)

        await ctx.send(f"{Emote.check} Removed {str(amount)} {stat} from **{user.name}**.")

        Log(title=f"{stat.capitalize()} Removed",
            description=f"{ctx.author.mention} removed {str(amount)} {stat} from {user.mention}.",
            fields=[{"name": "Value", "value": f"{str(current)} -> {str(current - amount)}"}],
            color=discord.Color.dark_red())

    @commands.command(aliases=["lb", "top"])
    @allowed_channels(["bot_cmds"])
    async def leaderboard(self, ctx, board=None, page=1):
        boards = {"wins": "wins", "win": "wins", "levels": "level", "xp": "level", "level": "level",
                  "skill": "skill", "sp": "skill", "bal": "balance", "balance": "balance",
                  "coins": "balance", "money": "balance"}

        colors = {"wins": 0xffff00, "level": discord.Color.green()}

        if board is None:
            embed = discord.Embed(title="Your Leaderboard Positions", color=ctx.author.color)
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/575627727013412891/721700942336229397/Trophy.png")

            user = User.fetch_by_id(ctx, ctx.author.id)
            win_pos, win_total = user.fetch_top_pos_by_attr("wins")
            level_pos, level_total = user.fetch_top_pos_by_attr("level")

            if win_pos:
                text = f"**Wins:** #{win_pos} out of {win_total} ({user.wins} wins)"
            else:
                text = "**Wins:** *Unranked*"

            if level_pos:
                text += f"\n\n**Levels:** #{level_pos} out of {level_total} (Level {user.level}, {user.xp} xp)"
            else:
                text += "\n\n**Levels:** *Unranked*"

            embed.description = text
            embed.set_footer(text="Type \";leaderboard <board>\" to view a specific leaderboard!")
            await ctx.send(embed=embed)
            return

        try:
            int_page = int(page)
        except ValueError:
            raise commands.BadArgument(f"`{page}` is not a valid page number!")

        if int_page <= 0: page = 1
        attr = boards[board.lower()]
        start = (page - 1) * 10

        if board.lower() not in boards.keys():
            raise commands.BadArgument(f"The `{board}` leaderboard doesn't exist!\nTry looking at one of these"
                                       "leaderboards: `wins` or `levels`")

        top, total = User.fetch_top_by_attr(attr, start=start)
        max_pages = total // 10 + 1
        if page > max_pages: page = max_pages
        embed = discord.Embed(title=f"{attr.capitalize()} Leaderboard (Page {page} of {str(max_pages)})")
        embed.color = colors[attr]

        text = ""
        position = (page - 1) * 10 + 1
        for user in top:
            member = ctx.bot.get_guild(config['guild_id']).get_member(user.id)

            if member is None:
                mention = user.username
            else:
                mention = member.mention

            text += f"\n[**{position}**] {mention} - "

            if attr == "wins":
                text += f"**{user.wins}** wins"

            if attr == "level":
                text += f"Level **{user.level}**, {user.xp} xp"

            position += 1

        user = User.fetch_by_id(ctx, ctx.author.id)
        pos, total = user.fetch_top_pos_by_attr(attr)
        text += f"\n\n__Your rank:__\n **#{str(pos)}** out of {str(total)} players"

        embed.description = text

        await ctx.send(embed=embed)

    @commands.command()
    @is_authorized(1, to=True, mech=True)
    async def activity(self, ctx):
        embed = discord.Embed(title="TO Activity Check", color=discord.Color.green())
        text = ""

        for user in self.roles.t_organizer.members:
            if user == self.client.user: return

            latest = Tournament.custom_statement(self.client, f"SELECT * FROM tournaments WHERE host_id={user.id}"
                                                              " AND status=5 ORDER BY timestamp DESC")

            try:
                td_str = TimeUntil(latest[0].time) + f" ({latest[0].name})"
            except IndexError:
                td_str = "No results found!"

            text += f"{user.mention} - {td_str}\n"

        embed.description = text
        await ctx.send(embed=embed)

    @commands.command()
    @allowed_channels(["bot_cmds"])
    async def upcoming(self, ctx):
        embed = discord.Embed(title="Upcoming Tournaments", color=discord.Color.green())
        text = ""
        now = round(time.time())

        upcoming = Tournament.custom_statement(self.client, f"SELECT * FROM tournaments WHERE timestamp>{now}"
                                                            " AND status=1 ORDER BY timestamp DESC")
        text = ""

        if upcoming:
            for tourney in upcoming:
                text += f"**{tourney.name}** (Hosted by {tourney.host.mention}) - In {TimeUntil(tourney.time)}\n"
        else:
            text = "There are no upcoming tournaments! :("

        embed.description = text
        await ctx.send(embed=embed)
