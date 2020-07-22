# User Object

import sqlite3
import math
from core import ReadJSON

conn = sqlite3.connect("data/database.db", isolation_level=None)
ROWS = ("ID", "username", "IGN", "participations", "wins", "hosted",
        "streak", "streak_age", "max_streak", "level", "xp")

config = ReadJSON("config.json")


class User:
    @classmethod
    def _create_instance_from_raw(cls, raw):
        new_instance = cls()
        for i in range(len(ROWS)):
            setattr(new_instance, "_" + ROWS[i], raw[i])

        return new_instance

    @classmethod
    def fetch_by_id(cls, ctx, user_id):
        user_id = str(user_id)
        user = conn.execute(
            "SELECT * FROM stats WHERE ID=?", (user_id,)).fetchone()
        member = ctx.bot.get_guild(config['guild_id']).get_member(int(user_id))
        username = f"{member.name}#{member.discriminator}"

        if user is None:  # New User
            conn.execute(
                "INSERT INTO stats (ID, username) VALUES (?,?)", (user_id, username))
            user = conn.execute(
                "SELECT * FROM stats WHERE ID=?", (user_id,)).fetchone()

        user_class = cls._create_instance_from_raw(user)

        # Always update username
        if user_class.username != username: user_class.username = username

        return user_class

    @classmethod
    def fetch_by_ids(cls, ctx, user_ids: list):
        ids = tuple(user_ids)
        result = []

        if len(ids) == 1:
            ids = str(ids)[:-2] + ")"
        users = conn.execute(f"SELECT * FROM stats WHERE ID IN {ids}").fetchall()

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
