# Tournament Organizer Cog

# Importing Libraries
from time import strftime
from dateutil import parser
from inspect import Parameter
from discord.ext import commands
from discord import Color, Embed, HTTPException
from asyncio import TimeoutError as Timeout
from classes.tournament import Tournament, Status
from classes.perms import is_authorized, allowed_channels, authorized
from classes.emote import Emote
from classes.channel import Channel
from classes.role import Role
from classes.user import User
from core import Log, ReadJSON, TimeUntil, ModifierCheck, SendFirstTournamentMessage, UpdatedEmbed


class TournamentJoinException(commands.CommandError):
    def __init__(self, msg):
        super().__init__(message=msg)


class ModifierUtils:  # Method class for modifier parsing
    @classmethod
    def convert_to_prize_type(self, type_):
        prizetypes = ['NonDividable', 'ForEach', 'NoClaim']
        if type_ in prizetypes:
            return type_
        raise commands.BadArgument(
            f"`{type_}` is not a valid prize type.")

    @classmethod
    async def convert_value(self, ctx, converter, value):
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
    async def create(self, ctx):
        embed = Embed(title="Player Checklist",
                      color=Color.dark_green())

        self.embed = embed
        self.msg = await ctx.send(embed=embed)
        self.client = ctx.bot
        self.emote_str = "123456789🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿"
        await self.msg.pin()
        return Checklist()

    async def update(self, ctx, tournament):
        participant_list = tournament.participants
        host = tournament.host
        p_count = len(participant_list)
        l_index = 0

        host_ign = (await User.from_id(ctx, host.id)).ign
        ign_list = [f"👑 {host.mention} - `{host_ign}`"]

        for i in range(p_count):
            participant = participant_list[i]
            if participant is False:  # Left User
                l_index += 1
                continue
            player_ign = (await User.from_id(ctx, participant.id)).ign
            try:
                emote = self.emote_str[i]
            except IndexError:  # Player count is over 35
                if i == 36:  # First time exceeding
                    await ctx.send("⚠️ The checklist is unavailable over 35 participants.")
                return
            if i < 9:
                emote += "⃣"
            ign_list.append(f"{emote} {participant.mention} - `{player_ign}`")

        try:  # No players tracked soft-fail
            await self.msg.add_reaction(emote)
        except UnboundLocalError:
            return

        reactions = (await ctx.channel.fetch_message(self.msg.id)).reactions
        for reaction in reactions:
            if not isinstance(reaction.emoji, str):
                continue
            emoji = reaction.emoji[0]
            if emoji not in self.emote_str:
                continue
            i = self.emote_str.index(emoji) + 1
            if i > p_count:
                continue

            async for user in reaction.users():
                if user != self.client.user and authorized(ctx, user=user, to=True) or Role(self.client).temp_host in user.roles:
                    i -= l_index
                    ign_list[i] = "~~" + ign_list[i] + "~~"

        text = ""
        for ign_item in ign_list:
            text += ign_item + "\n"
        self.embed.description = text
        await self.msg.edit(embed=self.embed)


