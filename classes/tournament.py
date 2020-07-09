# Tournament Object

from discord import Embed, Color, utils
from core import ModifierCheck
from classes.emote import Emote
from core import ReadJSON
from dateutil import parser
from datetime import datetime, timedelta
import sqlite3
from asyncio import CancelledError

conn = sqlite3.connect("data/database.db")

cursor = conn.cursor()

config = ReadJSON("config.json")

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


class Tournament():
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
                    p_list = p_list[:sindex] + "s are" + p_list[sindex+5:]

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


    def add_participant(self,user):
        if False in self.participants:
            index = self.participants.index(False)
            self.participants[index] = user
        else:
            self.participants.append(user)

    def remove_participant(self,user):
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
        xp = 50 # Default for participation
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

        order = ('name','host_id','prize','timestamp','status','roles','note')
        attrlist = []

        for attr in order:
            attrlist.append(attrs[attr])


        tourney = cursor.execute(
            "SELECT * FROM tournaments WHERE ID=?", (self.id,)).fetchone()

        if tourney is None:
            cursor.execute(
                "INSERT INTO tournaments(name, host_id, prize, timestamp, status, roles, note) VALUES (?,?,?,?,?,?,?)", attrlist)
            tourney = cursor.execute(
                "SELECT ID FROM tournaments ORDER BY ID DESC").fetchone()
            conn.commit()
            self.id = tourney[0]

        else:
            cmd = "UPDATE tournaments SET "
            update = []

            for i in range(len(attrlist)):
                
                if attrlist[i] != tourney[i+1]:
                    cmd += order[i] + "=?, "
                    update.append(attrlist[i])
            
            cmd = cmd[:-2] + " WHERE ID=?"
            update.append(self.id)

            cursor.execute(cmd, update)
            conn.commit()

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
        except CancelledError: pass

    @classmethod
    def _create_instance_from_raw(cls, client, raw):
        guild = client.get_guild(config['guild_id'])
        new_instance = cls()
        attributes = [description[0] for description in cursor.description]

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

        response = cursor.execute(f"SELECT * FROM tournaments WHERE timestamp>{now}").fetchall()

        for item in response:

            tourney = cls._create_instance_from_raw(client, item)
            
            tourney_list.append(tourney)
        
        return tourney_list

    @classmethod
    def get_tournament_by_id(cls, client, t_id):
        response = cursor.execute("SELECT * FROM tournaments WHERE ID=?", (str(t_id),)).fetchone()

        if response is not None:
            response = cls._create_instance_from_raw(client, response)

        return response

    @classmethod
    def get_tournament_by_name(cls, client, t_name):
        response = cursor.execute("SELECT * FROM tournaments WHERE name=?", (t_name,)).fetchone()

        if response is not None:
            response = cls._create_instance_from_raw(client, response)

        return response

    @classmethod
    def custom_statement(cls, client, statement):
        response = cursor.execute(statement).fetchall()
        out = []

        for item in response:
            if item is not None:
                instance = cls._create_instance_from_raw(client, item)
                out.append(instance)

        conn.commit()
        return out
