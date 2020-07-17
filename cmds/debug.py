# Debug Cog

# Importing Libraries
import discord
from discord.ext import commands


class Debug(commands.Cog):
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

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx, cog_name, *, cmd):

        cog = self.client.get_cog(cog_name)

        if cog is None:
            raise commands.BadArgument(f"Cog `{cog_name}` not found.")

        result = await cog._eval(ctx, cmd)

        if result != "":
            if len(result) <= 2000:
                await ctx.send(str(result))
            else:
                await ctx.send("Output is too long, showing only the first 2000 characters.")
                await ctx.send(str(result)[:2000])

    @commands.command()
    @commands.is_owner()
    async def stop(self, ctx):
        await ctx.send("Goodbye world!")

        await self.client.close()

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, cog_name):
        cog = self.client.get_cog(cog_name)

        if not isinstance(cog, commands.Cog):
            raise commands.BadArgument("Cog not found.")

        self.client.remove_cog(cog_name)
        self.client.add_cog(cog.__class__(self.client))

        await ctx.send(f"Reloaded cog {cog_name}.")

    @commands.command()
    @commands.is_owner()
    async def upload(self, ctx):
        file = discord.File(fp="data/database.db")
        await ctx.author.send(file=file)

    @staticmethod
    def unlock_db():
        import classes.user
        import classes.tournament
        classes.user.conn.commit()
        classes.tournament.conn.commit()