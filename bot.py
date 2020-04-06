# Tournament Master Refactored Code by Geekid812#1871

# Importing libraries
import discord
from discord.ext import commands
import traceback

# Importing classes and cogs
from core import ReadJSON, UpdatedPresence, Log
from classes.emote import Emote
from cmds.t_organizer import TOrganizer, TournamentJoinException

config = ReadJSON("config.json")
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
        starting = False
        to_cog = TOrganizer(client)

        client.add_check(commands.guild_only())
        client.add_cog(to_cog)

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
    if reaction.message.id == to_cog.tournament.msg.id:
        ctx = await client.get_context(to_cog.tournament.msg)
        ctx.author = user
        ctx.message.author = user
        await reaction.remove(user)
        if reaction.emoji == "\u2795":  # Join button
            ctx.command = client.get_command("join")
        elif reaction.emoji == "📽️":  # Spectate button
            ctx.command = client.get_command("spectate")
        await client.invoke(ctx)
    else:
        await UpdateChecklist(reaction)

@client.event
async def on_reaction_remove(reaction, user):
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


@client.event
async def on_member_update(before, after):
    if before.status != after.status:  # Member updated his status
        await client.change_presence(activity=UpdatedPresence(client))

# Error Handler
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.BadArgument):  # Bad Argument Raised
        e = str(error).replace('"', '`')
        await ctx.send(f"{Emote.deny} {e}")
        return

    # Missing Required Argument Raised
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(f"{Emote.deny} **Missing Required Argument** \nThis command requires more arguments. Try again by providing a `{error.param}` parameter this time!")
        return

    if isinstance(error, TournamentJoinException):
        message = f"{Emote.deny} {ctx.author.mention}, {str(error)}"
        await ctx.send(message, delete_after=10)
        Log("Tournament Join Failed",
            color=discord.Color.dark_red(),
            fields=[{'name': "Denial Message", 'value': message}])
        return

    # None of previously mentioned errors
    traceback.print_exception(type(error), error, error.__traceback__)

# Run Client
client.run(config['token'])
