# Channel Object

from time import sleep


class Channel:
    def __init__(self, client):
        for i in range(5):
            self.t_channel = client.get_channel(575627727013412891)
            self.t_chat = client.get_channel(575627727013412891)
            self.t_planned = client.get_channel(575627727013412891)
            self.logs = client.get_channel(553887905378992129)
            self.t_logs = client.get_channel(575627727013412891)
            self.bot_cmds = client.get_channel(553886807373381635)
            self.t_demands = client.get_channel(561513445170741259)
            self.error_logs = client.get_channel(707899679257657405)

            all_channels = [getattr(self, c) for c in dir(self) if not c.startswith("_")]

            if None not in all_channels: break
            if i < 4:
                print(f"Failed to load channels, retrying in 5 seconds. ({str(4 - i)} attempts left)")
                sleep(5)
            else:
                print("Failed to load channels!")