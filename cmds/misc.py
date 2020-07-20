# Misc Cog

# Importing Libraries
import discord
import asyncio
import random
import chess
import chess.svg
import json
from svglib.svglib import svg2rlg
from discord.ext import commands
from reportlab.graphics import renderPM
from PIL import Image

from classes.emote import Emote
from classes.perms import bot_cmds_only


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
    @bot_cmds_only()
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

        await ctx.send(f"{ctx.author.mention}, it's your turn! Send me your choice in DM!"
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

        await ctx.send(f"{opponent.mention}, it's your turn! Send me your choice in DM!"
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

    @commands.command()
    @commands.is_owner()
    async def say(self, ctx, *, msg):
        await ctx.send(msg)

    @commands.command()
    @bot_cmds_only()
    async def fiar(self, ctx, opponent: discord.Member):
        if False:
            raise commands.BadArgument("Sadly, you cannot challenge yourself.")

        if opponent == self.client.user:
            raise commands.BadArgument("Not to be rude, but I can't play with you.")

        await ctx.send(f"**{ctx.author.name}** challenged **{opponent.name}** to a 4 in a row duel! They"
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

        def check_emoji_1(msg):
            return all([msg.author == ctx.author,
                        msg.channel == ctx.channel,
                        msg.content in [str(emoji) for emoji in ctx.guild.emojis] + ["⬛"]])

        def check_emoji_2(msg):
            return all([msg.author == opponent,
                        msg.channel == ctx.channel,
                        msg.content in [str(emoji) for emoji in ctx.guild.emojis] + ["⬛"]])

        def check_input_1(msg):
            return all([msg.author == ctx.author,
                        msg.channel == ctx.channel,
                        msg.content in [str(i + 1) for i in range(7)]])

        def check_input_2(msg):
            return all([msg.author == opponent,
                        msg.channel == ctx.channel,
                        msg.content in [str(i + 1) for i in range(7)]])

        await ctx.send(f"{ctx.author.mention}, type the emoji you want to use in chat! (Only uses this server's emojis)")

        try:
            msg = await self.client.wait_for('message', timeout=60, check=check_emoji_1)
            p1_emoji = msg.content
        except asyncio.TimeoutError:
            await ctx.send("I guess you don't want to pick anything? I'll cancel this then...")
            return

        await ctx.send(f"{opponent.mention}, type the emoji you want to use in chat! (Only uses this server's emojis)")

        try:
            msg = await self.client.wait_for('message', timeout=60, check=check_emoji_2)
            p2_emoji = msg.content
        except asyncio.TimeoutError:
            await ctx.send("I guess you don't want to pick anything? I'll cancel this then...")
            return

        # P1 = Author | P2 = Opponent (Challenged Player)
        # 0 = None | 1 = P1 | 2 = P2

        board = [[0 for i in range(6)] for i in range(7)]
        first_row = "1⃣2⃣3⃣4⃣5⃣6⃣7⃣ \n"
        winner = None
        turn = 1

        while True:
            # Draw Board
            embed = discord.Embed(name="4 in a Row", color=discord.Color.blue())

            if winner == 1:
                embed.set_author(name=f"{ctx.author.name} wins!")
                embed.color = discord.Color.gold()

            elif winner == 2:
                embed.set_author(name=f"{opponent.name} wins!")
                embed.color = discord.Color.gold()

            elif turn == 1:
                embed.set_author(name=f"{ctx.author.name} is playing!")
                check_func = check_input_1

            else:
                embed.set_author(name=f"{opponent.name} is playing!")
                check_func = check_input_2

            text = ""
            for r in range(6):
                for c in range(7):
                    if board[c][r] == 0:
                        text += ":black_large_square:"
                    elif board[c][r] == 1:
                        text += p1_emoji
                    else:
                        text += p2_emoji
                text += "\n"

            embed.description = first_row + text
            await ctx.send(embed=embed)

            if winner is not None: break

            # Wait For Input
            exit_input = False
            while not exit_input:
                try:
                    msg = await self.client.wait_for('message', timeout=120, check=check_func)
                    col = int(msg.content) - 1
                except asyncio.TimeoutError:
                    await ctx.send("I guess you don't want to pick anything? I'll cancel this then...")
                    return

                for row in reversed(range(6)):
                    if board[col][row] == 0:
                        row_chosen = row
                        board[col][row] = turn
                        exit_input = True
                        break

                if not exit_input:
                    await ctx.send("Hold on, you can't place anything here! Try another column!")

            # Detect Win
            for checknum in range(4):
                # 0 = Column | 1 = Row | 2 = Diagonal Downwards | 3 = Diagonal Upwards
                in_a_row = 0
                for i in range(7):

                    # Choose condition
                    if checknum == 0:
                        if i == 6: continue
                        item = board[col][i]

                    elif checknum == 1:
                        item = board[i][row_chosen]

                    elif checknum == 2:
                        row_item = row_chosen - col + i
                        if row_item > 5 or row_item < 0:
                            in_a_row = 0
                            continue
                        item = board[i][row_item]

                    elif checknum == 3:
                        row_item = row_chosen + col - i
                        if row_item > 5 or row_item < 0:
                            in_a_row = 0
                            continue
                        item = board[i][row_item]

                    if item == turn:
                        in_a_row += 1
                        if in_a_row == 4:
                            winner = turn
                            break
                    else:
                        in_a_row = 0


            # Change Turn
            turn += 1
            if turn == 3: turn = 1

    @commands.command()
    @bot_cmds_only()
    async def chess(self, ctx, opponent: discord.Member):
        if opponent == ctx.author:
            raise commands.BadArgument("Sadly, you cannot challenge yourself.")

        if opponent == self.client.user:
            raise commands.BadArgument("I'm not big brain enough to play with you, sorry!")

        await ctx.send(f"**{ctx.author.name}** challenged **{opponent.name}** to a game of chess! They"
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

        await ctx.send(f":white_large_square: {ctx.author.name}\n:black_large_square: {opponent.name}")

        await self.chess_loop(ctx, p1=ctx.author, p2=opponent)

    async def chess_loop(self, ctx, p1, p2):

        def check_input_1(msg):
            try:
                s = msg.content.split(" ")
                f = s[0].lower()
                t = s[1].lower()
                chess.Move.from_uci(f + t)
            except:
                return False

            return all([msg.author == p1,
                        msg.channel == ctx.channel])

        def check_input_2(msg):
            try:
                s = msg.content.split(" ")
                f = s[0].lower()
                t = s[1].lower()
                chess.Move.from_uci(f + t)
            except:
                return False

            return all([msg.author == p2,
                        msg.channel == ctx.channel])

        game_over = False
        board = chess.Board()
        last_move_info = ""
        title = p1.name + " is playing!"
        color = discord.Color.blue()

        while not game_over:
            playing = p1 if board.turn == chess.WHITE else p2
            check_func = check_input_1 if board.turn == chess.WHITE else check_input_2
            turn_count = board.fullmove_number
            image = await self.create_board_image(board)

            embed = discord.Embed(description=last_move_info, color=color)
            embed.set_footer(text="Turn " + str(turn_count))
            embed.set_author(name=title)
            embed.set_image(url="attachment://board.png")
            await ctx.send(file=image, embed=embed)

            end_turn = False
            while not end_turn:
                try:
                    msg = await self.client.wait_for('message', timeout=600, check=check_func)
                    content = msg.content
                except asyncio.TimeoutError:
                    await ctx.send("Well then, I see you aren't going to play the game. Might as well cancel...")
                    return

                split = content.split(" ")
                from_ = split[0]
                to_ = split[1]
                move = chess.Move.from_uci(from_.lower() + to_.lower())

                if move in board.legal_moves:
                    board.push(move)
                    last_move_info = f"{playing.name} moved `{from_.upper()}` to `{to_.upper()}`."

                    if board.is_checkmate():
                        game_over = True
                        embed = discord.Embed(title="Checkmate!",
                                              description=f"{playing.name} wins!",
                                              color=discord.Color.gold())
                        image = await self.create_board_image(board)
                        embed.set_image(url="attachment://board.png")
                        await ctx.send(file=image, embed=embed)

                    elif board.is_check():
                        title = "Check!"
                        color = discord.Color.teal()

                    elif board.is_game_over(claim_draw=False):
                        game_over = True
                        embed = discord.Embed(title="Game Over!",
                                              description=f"{playing.name} wins!",
                                              color=discord.Color.dark_red())
                        image = await self.create_board_image(board)
                        embed.set_image(url="attachment://board.png")
                        await ctx.send(file=image, embed=embed)

                    else:
                        next_playing = p2 if p1 == playing else p1
                        title = next_playing.name + " is playing!"
                        color = discord.Color.blue()

                    end_turn = True

                else:
                    await ctx.send("This move is not valid! Try again.")

    @staticmethod
    async def create_board_image(board):
        try:
            move = board.peek()
            arrow = chess.svg.Arrow(move.from_square, move.to_square, color='#37a1ff')
            arrows = [arrow]
        except IndexError:
            arrows = []

        img = chess.svg.board(board=board, arrows=arrows)

        with open('assets/chess_board.svg', "w") as out:
            out.write(img)

        drawing = svg2rlg("assets/chess_board.svg")
        renderPM.drawToFile(drawing, "assets/chess_board.png", fmt="PNG")
        img = Image.open('assets/chess_board.png')
        img.save('assets/chess_board.png')

        return discord.File(fp="assets/chess_board.png", filename="board.png")

    @commands.command()
    @bot_cmds_only()
    async def item(self, ctx, *, name):
        with open("assets/items.json", "r") as f:
            items = json.load(f)

        encoded_name = name.lower().replace(" ", "-")
        search_results = [item for item in items if encoded_name in item['name']]

        if len(search_results) != 1:
            embed = discord.Embed(title=f"Found {len(search_results)} results matching '{name}'",
                                  color=discord.Color.dark_teal())

            if len(search_results) < 30:
                text = ""
                num = 1
                for result in search_results:
                    text += f"`{num} -` {result['name']}\n"
                    num += 1

                if len(search_results) == 0:
                    text = "No results found! \\:("

            else:
                text = "Please be more precise in your search!"

            embed.description = text
            await ctx.send(embed=embed)
            return

        item_ = search_results[0]
        clean_name = item_["name"].replace("-", " ").title()
        embed = discord.Embed(title=clean_name)
        embed.set_image(url=item_["image"])

        if item_["rarity"] == "RARE":
            embed.color = discord.Color.blue()

        elif item_["rarity"] == "EPIC":
            embed.color = discord.Color.dark_magenta()

        elif item_["rarity"] == "LEGENDARY":
            embed.color = discord.Color.gold()

        embed.add_field(name="Item Type", value=item_["type"].capitalize())
        embed.add_field(name="Rarity", value=item_["rarity"].capitalize())

        if "itemSet" in item_.keys():
            clean_set_name = item_["itemSet"].replace("-", " ").title()
            embed.add_field(name="Item Set", value=clean_set_name)

        if item_["costGems"] != -1:
            embed.add_field(name="Cost", value=f"{item_['costGems']} gems")

        elif item_["costRoses"] != -1:
            embed.add_field(name="Cost", value=f"{item_['costRoses']} roses")

        elif item_["costCoins"] != -1:
            embed.add_field(name="Cost", value=f"{item_['costCoins']} coins")

        elif item_["minLevel"] != -1:
            embed.add_field(name="Level Required", value=str(item_["minLevel"]))

        await ctx.send(embed=embed)
