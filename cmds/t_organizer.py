# Tournament Organizer Cog

# Importing Libraries
import asyncio
from inspect import Parameter
from time import strftime

from dateutil import parser
from datetime import datetime, timedelta
from discord import Color, Embed, HTTPException
from discord import Member, NotFound
from discord.ext import commands

from classes.channel import Channel
from classes.emote import Emote
from classes.perms import is_authorized, bot_cmds_only
from classes.role import Role
from classes.tournament import Tournament, Status
from classes.user import User
from core import Log, TimeUntil, ModifierCheck, UpdatedEmbed, SendFirstTournamentMessage, Tip


class TournamentJoinException(commands.CommandError):
    def __init__(self, msg):
        super().__init__(message=msg)


class ModifierUtils:  # Method class for modifier parsing
    @staticmethod
    def convert_to_prize_type(type_):
        prizetypes = ['NonDividable', 'ForEach', 'NoClaim']
        if type_ in prizetypes:
            return type_
        raise commands.BadArgument(
            f"`{type_}` is not a valid prize type.")

    @staticmethod
    async def convert_value(ctx, converter, value):
        try:
            v = await converter.convert(ctx, value)
        except AttributeError:
            try:
                v = converter(value)
            except ValueError:
                raise commands.BadArgument(
                    f"`{value}` is not a vaild value for this modifier.")
        return v


class Checklist:  # A class used for the IGN checklist
    @classmethod
    async def create(cls, ctx):
        checklist = cls()
        embed = Embed(title="Player Checklist",
                      color=Color.dark_green())

        checklist.embed = embed
        checklist.checked = {}
        checklist.msg = await Channel(ctx.bot).t_chat.send(embed=embed)
        checklist.client = ctx.bot
        checklist.emote_str = "123456789🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿"
        await checklist.msg.pin()
        return checklist

    async def uncheck_item(self, ctx, tournament, emoji):
        index = self.emote_str.index(emoji)
        self.checked[index] = False
        await self.update_text(ctx, tournament)

    async def check_item(self, ctx, tournament, emoji):
        index = self.emote_str.index(emoji)
        self.checked[index] = True
        await self.update_text(ctx, tournament)

    async def update_text(self, ctx, tournament):
        participant_list = tournament.participants
        host = tournament.host
        p_count = len(participant_list)
        l_index = 0

        host_ign = ign_cache[host.id]
        ign_list = [f"👑 {host.mention} - `{host_ign}`"]

        for i in range(p_count):
            participant = participant_list[i]
            if participant is False:  # Left User
                l_index += 1
                continue
            player_ign = ign_cache[participant.id]
            try:
                emote = self.emote_str[i]
            except IndexError:  # Player count is over 35
                if i == 36:  # First time exceeding
                    await ctx.send("⚠️ The checklist is unavailable over 35 participants.")
                return
            if i < 9:
                emote += "⃣"

            new_entry = f"{emote} {participant.mention} - `{player_ign}`"
            try:
                if self.checked[i] is True:
                    new_entry = "~~" + new_entry + "~~"
            except KeyError:
                self.checked[i] = False

            ign_list.append(new_entry)

        try:  # No players tracked soft-fail
            await self.msg.add_reaction(emote)
        except UnboundLocalError:
            return

        text = ""
        for ign_item in ign_list:
            text += ign_item + "\n"
        self.embed.description = text
        await self.msg.edit(embed=self.embed)


ign_cache = {}


