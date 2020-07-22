# Database API

# User Object

import sqlite3
import math
import time
from datetime import datetime, timedelta
from discord import Embed, Color, utils
from core import ModifierCheck
from classes.emote import Emote
from core import ReadJSON
from asyncio import CancelledError

conn = sqlite3.connect("data/database.db", isolation_level=None)

config = ReadJSON("config.json")


def adapt_datetime(ts):
    return time.mktime(ts.timetuple())


sqlite3.register_adapter(datetime, adapt_datetime)


class User:
    @classmethod
    def _create_instance_from_raw(cls, raw):
        new_instance = cls()
        attributes = [desc_item[0] for desc_item in raw.description]
        for i in range(len(attributes)):
            setattr(new_instance, "_" + attributes[i], raw[i])

        return new_instance

    @classmethod
    def fetch_by_id(cls, ctx, user_id):
        user_id = str(user_id)
        cursor = conn.execute(
            "SELECT * FROM stats WHERE ID=?", (user_id,)).fetchone()
        member = ctx.bot.get_guild(config['guild_id']).get_member(int(user_id))
        username = f"{member.name}#{member.discriminator}"

        if cursor is None:  # New User
            conn.execute(
                "INSERT INTO stats (ID, username) VALUES (?,?)", (user_id, username))
            cursor = conn.execute(
                "SELECT * FROM stats WHERE ID=?", (user_id,)).fetchone()

        user_class = cls._create_instance_from_raw(cursor)

        # Always update username
        if user_class.username != username: user_class.username = username

        return user_class

    @classmethod
    def fetch_by_ids(cls, ctx, user_ids: list):
        ids = tuple(user_ids)
        result = []

        # if len(ids) == 1:
        #     ids = str(ids)[:-2] + ")"
        users = conn.execute(f"SELECT * FROM stats WHERE ID IN ?", (ids, )).fetchall()

        for user in users:
            uid = user[0]
            user_ids.remove(uid)

            member = ctx.bot.get_guild(config['guild_id']).get_member(int(uid))
            username = f"{member.name}#{member.discriminator}"

            new_user = cls._create_instance_from_raw(user)

            # Always update username
            if new_user.username != username: new_user.username = username

            result.append(new_user)

        for user in user_ids:  # New users
            member = ctx.bot.get_guild(config['guild_id']).get_member(user)
            username = f"{member.name}#{member.discriminator}"

            conn.execute(
                "INSERT INTO stats (ID, username) VALUES (?,?)", (user, username))

            user = conn.execute(
                "SELECT * FROM stats WHERE ID=?", (user,)).fetchone()

            new_user = cls._create_instance_from_raw(user)

            result.append(new_user)
        return result

    @classmethod
    def fetch_attr_by_id(cls, user_id, attr):
        user_id = str(user_id)

        value = conn.execute(
            f"SELECT {attr} FROM stats WHERE ID={user_id}").fetchone()

        if value is None:
            # Return default value

            if attr == "level":  # Default value: 1
                value = 1

            elif attr in ["participations", "wins", "hosted", "xp", "streak", "max_streak"]:  # Default value: 0
                value = 0

            # The rest should have None as default values
            return value

        else:
            return value[0]

    @classmethod
    def fetch_top_by_attr(cls, attr, start=0):
        if attr == "level": attr = "level DESC, xp"

        value = conn.execute(
            f"SELECT * FROM stats ORDER BY {attr} DESC").fetchall()
        total = len(value)
        if start > total: start = total // 10 * 10

        result = []
        amount = 10
        if total - start < 10: amount = total

        for item in value[start:amount + start]:
            new_user = cls._create_instance_from_raw(item)
            result.append(new_user)

        return result, total

    def fetch_top_pos_by_attr(self, attr):
        user_id = self.id
        if attr == "level": attr = "level DESC, xp"

        value = conn.execute(
            f"SELECT * FROM stats ORDER BY {attr} DESC").fetchall()
        total = len(value)

        ids = [item[0] for item in value]

        if user_id not in ids:
            return 0

        return ids.index(user_id) + 1, total

    @classmethod
    def custom_statement(cls, client, statement):
        response = conn.execute(statement).fetchall()
        out = []

        for item in response:
            if item is not None:
                instance = cls._create_instance_from_raw(client, item)
                out.append(instance)
        return out

    @property
    def id(self):
        return self._ID

    @id.setter
    def id(self, value: int):
        self._ID = value
        conn.execute("UPDATE stats SET ID=? WHERE ID=?", (value, self.id))

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value: str):
        self._username = value
        conn.execute("UPDATE stats SET username=? WHERE ID=?",
                       (value, self.id))

    @property
    def ign(self):
        return self._IGN

    @ign.setter
    def ign(self, value: str):
        self._IGN = value
        conn.execute("UPDATE stats SET IGN=? WHERE ID=?",
                       (value, self.id))

    @property
    def participations(self):
        return self._participations

    @participations.setter
    def participations(self, value: int):
        self._participations = value
        conn.execute(
            "UPDATE stats SET participations=? WHERE ID=?", (value, self.id))

    @property
    def wins(self):
        return self._wins

    @wins.setter
    def wins(self, value: int):
        self._wins = value
        conn.execute("UPDATE stats SET wins=? WHERE ID=?", (value, self.id))

    @property
    def hosted(self):
        return self._hosted

    @hosted.setter
    def hosted(self, value: int):
        self._hosted = value
        conn.execute("UPDATE stats SET hosted=? WHERE ID=?",
                       (value, self.id))

    @property
    def streak(self):
        return self._streak

    @streak.setter
    def streak(self, value: int):
        self._streak = value
        conn.execute("UPDATE stats SET streak=? WHERE ID=?",
                       (value, self.id))

    @property
    def streak_age(self):
        return self._streak_age

    @streak_age.setter
    def streak_age(self, value=None):
        if value is not None:
            value = int(value)
        self._streak_age = value
        conn.execute(
            "UPDATE stats SET streak_age=? WHERE ID=?", (value, self.id))

    @property
    def max_streak(self):
        return self._max_streak

    @max_streak.setter
    def max_streak(self, value: int):
        self._max_streak = value
        conn.execute(
            "UPDATE stats SET max_streak=? WHERE ID=?", (value, self.id))

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value: int):
        self._level = value
        conn.execute("UPDATE stats SET level=? WHERE ID=?", (value, self.id))

    @property
    def xp(self):
        return self._xp

    @xp.setter
    def xp(self, value: int):
        while value >= self.level * 100:  # New level reached
            value -= self.level * 100
            self.level += 1

        self._xp = value
        conn.execute("UPDATE stats SET xp=? WHERE ID=?", (value, self.id))

    @property
    def progress_bar(self):
        xp_required = self.level * 100
        box_completed = math.floor(self.xp / xp_required * 10)
        box_missing = 10 - box_completed
        bar = ""

        for i in range(box_completed):
            bar += ":blue_square:"

        for i in range(box_missing):
            bar += ":white_large_square:"

        return bar


