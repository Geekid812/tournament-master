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

        if opponent == self.client.user:
            raise commands.BadArgument("Hey, I don't want to fight!")

        await ctx.send(f"**{ctx.author.name}** challenged **{opponent.name}** to a GNK duel! They"
                       " have 30 seconds to type `accept`.")

        def check(msg):
            return all([msg.author == opponent,
                        msg.channel == ctx.channel,
                        msg.content.lower() in ('accept', 'yes', 'acc', 'y')])

        try:
            await self.client.wait_for('message', timeout=30, check=check)
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
            conditions = [msg.author == ctx.author,
                          msg.channel == ctx.author.dm_channel,
                          msg.content.lower() in moves.keys()]
            return all(conditions)

        await ctx.send(f"{ctx.author.mention}, its your turn! Send me your choice in DM!"
                       "\nAvailable moves: `geek` `nou` `king` `ray` `mein`")

        try:
            p1_msg = await self.client.wait_for('message', timeout=120, check=check_p1)
            await p1_msg.add_reaction(Emote.check)
            p1_choice = p1_msg.content.lower()
        except asyncio.TimeoutError:
            await ctx.send("Hello there? I didn't get any reply? Guess I'm cancelling the game.")
            return

        def check_p2(msg):
            return all([msg.author == opponent,
                        msg.channel == opponent.dm_channel,
                        msg.content.lower() in moves.keys()])

        await ctx.send(f"{opponent.mention}, its your turn! Send me your choice in DM!"
                       "\nAvailable moves: `geek` `nou` `king` `ray` `mein`")

        try:
            p2_msg = await self.client.wait_for('message', timeout=120, check=check_p2)
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
        await asyncio.sleep(6)

        if p2_choice in moves[p1_choice]["beats"]:
            winner = ctx.author
            loser = opponent
            win_pick = p1_choice.capitalize()
            lose_pick = p2_choice.capitalize()
        elif p1_choice in moves[p2_choice]["beats"]:
            winner = opponent
            loser = ctx.author
            win_pick = p2_choice.capitalize()
            lose_pick = p1_choice.capitalize()
        else:
            tie_msgs = [
                "Seems like a bruh moment.",
                "Not nice.",
                "This does not spark joy :(",
                "Booooooring!",
                "Gotta try again lol"
            ]
            await ctx.send(f"Its a tie! You both picked {p1_choice.capitalize()}. " + random.choice(tie_msgs))
            return

        deaths = [
            f"{win_pick} stabs {lose_pick} during a tourney! RIP {loser.mention} you didn't pick the right teammate",
            f"{win_pick} is clearly superior to {lose_pick}, that makes {winner.mention} the winner!",
            f"{lose_pick} stood no chance against {win_pick}. Congrats {winner.mention}!",
            f"{win_pick} (who is secretly {winner.mention}) brutally banpanned {lose_pick}! That's a savage move.",
            f"{win_pick} demoted {lose_pick} for being mean. wack\n\nAlso can we get an F for {loser.mention}",
            f"{win_pick} stepped on {lose_pick}'s toes because they only had lemonade and no grapes"
            f"\n\nI knew {loser.mention} would lose this one"
        ]

        await ctx.send(random.choice(deaths))