class TOrganizer(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.tournament = Tournament()
        self.queue = Tournament.get_tournaments(client)
        self.attr = ['name', 'time', 'prize', 'host', 'roles', 'note']
        self.channels = Channel(client)
        self.roles = Role(client)
        self.checklist = None
        self.modifiers = [{'name': 'RequiredRole', 'value': commands.RoleConverter()},
                          {'name': 'MaxParticipants', 'value': int},
                          'SpectatorsAllowed',
                          {'name': 'PrizeType',
                           'value': ModifierUtils.convert_to_prize_type},
                          {'name': 'AutoGiveCoins', 'value': int},
                          {'name': 'AssistingTO', 'value': commands.MemberConverter()}]

        asyncio.create_task(self.update_reminders())

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

    def cache_ign(self, user, ign):
        if self.tournament.status not in (2, 3, 4): return

        ign_cache[user.id] = ign

    async def on_member_leave(self, member):
        if member in self.tournament.participants:
            self.tournament.remove_participant(member)
            await self.channels.t_chat.send(f":exclamation: {member.mention} left the server"
                                            " and has been removed from the tournament.")

    def increment_streak_age(self):
        User.custom_statement(self.client,
                              "UPDATE stats SET streak_age = streak_age + 1 WHERE streak_age IS NOT NULL")

    async def update_reminders(self):
        now = datetime.utcnow()
        tourneys = [tourney for tourney in self.queue if tourney.time - now < timedelta(days=1)]

        for tourney in tourneys:
            if tourney.reminder is not None:
                tourney.reminder.cancel()

            if not tourney.subscribed: continue

            coro = tourney.start_reminder(self.channels.bot_cmds)
            task = asyncio.create_task(coro)
            tourney.reminder = task

    @commands.command(aliases=['set'])
    @is_authorized(to=True)
    async def tset(self, ctx, attribute, *, value):
        if attribute not in self.attr:
            raise commands.BadArgument(
                f"`{attribute}` is not a valid tournament attribute.")
        if attribute == 'host':
            value = await commands.MemberConverter().convert(ctx, value)
        elif attribute == 'time':
            try:
                value = parser.parse(value, dayfirst=True)
            except ValueError:
                raise commands.BadArgument(
                    f"`{value}` is not a valid time format. Refer to the pinned messages for a list of time formats.")

        old_value = getattr(self.tournament, attribute)
        setattr(self.tournament, attribute, value)

        if self.tournament.status in (3, 4):
            embed = UpdatedEmbed(self.tournament)
            await self.tournament.msg.edit(embed=embed)

        await ctx.send(f"{Emote.check} The `{attribute}` has been set to **{value}**.")

        fields = [{"name": "Old Value", "value": old_value},
                  {"name": "New Value", "value": value}]
        if old_value is None:
            del fields[0]

        Log("Value Updated",
            description=f"{ctx.author.mention} updated the `{attribute}` for **{self.tournament.name}**.",
            color=Color.teal(),
            fields=fields)

    @commands.command()
    @is_authorized(to=True)
    async def t(self, ctx):
        tournament = self.tournament
        embed = Embed(title=tournament.name, color=Color.teal())

        for field in self.attr:
            value = getattr(tournament, field)
            embed.add_field(name=field.title(), value=value)

        if tournament.id is not None:
            embed.set_footer(text="Tournament ID: " + str(tournament.id))

        await ctx.send("Here's how the tournament currently looks like:", embed=embed)

    @commands.command(aliases=['reset'])
    @is_authorized(to=True)
    async def treset(self, ctx):
        if self.tournament.status in (2, 3, 4):
            raise commands.BadArgument(
                f"The tournament is ongoing and cannot be reset. Please try to use `;cancel` instead.")

        self.tournament = Tournament()
        await ctx.send(f"{Emote.check} The tournament has succesfully been reset.")

        Log("Tournament Reset",
            description=f"{ctx.author.mention} has reset the tournament to default values.",
            color=Color.dark_red())

    @commands.command(aliases=['plan'])
    @is_authorized(to=True)
    async def tplan(self, ctx):
        if self.tournament.status != Status.Pending:
            raise commands.BadArgument(
                f"The tournament cannot be scheduled at the moment.")

        req = ['name', 'host', 'time']
        missing = []
        for attr in req:
            if getattr(self.tournament, attr) is None:
                missing.append("`" + attr + "`")
        if missing:
            items = " and ".join(item for item in missing)
            raise commands.BadArgument(
                f"You have not specified a {items} for the tournament.")

        embed = Embed(title=self.tournament.name, color=Color.orange())
        embed.set_author(name="Tournament Scheduled")

        for attr in self.attr:
            val = getattr(self.tournament, attr)
            if attr == 'time':
                val = val.strftime("%A %d %b at %I:%M%p *GMT*")
            if attr == 'host':
                val = val.mention
            if attr not in ['name', 'roles'] and val is not None:
                embed.add_field(name=attr.title(), value=val)
        embed.set_footer(
            text=f"This tournament will take place in {TimeUntil(self.tournament.time)}!")

        await ctx.message.add_reaction(Emote.check)
        await self.channels.t_planned.send(f"New tournament scheduled! {self.roles.schedule.mention}",
                                           embed=embed)

        # Add stuff and Log
        Log("Tournament Planned",
            description=f"{ctx.author.mention} scheduled **{self.tournament.name}**.",
            color=Color.orange(), fields=[{"name": "Host", "value": self.tournament.host},
                                          {"name": "Time", "value": self.tournament.time}])
        self.tournament.status = Status.Scheduled
        self.tournament.save()
        await ctx.send("Tournament ID: " + str(self.tournament.id))
        if self.tournament not in self.queue:
            self.queue.append(self.tournament)
        self.tournament = Tournament()

    @commands.group(aliases=['modifiers', 'modifers', 'modifer'])
    @is_authorized(to=True)
    async def modifier(self, ctx):

        modifiers = self.modifiers

        if ctx.invoked_subcommand is not None:
            return

        # Display Modifiers Menu
        list_ = ""

        for mod in modifiers:
            try:
                list_ += mod['name'] + "\n"
            except TypeError:
                list_ += mod + "\n"

        applied = ""

        for mod in self.tournament.modifiers:
            try:
                applied += f"`{mod['name']}` = {mod['value']} \n"
            except TypeError:
                applied += f"`{mod}` \n"

        embed = Embed(title="Modifiers Menu", color=Color.teal())
        embed.add_field(name="Available Modifiers", value=list_, inline=True)
        if applied != "":
            embed.add_field(name="Active Modifiers",
                            value=applied, inline=True)

        await ctx.send(embed=embed)

    @modifier.command()
    @is_authorized(to=True)
    async def add(self, ctx, modifier, *, value=None):
        i = ModifierCheck(modifier, self.modifiers)

        if i is False:
            raise commands.BadArgument(
                f"Unknown modifier `{modifier}`.")

        if value is None and modifier not in self.modifiers:
            raise commands.errors.MissingRequiredArgument(
                Parameter('value', Parameter.KEYWORD_ONLY))

        if ModifierCheck(modifier, self.tournament.modifiers) is not False:
            raise commands.BadArgument(
                f"`{modifier}` has already been added to the tournament.")

        modifier = self.modifiers[i]
        fields = []

        if isinstance(modifier, dict):  # Value Settable Modifier
            modifier = modifier.copy()
            modifier['value'] = await ModifierUtils.convert_value(ctx, modifier['value'], value)
            fields.append({'name': "New Value", 'value': modifier['value']})
            await ctx.send(f"{Emote.check} `{modifier['name']}` was set to **{value}**.")
        else:
            await ctx.send(f"{Emote.check} `{modifier}` is now active for this tournament.")

        self.tournament.modifiers.append(modifier)
        if isinstance(modifier, dict):
            modifier = modifier['name']
        Log("Modifier Added",
            description=f"{ctx.author.mention} added the modifier `{modifier}` to **{self.tournament.name}**.",
            color=Color.dark_teal(),
            fields=fields)

    @modifier.command()
    @is_authorized(to=True)
    async def edit(self, ctx, modifier, *, value):
        i = ModifierCheck(modifier, self.tournament.modifiers)

        if i is False:
            raise commands.BadArgument(
                f"`{modifier}` is not active.")

        modifier = self.tournament.modifiers[i]
        if isinstance(modifier, str):
            raise commands.BadArgument(
                f"The value for `{modifier}` cannot be edited.")

        old_value = modifier['value']
        j = self.modifiers[ModifierCheck(modifier['name'], self.modifiers)]
        modifier['value'] = await ModifierUtils.convert_value(ctx, j['value'], value)

        if old_value == modifier['value']:
            await ctx.send("Nothing changed. Silly!")
            return

        await ctx.send(f"{Emote.check} The value for `{modifier['name']}` was changed to **{modifier['value']}**.")
        fields = [{'name': "Old Value", 'value': old_value},
                  {'name': "New Value", 'value': modifier['value']}]
        Log("Modifier Edited",
            description=f"{ctx.author.mention} changed the value of `{modifier['name']}` for **{self.tournament.name}**.",
            color=Color.dark_teal(),
            fields=fields)

    @modifier.command()
    @is_authorized(to=True)
    async def remove(self, ctx, modifier):
        i = ModifierCheck(modifier, self.tournament.modifiers)

        if i is False:
            raise commands.BadArgument(
                f"Modifier `{modifier}` is not active on this tournament.")

        old = self.tournament.modifiers[i]
        self.tournament.modifiers.pop(i)
        await ctx.send(f"{Emote.check} `{modifier}` has been removed.")
        fields = []
        if isinstance(old, dict):
            fields.append({'name': "Old Value", 'value': old['value']})
        Log("Modifier Removed",
            description=f"{ctx.author.mention} has removed `{modifier}` from **{self.tournament.name}**.",
            color=Color.dark_teal(),
            fields=fields)

    @commands.command(aliases=['tstart'])
    @is_authorized(to=True)
    async def start(self, ctx):
        if self.tournament.status >= 3:
            raise commands.BadArgument(
                "The tournament has already started.")

        req = ('name', 'host')
        missing = []
        for attr in req:
            if getattr(self.tournament, attr) is None:
                missing.append("`" + attr + "`")
        if missing:
            items = " and ".join(item for item in missing)
            raise commands.BadArgument(
                f"You have not specified a {items} for the tournament.")

        if self.tournament.time is None:
            self.tournament.time = datetime.utcnow()

        await self.tournament.host.add_roles(self.roles.temp_host)
        host_id = self.tournament.host.id
        ign_cache[host_id] = User.fetch_attr_by_id(host_id, "IGN")
        User.fetch_attr_by_id(host_id, "IGN")

        await ctx.message.add_reaction(Emote.check)
        Log("Tournament Started",
            description=f"{ctx.author.mention} started **{self.tournament.name}**.",
            color=Color.green())

        self.tournament.status = Status.Opened
        embed = UpdatedEmbed(self.tournament)

        try:
            msg = await self.channels.t_channel.fetch_message(self.channels.t_channel.last_message_id)
            await msg.delete()
        except (AttributeError, NotFound):
            pass

        self.tournament.msg = await self.channels.t_channel.send(f"Tournament **{self.tournament.name}** has started!"
                                                                 f" {self.roles.tournament.mention}", embed=embed)
        await self.tournament.msg.add_reaction(Emote.join)
        if ModifierCheck("SpectatorsAllowed", self.tournament.modifiers) is not False:
            await self.tournament.msg.add_reaction("📽️")

        self.checklist = await Checklist.create(ctx)

    @commands.command()
    @bot_cmds_only()
    async def join(self, ctx):
        await self.CheckRequirements(ctx.author)

        player_count = len(self.tournament.get_participants())
        mod_index = ModifierCheck("MaxParticipants", self.tournament.modifiers)

        if mod_index is not False:
            max_count = self.tournament.modifiers[mod_index]['value']
        else:
            max_count = 15  # Default
        if player_count >= max_count:
            raise TournamentJoinException(
                f"the tournament is full! The maximum number of participants is **{str(max_count)}**.")

        join_msg = f"{Emote.join} {ctx.author.mention} joined. **{str(player_count + 1)}** players are now ready."

        if player_count == 0:  # First join, make singular
            i = join_msg[-35:].index("s are") + len(join_msg) - 35
            join_msg = join_msg[:i] + " is" + join_msg[i + 5:]

        user = User.fetch_by_id(ctx, ctx.author.id)

        if user.participations == 0:
            join_msg += "\nThis is the first tournament they are participating in. Welcome! 🎉"
            await SendFirstTournamentMessage(ctx)
        if user.ign is None:
            join_msg += "\nThis player does not have an IGN set yet."
        else:
            join_msg += f"\nIGN: `{user.ign}`"

        ign_cache[ctx.author.id] = user.ign
        await ctx.author.add_roles(self.roles.participant)
        await ctx.author.remove_roles(self.roles.spectator)
        await self.channels.t_chat.send(join_msg)
        Log("Participant Joined", description=f"{ctx.author.mention} joined **{self.tournament.name}**.",
            color=Color.dark_green(), fields=[{'name': "Player Count", 'value': str(player_count + 1)}])
        self.tournament.add_participant(ctx.author)
        if ctx.author in self.tournament.spectators:
            self.tournament.spectators.remove(ctx.author)

        embed = UpdatedEmbed(self.tournament)
        await self.tournament.msg.edit(embed=embed)
        await self.checklist.update_text(ctx, self.tournament)

    @commands.command()
    @bot_cmds_only()
    async def spectate(self, ctx):
        await self.CheckRequirements(ctx.author)
        if ModifierCheck("SpectatorsAllowed", self.tournament.modifiers) is False:
            raise TournamentJoinException(
                "spectators are not allowed for this tournament!")

        if ctx.author in self.tournament.spectators:
            raise TournamentJoinException("you are already a spectator!")

        spec_count = len(self.tournament.spectators)
        join_msg = f"{Emote.join} {ctx.author.mention} joined the spectators. **{str(spec_count + 1)}** spectators are now watching the tournament."
        if spec_count == 0:  # First join, make singular
            i = join_msg[-35:].index("s are") + len(join_msg) - 35
            join_msg = join_msg[:i] + " is" + join_msg[i + 5:]

        await ctx.author.add_roles(self.roles.spectator)
        await self.channels.t_chat.send(join_msg)
        self.tournament.spectators.append(ctx.author)
        Log("Spectator Joined", description=f"{ctx.author.mention} joined **{self.tournament.name}**.",
            color=Color.dark_green(), fields=[{'name': "Spectator Count", 'value': str(spec_count + 1)}])

        embed = UpdatedEmbed(self.tournament)
        await self.tournament.msg.edit(embed=embed)

    async def CheckRequirements(self, user):
        if self.tournament.status != 3:
            raise TournamentJoinException("the tournament is not opened!")

        if user == self.tournament.host:
            raise TournamentJoinException(
                "you are the host! You cannot join your own tournament.")

        if user in self.tournament.participants:
            raise TournamentJoinException(
                f"you have already joined this tournament! Please move to {self.channels.t_chat.mention}.")

        if self.roles.t_banned in user.roles:
            raise TournamentJoinException(
                "you are banned from joining tournaments. You can check your ban status with `;profile`!")
        return

    @commands.command(aliases=["quit", "tleave"])
    async def leave(self, ctx):
        if ctx.author in self.tournament.participants:
            await ctx.author.remove_roles(self.roles.participant)
            if ctx.author in self.tournament.winners:
                self.tournament.winners.remove(ctx.author)
            self.tournament.remove_participant(ctx.author)
            await ctx.send(f"{Emote.leave} {ctx.author.mention} left the tournament.")
            Log("Participant Left",
                description=f"{ctx.author.mention} left **{self.tournament.name}**.", color=Color.dark_gold())

            embed = UpdatedEmbed(self.tournament)
            await self.tournament.msg.edit(embed=embed)
            await self.checklist.update_text(ctx, self.tournament)

        elif ctx.author in self.tournament.spectators:
            await ctx.author.remove_roles(self.roles.spectator)
            self.tournament.spectators.remove(ctx.author)
            await ctx.send(f"{ctx.author.mention} is no longer spectating the tournament.")
            Log("Spectator Left",
                description=f"{ctx.author.mention} left **{self.tournament.name}**.", color=Color.dark_gold())

            embed = UpdatedEmbed(self.tournament)
            await self.tournament.msg.edit(embed=embed)

        else:
            raise commands.BadArgument("You are not in a tournament!")

    @commands.command(aliases=['tkick'])
    @is_authorized(to=True)
    async def kick(self, ctx, user: Member):
        if user in self.tournament.participants:
            await user.remove_roles(self.roles.participant)
            if user in self.tournament.winners:
                self.tournament.winners.remove(user)
            self.tournament.remove_participant(user)
            await ctx.send(f"{Emote.leave} {user.mention} was kicked from the tournament.")
            Log("Participant Kicked",
                description=f"{user.mention} was kicked from **{self.tournament.name}** by {ctx.author.mention}.",
                color=Color.dark_gold())

            embed = UpdatedEmbed(self.tournament)
            await self.tournament.msg.edit(embed=embed)
            await self.checklist.update_text(ctx, self.tournament)

        elif user in self.tournament.spectators:
            await user.remove_roles(self.roles.spectator)
            self.tournament.spectators.remove(user)
            await ctx.send(f"{ctx.author.mention} is no longer spectating the tournament.")
            Log("Spectator Kicked",
                description=f"{ctx.author.mention} was kicked from **{self.tournament.name}** by {ctx.author.mention}.",
                color=Color.dark_gold())

            embed = UpdatedEmbed(self.tournament)
            await self.tournament.msg.edit(embed=embed)

        else:
            raise commands.BadArgument("This user is not in a tournament!")

    @commands.command(aliases=['tclose', 'tbegin', 'close'])
    @is_authorized(to=True)
    async def begin(self, ctx):
        if self.tournament.status != Status.Opened:
            raise commands.BadArgument(
                "The tournament cannot be closed right now.")
        if len(self.tournament.get_participants()) < 1:
            raise commands.BadArgument(
                "There are no participants in the tournament.")

        no_ign = ""
        for player in self.tournament.get_participants():
            user = User.fetch_by_id(ctx, player.id)
            if user.ign is None: no_ign += f"**{player.name}**\n"

        if no_ign != "":
            raise commands.BadArgument("Some players do not have an IGN set: \n" + no_ign)

        await ctx.send(f"{Emote.check} The tournament has been closed. Players can no longer join!")
        self.tournament.status = Status.Closed
        Log("Tournament Closed",
            description=f"{ctx.author.mention} closed **{self.tournament.name}**.", color=Color.dark_orange())

        await self.tournament.msg.clear_reactions()
        embed = UpdatedEmbed(self.tournament)
        await self.tournament.msg.edit(embed=embed)

    @commands.command(aliases=['tcancel'])
    @is_authorized(to=True)
    async def cancel(self, ctx):
        if self.tournament.status not in (1, 3, 4):
            raise commands.BadArgument("The tournament has not started.")

        await ctx.send(f"Are you sure you want to cancel **{self.tournament.name}**? `yes`/`no`")

        def check(m):
            return m.author == ctx.message.author and m.channel == ctx.message.channel

        try:
            msg = await self.client.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            raise commands.BadArgument("Command cancelled.")

        if msg.content.lower() == "no":
            raise commands.BadArgument(
                "Alright, the tournament will not be cancelled.")
        if msg.content.lower() != "yes":
            raise commands.BadArgument(
                "Invalid choice. Please type the command again to retry.")

        cancel_msg = await ctx.send(":flag_white: Cancelling...")

        try:
            self.queue.remove(self.tournament)
        except ValueError: pass

        if self.tournament.status in (3, 4):
            await self.cleanup()
            await self.client.get_command("nto").__call__(ctx)
        else:
            await self.update_reminders()

        try:
            await cancel_msg.edit(content=":flag_white: Tournament cancelled.")
        except HTTPException:
            pass

        Log("Tournament Cancelled",
            description=f"{ctx.author.mention} cancelled **{self.tournament.name}**.",
            color=Color.from_rgb(40, 40, 40))
        self.tournament.status = Status.Cancelled
        self.tournament.save()
        self.tournament = Tournament()

    async def cleanup(self):
        async def purge_role(role):
            for member in role.members:
                try:
                    await member.remove_roles(role)
                except HTTPException:
                    pass

        await purge_role(self.roles.participant)
        await purge_role(self.roles.temp_host)
        await purge_role(self.roles.spectator)

        for msg in await self.channels.t_chat.pins():
            await msg.unpin()

        try:
            await self.tournament.msg.delete()
        except HTTPException:
            pass

    @commands.command(aliases=['winner'])
    @is_authorized(to=True)
    async def w(self, ctx, users):
        if self.tournament.status != 4:
            raise commands.BadArgument("The tournament must have begun in order to add winners.")

        u_list = users.split(",")

        for user in u_list:
            user = await self._parse_player(ctx, user)

            if user not in self.tournament.participants and user != self.tournament.host:
                raise commands.BadArgument(f"**{user.name}** is not in the tournament.")

            if user in self.tournament.winners:
                raise commands.BadArgument(f"**{user.name}** is already a winner.")

            self.tournament.winners.append(user)
            await ctx.send(f":medal: Added **{user.name}** to the winners.")

            Log("Winner Added",
                description=f"{ctx.author.mention} added {user.mention} to the winners of **{self.tournament.name}**.",
                color=Color.from_rgb(200, 200, 0))

    @staticmethod
    async def _parse_player(ctx, user):
        try:
            result = await commands.MemberConverter().convert(ctx, user)
        except commands.BadArgument:
            try:
                index = list(ign_cache.values()).index(user)
                user_id = list(ign_cache.keys())[index]
                result = await commands.MemberConverter().convert(ctx, str(user_id))
            except ValueError:
                raise commands.BadArgument(f"Player `{user}` not found.")
        return result

    @commands.command(aliases=['rwinner'])
    @is_authorized(to=True)
    async def rw(self, ctx, users):
        if self.tournament.status != 4:
            raise commands.BadArgument("The tournament must have begun in order to add winners.")

        u_list = users.split(",")

        for user in u_list:
            user = await self._parse_player(ctx, user)

            if user not in self.tournament.participants and user != self.tournament.host:
                raise commands.BadArgument(f"**{user.name}** is not in the tournament.")

            if user not in self.tournament.winners:
                raise commands.BadArgument(f"**{user.name}** is not a winner.")

            self.tournament.winners.remove(user)
            await ctx.send(f":heavy_minus_sign: Removed **{user.name}** from the winners.")

            Log("Winner Removed",
                description=f"{ctx.author.mention} removed {user.mention} from the winners of **{self.tournament.name}**.",
                color=Color.from_rgb(200, 200, 0))

    @commands.command(aliases=['tend'])
    @is_authorized(to=True)
    async def end(self, ctx):
        if self.tournament.status != 4:
            raise commands.BadArgument(
                "The tournament must have begun before you can end it. If you are trying to cancel, use the `;cancel` "
                "command.")

        if not self.tournament.winners:
            await ctx.send("The winners list is empty! Are you sure you want to end this tournament? `yes`/`no`")

            def check(m):
                return m.author == ctx.message.author and m.channel == ctx.message.channel

            try:
                msg = await self.client.wait_for('message', check=check, timeout=30)
            except asyncio.TimeoutError:
                raise commands.BadArgument("Command cancelled.")

            if msg.content.lower() == "no":
                raise commands.BadArgument(
                    "Alright, I will not end the tournament yet.")
            if msg.content.lower() != "yes":
                raise commands.BadArgument(
                    "Invalid choice. Please type the command again to retry.")

        # OK to end from here

        await ctx.send(":checkered_flag: Thanks for playing! The tournament has ended!")

        await self.cleanup()

        id_list = [player.id for player in self.tournament.get_participants()]
        user_list = User.fetch_by_ids(ctx, id_list)

        for user in user_list:
            player = [x for x in self.tournament.get_participants() if x.id == user.id][0]
            summary, xp = self.tournament.calculate_xp_for(player, user.streak)

            user.participations += 1
            prev_level = user.level
            user.xp += xp
            new_level = user.level

            embed = Embed(title=self.tournament.name)

            if player in self.tournament.winners:
                embed.color = Color.from_rgb(200, 200, 0)
                embed.description = "\n**You won!** :tada:"

                user.wins += 1
                user.streak += 1
                user.streak_age = 0
                embed.description += f"\nYou're now on a **{user.streak}** win streak!"

                if user.streak > user.max_streak:
                    embed.description += "\nYou have beaten your max win streak! Congratulations!"
                    user.max_streak = user.streak

                elif user.streak == user.max_streak:
                    embed.description += "\nYou are tied with your max win streak!"

                else:
                    embed.description += f"\nYou're on your way to beat your max win streak of **{user.max_streak}**!"

            else:
                if user.streak != 0:
                    embed.description = f"\n **You lost!** :frowning:\nYou lost your win streak of {user.streak}."
                else:
                    embed.description = "\n **You lost!** :frowning:"
                
                user.streak = 0
                user.streak_age = None
                embed.color = Color.red()

            level_info = self._format_level_info(user)

            if new_level > prev_level:
                level_info += f"\n\nYou leveled up to level **{user.level}**! :partying_face:"

            embed.add_field(name="Experience", value=summary + "\n\n" + level_info)
            embed.set_footer(text="TIP: " + Tip())
            embed.set_author(name="Results")

            try:
                await player.send(embed=embed)
            except HTTPException as e:
                if e.status == 403:  # Forbidden
                    await ctx.send(f"{player.mention} has direct messages disabled,"
                                   " so I can't send them their results.")

        host = User.fetch_by_id(ctx, self.tournament.host.id)
        host.hosted += 1

        prev_level = host.level
        host.xp += 150  # Hosting XP
        new_level = host.level

        level_info = self._format_level_info(host)

        if new_level > prev_level:
            level_info += f"\n\nYou leveled up to level **{host.level}**! :partying_face:"

        desc = "You have recieved `150xp` for hosting this tournament!\n\n" + level_info
        embed = Embed(title="Thank you for hosting " + self.tournament.name + "!",
                      description=desc,
                      color=Color.green())

        try:
            await self.tournament.host.send(embed=embed)
        except HTTPException as e:
            if e.status == 403:  # Forbidden
                await ctx.send(f"{self.tournament.host.mention} has direct messages disabled,"
                               " so I can't send them their results.")
        except AttributeError:
            pass  # The bot user was the host so it cannot DM itself

        await self.client.get_command("nto").__call__(ctx)
        await self.channels.t_logs.send(embed=self.tournament.log_embed())

        self.tournament.status = Status.Ended
        self.tournament.save()
        try:
            self.queue.remove(self.tournament)
        except ValueError:
            pass
        self.tournament = Tournament()

    @staticmethod
    def _format_level_info(user):
        xp_required = user.level * 100
        xp_percentage = int(user.xp / xp_required * 100)
        full_progress = f"{user.progress_bar} `{xp_percentage}%`"
        xp_info = f"Level **{user.level}**\n{user.xp}/{xp_required}\n"
        return xp_info + full_progress

    @commands.command(aliases=["info"])
    @bot_cmds_only()
    async def tinfo(self, ctx, *, t_id=None):
        result = self.search_tournament(t_id)

        embed = Embed(title=result.name,
                      color=Color.dark_green())

        try:
            embed.description = f"Hosted by {result.host.mention}"
        except AttributeError:
            embed.description = "The host of this tournament left the server!"

        embed.set_footer(text="Tournament ID: " + str(result.id))

        if result.time is not None:
            countdown = ""
            if result.time > datetime.utcnow():
                try:
                    time_left = TimeUntil(result.time)
                    countdown = f"\nStarting in **{time_left}**"
                except ValueError:
                    pass

            embed.add_field(name="Time", value=strftime(f"%A %d %b %H:%M *GMT*", result.time.timetuple()) + countdown)
        else:
            embed.add_field(name="Time", value="Unknown")

        embed.add_field(name="Prize", value=result.prize)
        embed.add_field(name="Status", value=Status.KEYS[result.status])
        embed.add_field(name="Roles", value=result.roles)
        embed.add_field(name="Note", value=result.note)

        await ctx.send(embed=embed)

    def search_tournament(self, t_id):
        if t_id is None:
            raise commands.BadArgument("Please specify the name or ID of the tournament you want to search for!")
        try:
            int_id = int(t_id)
        except ValueError:
            int_id = None

        for tournament in self.queue:
            if isinstance(int_id, int) and tournament.id == int_id:
                return tournament

            if tournament.name == t_id:
                return tournament

        result = Tournament.get_tournament_by_id(self.client, t_id)

        if result is None:
            result = Tournament.get_tournament_by_name(self.client, t_id)

            if result is None:
                raise commands.BadArgument("Tournament not found! If you searched by name, check your spelling"
                                               " and capitialization!")

        return result

    @commands.command(aliases=["load"])
    @is_authorized(to=True)
    async def tload(self, ctx, *, t_id = None):
        if self.tournament.status in (2, 3, 4):
            raise commands.BadArgument(
                f"The tournament is ongoing and cannot be reset. Please try to use `;cancel` instead.")

        tournament = self.search_tournament(t_id)
        self.tournament = tournament
        await ctx.send(f"{Emote.check} Loaded **{tournament.name}**.")

    @commands.command(aliases=["save"])
    @is_authorized(to=True)
    async def tsave(self, ctx):
        req = ('name', 'host', 'time')
        missing = []
        for attr in req:
            if getattr(self.tournament, attr) is None:
                missing.append("`" + attr + "`")
        if missing:
            items = " and ".join(item for item in missing)
            raise commands.BadArgument(
                f"You have not specified a {items} for the tournament.")

        self.tournament.save()

        if self.tournament not in self.queue:
            self.queue.append(self.tournament)

        await ctx.send(f"{Emote.check} Saved **{self.tournament.name}**.\nTournament ID: {self.tournament.id}")
        self.tournament = Tournament()

    @commands.command()
    @is_authorized(to=True)
    async def nto(self, ctx):
        embed = Embed(title="The tournament is not open yet!",
                      description=f"Type `;upcoming` in {self.channels.bot_cmds.mention} to know"
                      " when the next tournament will happen!",
                      timestamp=datetime.utcnow(),
                      color=Color.red())
        embed.set_footer(text="Last tournament ended: ")
        await self.channels.t_channel.send(embed=embed)

    @commands.command(aliases=["reminder"])
    @bot_cmds_only()
    async def remindme(self, ctx, *, t_id = None):
        tourney = self.search_tournament(t_id)

        if tourney.status != Status.Scheduled:
            raise commands.BadArgument("This tournament is not scheduled, I don't know when it will start!")

        if ctx.author not in tourney.subscribed:
            # Subscribe
            if tourney.subscribed:
                Tournament.custom_statement(self.client,
                    "UPDATE tournaments SET subscribed_id = subscribed_id || "
                    f"\",{str(ctx.author.id)}\" WHERE ID={tourney.id}")

            else:
                Tournament.custom_statement(self.client,
                    f"UPDATE tournaments SET subscribed_id = \"{str(ctx.author.id)}\" WHERE ID={tourney.id}")

            tourney.subscribed.append(ctx.author)
            await self.update_reminders()
            await ctx.send(f"{Emote.check} {ctx.author.mention}, you will be reminded"
                           f" 10 minutes before **{tourney.name}** starts.")
            return

        # Unsubscribe
        Tournament.custom_statement(self.client,
            "UPDATE tournaments SET subscribed_id="
            f"replace(subscribed_id,\"{ctx.author.id}\",\"\")"
            f" WHERE ID={tourney.id}"
        )
        tourney.subscribed.remove(ctx.author)
        await self.update_reminders()
        await ctx.send(f"{Emote.check} {ctx.author.mention}, you will no longer be reminded"
                       f" when **{tourney.name}** starts.")
