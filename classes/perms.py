# Perms Class

# Importing Libraries
import discord
from discord.ext import commands
from classes.channel import Channel


class MissingPermissions(commands.CheckFailure):
    pass


class InvalidChannel(commands.CheckFailure):
    pass


def authorized(ctx, user=None, level=5, to=False):
    """
    Checks if the specified user has the required permissions.

    Level 1 - Mini Mod
    Level 2 - Mod
    Level 3 - Super Mod
    Level 4 - Admin
    Level 5 - Bot Owner
    """
    if user is None:
        user = ctx.message.author

    if ctx.message.author.id == 385404247493050369:  # If User is Bot Owner
        return True

    roles = ctx.message.guild.roles
    perms = 0

    if level != 5:
        lvl = [554384345645973514, 554384010650845184, 554383429173641227, 554382994589089801]

        for i in range(4):
            r = discord.utils.get(roles, id=lvl[i])
            if r in user.roles:
                perms = 4 - i

    to_role = discord.utils.get(roles, id=554385062313852968)
    allowed = False
    if to is True and to_role in user.roles:
        allowed = True
    if perms >= level:
        allowed = True

    if allowed: return True

    raise MissingPermissions


def is_authorized(level=5, to=False):
    def pred(ctx):
        return authorized(ctx, level=level, to=to)

    return commands.check(pred)


def bot_cmds_only():
    def pred(ctx):
        channels = Channel(ctx.bot)
        list_ = [channels.bot_cmds, channels.t_channel]

        try:
            authorized(ctx, level=1, to=True)
            return True
        except MissingPermissions:
            if ctx.channel in list_: return True

            raise InvalidChannel

    return commands.check(pred)
