# Perms Class

# Importing Libraries
import discord
from discord.ext import commands
from classes.channel import Channel


class MissingPermissions(commands.CheckFailure):
    pass


class InvalidChannel(commands.CheckFailure):
    pass


def authorized(ctx, user=None, level=6, to=False, mech=False):
    """
    Checks if the specified user has the required permissions.

    Level 1 - Helper
    Level 2 - Mini Mod
    Level 3 - Mod
    Level 4 - Super Mod
    Level 5 - Admin
    Level 6 - Bot Owner
    """
    if user is None:
        user = ctx.message.author
    lvl = [554384345645973514, 554384010650845184, 554383429173641227, 554382994589089801, 554382249169256469]
    roles = ctx.message.guild.roles
    perms = 0
    if ctx.message.author.id == 385404247493050369:  # If User is Bot Owner
        perms = 6
    else:
        for i in range(5):
            r = discord.utils.get(roles, id=lvl[i])
            if r in user.roles:
                perms = 5 - i
    to_role = discord.utils.get(roles, id=554385062313852968)
    mech_role = discord.utils.get(roles, id=556420758381789184)
    allowed = False
    if to == True and to_role in user.roles:
        allowed = True
    if mech == True and mech_role in user.roles:
        allowed = True
    if perms >= level:
        allowed = True

    if allowed: return True

    raise MissingPermissions


def is_authorized(level=6, to=False, mech=False):
    def pred(ctx):
        return authorized(ctx, level=level, to=to, mech=mech)

    return commands.check(pred)


def allowed_channels(channel_list, level=6, to=False, mech=False):
    def pred(ctx):
        channels = Channel(ctx.bot)
        list_ = []
        for channel in channel_list:
            list_.append(getattr(channels, channel))

        try:
            authorized(ctx, level=level, to=to, mech=mech)
            return True
        except MissingPermissions:
            if ctx.channel in list_: return True

            raise InvalidChannel

    return commands.check(pred)