class Status:
    Pending = 0
    Scheduled = 1
    PurchasableEntry = 2
    Opened = 3
    Closed = 4
    Ended = 5
    Cancelled = 6

    KEYS = {0: "Pending", 1: "Scheduled", 2: "PurchasableEntry", 3: "Opened", 4: "Closed", 5: "Ended",
            6: "Cancelled"}


class Tournament:
    def __init__(self):
        self.id = None
        self.msg = None
        self.name = None
        self.time = None
        self.prize = None
        self.status = Status.Pending
        self.host = None
        self.roles = None
        self.note = None
        self.participants = []
        self.spectators = []
        self.winners = []
        self.modifiers = []
        self.reminder = None
        self.subscribed = []

    def todict(self):
        dict_ = {}
        for attr in dir(self):
            if not attr.startswith("_"):
                dict_[attr] = getattr(self, attr)
        return dict_

    def embed_message(self):
        embed = Embed()  # This acts as the list of fields
        # Tournament Info
        for attr in ['host', 'prize', 'roles', 'note']:
            value = getattr(self, attr)
            if attr is not None and value is not None:
                if attr == 'host':
                    value = value.mention
                embed.add_field(name=attr.title(),
                                value=value,
                                inline=True)

        # Participant List
        p_list = ""
        player_list = self.get_participants()
        for user in player_list:
            p_list += user.mention + "\n"
        if p_list == "":
            p_list = "This seems empty..."

        if ModifierCheck('SpectatorsAllowed', self.modifiers) is not False:
            spectators_count = len(self.spectators)
            if spectators_count > 0:
                p_list += f"\n**{spectators_count}** player is also spectating this tournament."
                if spectators_count >= 2:  # Make plural
                    sindex = p_list.find(" is")
                    p_list = p_list[:sindex] + "s are" + p_list[sindex + 5:]

        participants_count = str(len(player_list))
        mindex = ModifierCheck('MaxParticipants', self.modifiers)
        if mindex is not False:
            title = f"Participants ({participants_count}/{self.modifiers[mindex]['value']})"
        else:
            title = f"Participants ({participants_count}/15)"
        embed.add_field(name=title, value=p_list, inline=False)

        # Tournament Modifiers and Joins
        if self.status == Status.Opened:
            embed.add_field(name=f"You can join the tournament by adding a {Emote.join} reaction to this message.",
                            value=f"You can also type `;join` in <#553886807373381635> to enter the game.",
                            inline=False)

            index = ModifierCheck('RequiredRole', self.modifiers)
            if index is not False:
                embed.add_field(name="Required role to join",
                                value=f"You must have the {self.modifiers[index]['value'].mention} role in order to join this tournament!",
                                inline=False)

            if ModifierCheck('SpectatorsAllowed', self.modifiers) is not False:
                embed.add_field(name="Spectators can enter this tournament",
                                value="You can react with the 📽️ emoji or type `;spectate` to join as a spectator!",
                                inline=False)

        else:
            embed.add_field(name="This tournament has started a few minutes ago",
                            value="You can no longer join this game!",
                            inline=False)

        return embed

    def log_embed(self):
        embed = Embed(title=self.name, description=f"Hosted by {self.host.mention}", color=Color.blue(),
                      timestamp=datetime.utcnow())
        winners = self.winners
        losers = [player for player in self.get_participants() if player not in self.winners]
        total = len(self.get_participants())

        text = ""
        for winner in winners:
            text += f":crown: {winner.mention}\n"

        for loser in losers:
            text += f"{loser.mention}\n"

        embed.add_field(name=str(total) + " participants", value=text)
        embed.set_footer(text="Tournament ended at: ")

        return embed

    def add_participant(self, user):
        if False in self.participants:
            index = self.participants.index(False)
            self.participants[index] = user
        else:
            self.participants.append(user)

    def remove_participant(self, user):
        index = self.participants.index(user)
        self.participants[index] = False

    def get_participants(self):
        participants = []
        for user in self.participants:
            if user is not False:
                participants.append(user)
        return participants

    def calculate_xp_for(self, player, streak):
        '''
        Participation: 50xp
        Winner: 100xp
        Solo win: 50xp
        Win streak: 25xp * streak
        Full tournament: 25xp
        '''
        xp = 50  # Default for participation
        summary = "Participation: `50xp`"

        if player in self.winners:
            xp += 100
            summary += "\nWinner: `100xp`"

            if len(self.winners) == 1:
                xp += 50
                summary += "\nSolo Win: `50xp`"

            if streak >= 2:
                add = streak * 25
                xp += add
                summary += f"\n{streak}x Win Streak: `{add}xp`"

        player_count = len(self.participants)
        mindex = ModifierCheck('MaxParticipants', self.modifiers)

        if mindex is not False:
            max_players = self.modifiers[mindex]['value']
        else:
            max_players = 15

        if player_count == max_players:
            xp += 25
            summary += "\nFull Tournament: `25xp`"

        summary += f"\n\n**Total:** `{xp}xp`"

        return summary, xp

    def save(self):
        attrs = {}
        for attr in dir(self):
            if not attr.startswith("_") and not callable(attr):
                attrs[attr] = getattr(self, attr)

        attrs['host_id'] = attrs['host'].id
        attrs['timestamp'] = attrs['time'].timestamp()

        order = ('name', 'host_id', 'prize', 'timestamp', 'status', 'roles', 'note')
        attrlist = []

        for attr in order:
            attrlist.append(attrs[attr])

        tourney = conn.execute(
            "SELECT * FROM tournaments WHERE ID=?", (self.id,)).fetchone()

        if tourney is None:
            conn.execute(
                "INSERT INTO tournaments(name, host_id, prize, timestamp, status, roles, note) VALUES (?,?,?,?,?,?,?)",
                attrlist)
            tourney = conn.execute(
                "SELECT ID FROM tournaments ORDER BY ID DESC").fetchone()
            self.id = tourney[0]

        else:
            cmd = "UPDATE tournaments SET "
            update = []

            for i in range(len(attrlist)):

                if attrlist[i] != tourney[i + 1]:
                    cmd += order[i] + "=?, "
                    update.append(attrlist[i])

            cmd = cmd[:-2] + " WHERE ID=?"
            update.append(self.id)

            conn.execute(cmd, update)

    async def start_reminder(self, destination):
        try:
            print("Starting reminder!")
            ten_mins_before = self.time - timedelta(minutes=10)
            await utils.sleep_until(ten_mins_before)
            mentions = ""

            for player in self.subscribed:
                mentions += player.mention + " "

            embed = Embed(title="Reminder",
                          description=f"**{self.name}** will start in 10 minutes!",
                          color=Color.teal())

            await destination.send(mentions, embed=embed)
        except CancelledError:
            pass

    @classmethod
    def _create_instance_from_raw(cls, client, raw):
        guild = client.get_guild(config['guild_id'])
        new_instance = cls()
        attributes = [description[0] for description in raw.description]

        for i in range(len(attributes)):
            name = attributes[i].lower()
            value = raw[i]

            if name == 'host_id':
                name = 'host'
                value = guild.get_member(value)

            elif name == 'timestamp':
                name = 'time'
                try:
                    value = datetime.fromtimestamp(value)
                except TypeError:
                    value = None

            elif name == 'subscribed_id':
                if value is None: continue
                player_list = []
                name = 'subscribed'

                for player_id in value.split(","):
                    if player_id == "": continue
                    member = guild.get_member(int(player_id))
                    if member is None: continue

                    player_list.append(member)

                value = player_list

            setattr(new_instance, name, value)

        return new_instance

    @classmethod
    def get_tournaments(cls, client):
        now = datetime.now().timestamp()
        tourney_list = []

        response = conn.execute(f"SELECT * FROM tournaments WHERE timestamp>{now}").fetchall()

        for item in response:
            tourney = cls._create_instance_from_raw(client, item)

            tourney_list.append(tourney)

        return tourney_list

    @classmethod
    def get_tournament_by_id(cls, client, t_id):
        response = conn.execute("SELECT * FROM tournaments WHERE ID=?", (str(t_id),)).fetchone()

        if response is not None:
            response = cls._create_instance_from_raw(client, response)

        return response

    @classmethod
    def get_tournament_by_name(cls, client, t_name):
        response = conn.execute("SELECT * FROM tournaments WHERE name=?", (t_name,)).fetchone()

        if response is not None:
            response = cls._create_instance_from_raw(client, response)

        return response

    @classmethod
    def custom_statement(cls, client, statement):
        response = conn.execute(statement).fetchall()
        out = []

        for item in response:
            if item is not None:
                instance = cls._create_instance_from_raw(client, item)
                out.append(instance)

        return out