class TOrganizer(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.tournament = Tournament()
        # self.tournaments = ReadJSON("tournaments.json")
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

        self.tournament.name = "Testing"
        self.tournament.roles = "Empty"

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
                parser.parse(value, dayfirst=True)
            except ValueError:
                raise commands.BadArgument(
                    f"`{value}` is not a valid time format. Refer to the pinned messages for a list of time formats.")

        old_value = getattr(self.tournament, attribute)
        setattr(self.tournament, attribute, value)

        if self.tournament.status >= 3:
            # Update Tournament Message TODO
            pass

        await ctx.send(f"{Emote.check} The `{attribute}` has been set to **{value}**.")

        fields = [{"name": "Old Value", "value": old_value},
                  {"name": "New Value", "value": value}]
        if old_value is None:
            del fields[0]

        Log("Value Updated",
            description=f"{ctx.author.mention} updated the `{attribute}` for **{self.tournament.name}**.",
            color=Color.teal(),
            fields=fields)

    @commands.command(aliases=['info'])
    @is_authorized(to=True)
    async def tinfo(self, ctx):
        tournament = self.tournament
        embed = Embed(title=tournament.name, color=Color.teal())

        for field in self.attr:
            value = getattr(tournament, field)
            embed.add_field(name=field.title(), value=value)

        await ctx.send("Here's how the tournament currently looks like:", embed=embed)

    @commands.command(aliases=['reset'])
    @is_authorized(to=True)
    async def treset(self, ctx):
        if self.tournament.status >= 2:
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
                missing.append("`"+attr+"`")
        if missing != []:
            items = " and ".join(item for item in missing)
            raise commands.BadArgument(
                f"You have not specified a {items} for the tournament.")

        embed = Embed(title=self.tournament.name, color=Color.orange())
        embed.set_author(name="Tournament Scheduled")

        for attr in self.attr:
            val = getattr(self.tournament, attr)
            if attr == 'time':
                time = parser.parse(val, dayfirst=True, ignoretz=True)
                val = strftime(f"%A %d %b %H:%M *UTC*", time.timetuple())
            elif attr == 'host':
                val = val.mention
            if attr not in ['name', 'roles'] and val is not None:
                embed.add_field(name=attr.title(), value=val)
        embed.set_footer(
            text=f"This tournament will take place in {TimeUntil(time)}!")

        await ctx.message.add_reaction(Emote.check)
        await self.channels.t_planned.send("Text", embed=embed)

        # Add stuff and Log
        Log("Tournament Planned",
            description=f"{ctx.author.mention} scheduled **{self.tournament.name}**.",
            color=Color.orange(), fields=[{"name": "Host", "value": self.tournament.host},
                                          {"name": "Time", "value": self.tournament.time}])
        self.tournament.status = Status.Scheduled
        # self.tournaments.append(self.tournament.todict()) TODO fix this
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

        req = ['name', 'host', 'roles']
        missing = []
        for attr in req:
            if getattr(self.tournament, attr) is None:
                missing.append("`"+attr+"`")
        if missing != []:
            items = " and ".join(item for item in missing)
            raise commands.BadArgument(
                f"You have not specified a {items} for the tournament.")

        if self.roles.temp_host not in self.tournament.host.roles:
            await self.tournament.host.add_roles(self.roles.temp_host)

        self.tournament.status = Status.Opened
        await ctx.message.add_reaction(Emote.check)
        Log("Tournament Started",
            description=f"{ctx.author.mention} started **{self.tournament.name}**.",
            color=Color.green())

        embed = UpdatedEmbed(self.tournament)

        try:
            await self.channels.t_channel.last_message.delete()
        except AttributeError:
            pass
        self.tournament.msg = await self.channels.t_channel.send("Text", embed=embed)
        await self.tournament.msg.add_reaction("\u2795")
        if ModifierCheck("SpectatorsAllowed", self.tournament.modifiers) is not False:
            await self.tournament.msg.add_reaction("📽️")

        self.checklist = await Checklist.create(ctx)

    @commands.command()
    @allowed_channels(["t_channel", "bot_cmds"])
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

        join_msg = f"{ctx.author.mention} joined. **{str(player_count + 1)}** players are now ready."
        if player_count == 0:  # First join, make singular
            i = join_msg[-35:].index("s are") + len(join_msg) - 35
            join_msg = join_msg[:i] + " is" + join_msg[i+5:]
        user = await User.from_id(ctx, ctx.author.id)
        if user.participations == 0:
            join_msg += "\nThis is the first tournament they are participating in. Welcome! 🎉"
            # await SendFirstTournamentMessage(ctx) TODO enable this after testing
        if user.ign is None:
            join_msg += "\nThis player does not have an IGN set yet."
        else:
            join_msg += f"\nIGN: `{user.ign}`"

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
        await self.checklist.update(ctx, self.tournament)

    @commands.command()
    @allowed_channels(["t_channel", "bot_cmds"])
    async def spectate(self, ctx):
        await self.CheckRequirements(ctx.author)
        if ModifierCheck("SpectatorsAllowed", self.tournament.modifiers) is False:
            raise TournamentJoinException(
                "spectators are not allowed for this tournament!")

        if ctx.author in self.tournament.spectators:
            raise TournamentJoinException("you are already a spectator!")

        spec_count = len(self.tournament.spectators)
        join_msg = f"{ctx.author.mention} joined the spectators. **{str(spec_count + 1)}** spectators are now watching the tournament."
        if spec_count == 0:  # First join, make singular
            i = join_msg[-35:].index("s are") + len(join_msg) - 35
            join_msg = join_msg[:i] + " is" + join_msg[i+5:]

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
            await ctx.send(f"{ctx.author.mention} left the tournament.")
            Log("Participant Left",
                description=f"{ctx.author.mention} left **{self.tournament.name}**.", color=Color.dark_gold())

            embed = UpdatedEmbed(self.tournament)
            await self.tournament.msg.edit(embed=embed)
            await self.checklist.update(ctx, self.tournament)

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
        for player in self.tournament.participants:
            user = await User.from_id(ctx, player.id)
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
        if self.tournament.status not in (3, 4):
            raise commands.BadArgument("The tournament has not started.")

        await ctx.send("Are you sure you want to cancel this tournament? `yes`/`no`")

        def check(m):
            return m.author == ctx.message.author and m.channel == ctx.message.channel

        try:
            msg = await self.client.wait_for('message', check=check, timeout=30)
        except Timeout:
            raise commands.BadArgument("Command cancelled.")

        if msg.content.lower() == "no":
            raise commands.BadArgument(
                "Alright, the tournament will not be cancelled.")
        if msg.content.lower() != "yes":
            raise commands.BadArgument(
                "Invalid choice. Please type the command again to retry.")

        cancel_msg = await ctx.send(":flag_white: Cancelling...")

        async def purge_role(role):
            for member in role.members:
                try:
                    await member.remove_roles(role)
                except HTTPException:
                    pass

        await purge_role(self.roles.participant)
        await purge_role(self.roles.temp_host)
        await purge_role(self.roles.spectator)

        try:
            await self.tournament.msg.delete()
        except HTTPException:
            pass
        # TODO No tournaments message

        try:
            await cancel_msg.edit(content=":flag_white: Tournament cancelled.")
        except HTTPException:
            pass

        Log("Tournament Cancelled",
            description=f"{ctx.author.mention} cancelled **{self.tournament.name}**.",
            color=Color.from_rgb(40,40,40))
        self.tournament = Tournament()
