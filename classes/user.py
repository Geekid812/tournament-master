# User Object

import sqlite3
from discord.ext.commands import MemberConverter

conn = sqlite3.connect("data/database.db")

cursor = conn.cursor()


class User:
    @classmethod
    async def from_id(self, ctx, user_id):
        user_id = str(user_id)
        user = cursor.execute(
            "SELECT * FROM users WHERE ID=?", (user_id,)).fetchone()
        member = await MemberConverter().convert(ctx, user_id)
        username = f"{member.name}#{member.discriminator}"

        if user is None:  # New User
            print("New database user: " + username)
            cursor.execute(
                "INSERT INTO users (ID, username) VALUES (?,?)", (user_id, username))
            conn.commit()
            user = cursor.execute(
                "SELECT * FROM users WHERE ID=?", (user_id,)).fetchone()

        # A list of all attributes
        attributes = [description[0] for description in cursor.description]
        for i in range(len(attributes)):
            setattr(self, "_" + attributes[i], user[i])
        
        # Always update username
        if self.username != username: self.username = username
        return User()

    @property
    def id(self):
        return self._ID

    @id.setter
    def id(self, value: int):
        self._ID = value
        cursor.execute("UPDATE users SET ID=? WHERE ID=?", (value, self.id))
        conn.commit()

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value: str):
        self._username = value
        cursor.execute("UPDATE users SET username=? WHERE ID=?",
                       (value, self.id))
        conn.commit()

    @property
    def ign(self):
        return self._IGN

    @ign.setter
    def ign(self, value: str):
        self._IGN = value
        cursor.execute("UPDATE users SET IGN=? WHERE ID=?",
                       (value, self.id))
        conn.commit()

    @property
    def participations(self):
        return self._participations

    @participations.setter
    def participations(self, value: int):
        self._participations = value
        cursor.execute(
            "UPDATE users SET participations=? WHERE ID=?", (value, self.id))
        conn.commit()

    @property
    def wins(self):
        return self._wins

    @wins.setter
    def wins(self, value: int):
        self._wins = value
        cursor.execute("UPDATE users SET wins=? WHERE ID=?", (value, self.id))
        conn.commit()

    @property
    def hosted(self):
        return self._hosted

    @hosted.setter
    def hosted(self, value: int):
        self._hosted = value
        cursor.execute("UPDATE users SET hosted=? WHERE ID=?",
                       (value, self.id))
        conn.commit()

    @property
    def streak(self):
        return self._streak

    @streak.setter
    def streak(self, value: int):
        self._streak = value
        cursor.execute("UPDATE users SET streak=? WHERE ID=?",
                       (value, self.id))
        conn.commit()

    @property
    def streak_age(self):
        return self._streak_age

    @streak_age.setter
    def streak_age(self, value=None):
        if value is not None:
            value = int(value)
        self._streak_age = value
        cursor.execute(
            "UPDATE users SET streak_age=? WHERE ID=?", (value, self.id))
        conn.commit()

    @property
    def max_streak(self):
        return self._max_streak

    @max_streak.setter
    def max_streak(self, value: int):
        self._max_streak = value
        cursor.execute(
            "UPDATE users SET max_streak=? WHERE ID=?", (value, self.id))
        conn.commit()

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value: int):
        self._level = value
        cursor.execute("UPDATE users SET level=? WHERE ID=?", (value, self.id))
        conn.commit()

    @property
    def xp(self):
        return self._xp

    @xp.setter
    def xp(self, value: int):
        self._xp = value
        cursor.execute("UPDATE users SET xp=? WHERE ID=?", (value, self.id))
        conn.commit()
