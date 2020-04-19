# Tournament Object

from discord import Embed
from core import ModifierCheck
from classes.emote import Emote


class Status:
    Pending = 0
    Scheduled = 1
    Buyable = 2
    Opened = 3
    Closed = 4
    Ended = 5


class Tournament():
    def __init__(self):
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