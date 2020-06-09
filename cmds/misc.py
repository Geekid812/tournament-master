# Misc Cog

# Importing Libraries
import discord
from discord.ext import commands


class Misc(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
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