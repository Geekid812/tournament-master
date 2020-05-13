# Debug Cog

# Importing Libraries
import discord
from discord.ext import commands

to_cog = None
stats_cog = None


class Debug(commands.Cog):
    def __init__(self, client, **kwargs):
        self.client = client

        global to_cog
        global stats_cog
        to_cog = kwargs.get("to_cog")
        stats_cog = kwargs.get("stats_cog")

    async def _eval(self, ctx, cmd):
        try:
            try:
                result = eval(cmd)
            except SyntaxError:
                result = exec(cmd)

            return result
        except Exception as e:
            raise commands.BadArgument("Eval raised an exception: `" + str(e) + "`")

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx, cog, *, cmd):
        cog_aliases = {"t_organizer": to_cog,
                       "to": to_cog,
                       "stats": stats_cog,
                       "debug": self}

        try:
            cog = cog_aliases[cog]
        except KeyError:
            raise commands.BadArgument(f"Cog `{cog}` not found.")

        result = await cog._eval(ctx, cmd)

        if result != "":
            await ctx.send(str(result))
