# Channel Object


class Channel:
    def __init__(self, client):
        # tchannel Temp Edit | Real ID: 553645306957398026
        self.t_channel = client.get_channel(711652464885104701)
        # tchat Temp Edit | Real ID: 553646158786854913
        self.t_chat = client.get_channel(711652552114044948)
        # tplanned Temp Edit | Real ID: 553645189168758795
        self.t_planned = client.get_channel(575627727013412891)
        self.logs = client.get_channel(553887905378992129)
        self.t_logs = client.get_channel(553647392457621504)
        # Real ID: 553886807373381635
        self.bot_cmds = client.get_channel(711653087168823386)
        self.t_demands = client.get_channel(561513445170741259)
        self.error_logs = client.get_channel(707899679257657405)