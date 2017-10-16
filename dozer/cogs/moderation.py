import asyncio, discord
from discord.ext.commands import has_permissions, bot_has_permissions
from .. import db
from ._utils import *

class Moderation(Cog):
	@command()
	@has_permissions(ban_members=True)
	@bot_has_permissions(ban_members=True)
	async def ban(self, ctx, user_mentions: discord.User, *, reason):
		"Bans the user mentioned."
		usertoban = user_mentions
		howtounban = "When it's time to unban, here's the ID to unban: <@{} >".format(usertoban.id)
		modlogmessage = "{} has been banned by {} because {}. {}".format(usertoban, ctx.author.mention, reason, howtounban)
		await ctx.guild.ban(usertoban)
		await ctx.send(modlogmessage)
		with db.Session() as session:
			modlogchannel = session.query(ModerationSettings).filter_by(id=ctx.guild.id).one_or_none()
			if modlogchannel is not None:
				channel = ctx.guild.get_channel(modlogchannel.modlog_channel)
				await channel.send(modlogmessage)
			else:
				await ctx.send("Please configure modlog channel to enable modlog functionality")
	
	@command()
	@has_permissions(ban_members=True)
	@bot_has_permissions(ban_members=True)
	async def unban(self, ctx, user_mentions: discord.User, *, reason):
		"Unbans the user ID mentioned."
		usertoban = user_mentions
		await ctx.guild.unban(usertoban)
		modlogmessage = "{} has been unbanned by {} because {}".format(usertoban, ctx.author.mention, reason)
		await ctx.send(modlogmessage)
		with db.Session() as session:
			modlogchannel = session.query(ModerationSettings).filter_by(id=ctx.guild.id).one_or_none()
			if modlogchannel is not None:
				channel = ctx.guild.get_channel(modlogchannel.modlog_channel)
				await channel.send(modlogmessage)
			else:
				await ctx.send("Please configure modlog channel to enable modlog functionality")
	
	@command()
	@has_permissions(kick_members=True)
	@bot_has_permissions(kick_members=True)
	async def kick(self, ctx, user_mentions: discord.User, *, reason):
		"Kicks the user mentioned."
		usertokick = user_mentions
		await ctx.guild.kick(usertokick)
		modlogmessage = "{} has been kicked by {} because {}".format(usertokick, ctx.author.mention, reason)
		await ctx.send(modlogmessage)
		with db.Session() as session:
			modlogchannel = session.query(ModerationSettings).filter_by(id=ctx.guild.id).one_or_none()
			if modlogchannel is not None:
				channel = ctx.guild.get_channel(modlogchannel.modlog_channel)
				await channel.send(modlogmessage)
			else:
				await ctx.send("Please configure modlog channel to enable modlog functionality")
	
	@command()
	@has_permissions(administrator=True)
	async def config(self, ctx, channel_mentions: discord.TextChannel):
		"""Set the modlog channel for a server by passing the channel id"""
		print(channel_mentions)
		with db.Session() as session:
			config = session.query(ModerationSettings).filter_by(id=str(ctx.guild.id)).one_or_none()
			if config is not None:
				print("config is not none")
				config.name = ctx.guild.name
				config.modlog_channel = str(channel_mentions.id)
			else:
				print("Config is none")
				config = ModerationSettings(id=ctx.guild.id, modlog_channel=channel_mentions.id, name=ctx.guild.name)
				session.add(config)
			await ctx.send(ctx.message.author.mention + ', modlog settings configured!')
	
	@command()
	@has_permissions(manage_roles=True)
	@bot_has_permissions(manage_roles=True)
	async def timeout(self, ctx, duration: float):
		"""Set a timeout (no sending messages or adding reactions) on the current channel."""
		with db.Session() as session:
			settings = session.query(ModerationSettings).filter_by(id=ctx.guild.id).one_or_none()
			if settings is None:
				settings = ModerationSettings(id=ctx.guild.id, name=ctx.guild.name)
				session.add(settings)
			
			members_role = discord.utils.get(ctx.guild.roles, id=settings.members_role) # None-safe - nonexistent or non-configured role return None
		
		if members_role is not None:
			targets = {members_role}
		else:
			# TODO determine what role to mute
			targets = set()
		
		to_restore = [tup for tup in ctx.channel.overwrites if tup[0] in targets]
		for target, overwrite in to_restore:
			new_overwrite = discord.PermissionOverwrite.from_pair(*overwrite.pair())
			new_overwrite.update(send_messages=False, add_reactions=False)
			await ctx.channel.set_permissions(target, overwrite=new_overwrite)
		
		for allow_target in (ctx.me, ctx.author):
			overwrite = ctx.channel.overwrites_for(allow_target)
			new_overwrite = discord.PermissionOverwrite.from_pair(*overwrite.pair())
			new_overwrite.update(send_messages=True)
			await ctx.channel.set_permissions(allow_target, overwrite=new_overwrite)
			to_restore.append((allow_target, overwrite))
		
		await asyncio.sleep(duration)
		
		for target, overwrite in to_restore:
			await ctx.channel.set_permissions(target, overwrite=overwrite)
	
	timeout.example_usage = """
	`{prefix}timeout 60` - prevents sending messages in this channel for 1 minute (60s)
	"""

class ModerationSettings(db.DatabaseObject):
	__tablename__ = 'modlogconfig'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String)
	modlog_channel = db.Column(db.Integer, nullable=True)
	members_role = db.Column(db.Integer, nullable=True)

def setup(bot):
	bot.add_cog(Moderation(bot))
