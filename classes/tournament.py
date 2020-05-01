# Tournament Object

from discord import Embed, Object
from core import ModifierCheck
from classes.emote import Emote
from core import ReadJSON
from dateutil import parser
from datetime import datetime
import sqlite3

conn = sqlite3.connect("data/database.db")

cursor = conn.cursor()


class Status:
    Pending = 0
    Scheduled = 1
    Buyable = 2
    Opened = 3
    Closed = 4
    Ended = 5


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
        attrs['timestamp'] = parser.parse(attrs['time'], dayfirst=True, ignoretz=True).timestamp()

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
            print(self.id)
        
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
        
    @classmethod
    def get_tournaments(cls):
        order = ('name','host_id','prize','timestamp','status','roles','note')
        now = datetime.now().timestamp()
        tourney_list = []

        response = cursor.execute("SELECT * FROM tournaments WHERE timestamp>?", (now,)).fetchall()

        for item in response:
            tourney = cls()
            info = item[1:7]

            for i in range(len(info)):
                value = info[i]
                name = order[i]

                if name == 'host_id':
                    name = 'host'
                    value = Object(value)

                if name == 'timestamp':
                    name = 'time'
                    value = datetime.fromtimestamp(value)

                setattr(tourney, name, value)
            
            tourney_list.append(tourney)
        
        return tourney_list
                