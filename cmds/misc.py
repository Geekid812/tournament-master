# Misc Cog

# Importing Libraries
import discord
import asyncio
import random
from discord.ext import commands
from classes.emote import Emote
from classes.perms import allowed_channels


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

    @commands.command()
    @allowed_channels(["bot_cmds"])
    async def gnk(self, ctx, opponent: discord.Member):
        if opponent == ctx.author:
            raise commands.BadArgument("Sadly, you cannot challenge yourself.")

        if opponent == self.client:
            raise commands.BadArgument("Hey, I don't want to fight!")

        await ctx.send(f"**{ctx.author.name}** challenged **{opponent.name}** to a GNK duel! They"
                       " have 30 seconds to type `accept`.")

        def check(msg):
            return all([msg.author == opponent,
                        msg.channel == ctx.channel,
                        msg.content.lower() in ('accept', 'yes', 'acc', 'y')])

        try:
            await asyncio.wait_for('message', timeout=30, check=check)
        except asyncio.TimeoutError:
            await ctx.send("The challenge invite expired. Sad moment.")
            return

        # P1 = Author | P2 = Opponent (Challenged Player)

        moves = {"geek":{"beats": ["nou", "ray"]},
                 "nou":{"beats": ["king", "ray"]},
                 "king":{"beats": ["geek", "mein"]},
                 "ray":{"beats": ["king", "mein"]},
                 "mein":{"beats": ["geek", "nou"]}}

        def check_p1(msg):
            return all([msg.author == ctx.author,
                        msg.channel == ctx.author.id,
                        msg.content.lower() in moves.keys()])

        await ctx.send(f"{ctx.author.mention}, its your turn! Send me your choice in DM!"
                       "\nAvailable moves: `geek` `nou` `king` `ray` `mein`")

        try:
            p1_msg = await asyncio.wait_for('message', timeout=120, check=check_p1)
            await p1_msg.add_reaction(Emote.check)
            p1_choice = p1_msg.content.lower()
        except asyncio.TimeoutError:
            await ctx.send("Hello there? I didn't get any reply? Guess I'm cancelling the game.")
            return

        def check_p2(msg):
            return all([msg.author == opponent,
                        msg.channel == opponent.id,
                        msg.content.lower() in moves.keys()])

        await ctx.send(f"{opponent.mention}, its your turn! Send me your choice in DM!"
                       "\nAvailable moves: `geek` `nou` `king` `ray` `mein`")

        try:
            p2_msg = await asyncio.wait_for('message', timeout=120, check=check_p2)
            await p2_msg.add_reaction(Emote.check)
            p2_choice = p2_msg.content.lower()
        except asyncio.TimeoutError:
            await ctx.send("Hello there? I didn't get any reply? Guess I'm cancelling the game.")
            return

        results_in_msgs = [
            "The results are in!",
            "Alright, can we get a drumroll?",
            "Are you ready for the results?",
            "How did it turn out?",
            "Let's see who won that one.",
            "Can we get some hype here for the results?",
            "I'm ready for the results!",
            "What do you think will happen?"
        ]

        await ctx.send(random.choice(results_in_msgs))
        await asyncio.sleep(5)