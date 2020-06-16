# Tournament Master Refactored Code by Geekid812#1871

# Importing libraries
import discord
import textwrap
import os
from discord.ext import commands
import traceback

# Importing classes and cogs
from core import ReadJSON, UpdatedPresence, Log
from classes.emote import Emote
from classes.channel import Channel
from classes.perms import MissingPermissions, InvalidChannel
from cmds.t_organizer import TOrganizer, TournamentJoinException
from cmds.stats import Stats
from cmds.debug import Debug
from cmds.misc import Misc

config = ReadJSON("config.json")
tokens = ReadJSON("tokens.json")
client = commands.Bot(
    command_prefix=config['prefix'], help_command=None, self_bot=False)
starting = True


# Connect Event
@client.event
async def on_ready():
    print("{0.name} is ready!\nID: {0.id}\ndiscord.py Version: {1}".format(
        client.user, str(discord.__version__)))
    # Log("Bot Online", color=discord.Color.green())
    await client.change_presence(activity=UpdatedPresence(client))

    # Cogs and Checks (only on first start)
    global starting
    if starting:
        global to_cog
        global stats_cog
        global debug_cog
        starting = False
        to_cog = TOrganizer(client)
        stats_cog = Stats(client)
        debug_cog = Debug(client)
        misc_cog = Misc(client)

        client.add_check(commands.guild_only())
        client.add_cog(to_cog)
        client.add_cog(stats_cog)
        client.add_cog(debug_cog)
        client.add_cog(misc_cog)


# Disconnect Event
@client.event
async def on_disconnect():
    print(f"{client.user.name} disconnected!")
    Log("Bot Disconnected", color=discord.Color.red())


# Reaction Filter
@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return  # Ignore reactions from the bot
    if to_cog.tournament.msg is not None and reaction.message.id == to_cog.tournament.msg.id:
        ctx = await client.get_context(to_cog.tournament.msg)
        ctx.author = user
        ctx.message.author = user
        await reaction.remove(user)
        if str(reaction.emoji) == Emote.join:  # Join button
            ctx.command = client.get_command("join")
        elif str(reaction.emoji) == "📽️":  # Spectate button
            ctx.command = client.get_command("spectate")
        await client.invoke(ctx)
    elif to_cog.checklist.msg is not None and reaction.message.id == to_cog.checklist.msg.id:
        await UpdateChecklist(reaction)


@client.event
async def on_reaction_remove(reaction, user):
    if to_cog.checklist.msg is not None and reaction.message.id == to_cog.checklist.msg.id:
        await UpdateChecklist(reaction)


async def UpdateChecklist(reaction):
    if to_cog.checklist is not None and reaction.message.id == to_cog.checklist.msg.id:
        if reaction.emoji[0] in to_cog.checklist.emote_str:
            ctx = await client.get_context(to_cog.checklist.msg)
            await to_cog.checklist.update(ctx, to_cog.tournament)


# Presence Manager
@client.event
async def on_member_join(member):
    await client.change_presence(activity=UpdatedPresence(client))


@client.event
async def on_member_leave(member):
    await client.change_presence(activity=UpdatedPresence(client))
    await client.get_cog("TOrganizer").on_member_leave(member)


# Error Handler
@client.event
async def on_command_error(ctx: commands.Context, error):

    if isinstance(error, commands.errors.BadArgument):  # Bad Argument Raised
        e = str(error).replace('"', '`')
        await ctx.send(f"{Emote.deny} {e}")
        return

    # Missing Required Argument Raised
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(
            f"{Emote.deny} **Missing Required Argument** \nThis command requires more arguments. Try again by "
            f"providing a `{error.param}` parameter this time!")
        return

    if isinstance(error, TournamentJoinException):
        message = f"{Emote.deny} {ctx.author.mention}, {str(error)}"
        await ctx.send(message, delete_after=10)
        Log("Tournament Join Failed",
            color=discord.Color.dark_red(),
            fields=[{'name': "Denial Message", 'value': message}])
        return

    if isinstance(error, commands.errors.CommandNotFound): return

    if isinstance(error, MissingPermissions):

        if ctx.command.qualified_name == "setign":
            await ctx.send("I think the command you are looking for is `;ign`. Try it!")

        return

    if isinstance(error, InvalidChannel):

        await ctx.send(f"You cannot use this command here. Move to {Channel(client).bot_cmds.mention} and try again!")

    # None of previously mentioned errors
    embed = discord.Embed(title="An error occured!",
                          description="An unexecpted problem was encountered! The issue has automatically been "
                                      "reported. Sorry for the incovenience!",
                          color=discord.Color.red())
    await ctx.send(embed=embed)

    try:
        await send_traceback(ctx, error)
    except Exception as e:
        await Channel(client).error_logs.send(
            "Unable to send to send full traceback: "
            f"\nCause: `{str(type(e))}: {str(e)}`"
            f"\nMinimal Traceback: `{str(type(error))}: {str(error)}`")
    finally:
        traceback.print_exception(type(error), error, error.__traceback__)


async def send_traceback(ctx, error):
    tb_embed = discord.Embed()

    try:
        error = error.original
    except AttributeError:
        pass

    error_type = str(type(error))[8:-2]
    traceback_lines = traceback.format_exception(type(error), error, error.__traceback__)
    traceback_details = traceback_lines[-2].splitlines()

    line_content = textwrap.dedent(traceback_details[1])
    error_message = traceback_lines[-1]

    raw_context_info = traceback_details[0]
    path_end_index = raw_context_info.find("\", line")
    path = raw_context_info[8: path_end_index]
    context_info = raw_context_info[:8] + os.path.basename(path) + raw_context_info[path_end_index:]

    colors = list(error_type.encode("utf_8"))
    if len(colors) >= 4:
        r = colors[0] * colors[1] % 255
        g = colors[2] * colors[3] % 255
        b = colors[-1] * colors[-2] % 255
    else:
        r, g, b = 0, 0, 0

    tb_embed.title = error_type
    tb_embed.color = discord.Color.from_rgb(r, g, b)
    tb_embed.set_author(name="Traceback")

    tb_embed.add_field(name="Command", value=ctx.message.content)
    tb_embed.add_field(name="Channel", value=ctx.channel.mention)
    tb_embed.add_field(name="Author", value=ctx.author.mention)
    tb_embed.add_field(name=context_info, value="```py\n" + line_content + "\n\n" + error_message + "```", inline=False)

    await Channel(client).error_logs.send(embed=tb_embed)


# Run Client
client.run(tokens['token'])
