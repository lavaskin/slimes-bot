import os
import discord
from discord.ext import commands
from dotenv import load_dotenv


# Setup Bot
load_dotenv()
activity = discord.Activity(type=discord.ActivityType.listening, name="s!help")
bot = commands.Bot(command_prefix='s!', activity=activity, case_insensitive=True)


@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandOnCooldown):
		# Check if more than 2 minutes remaining
		if error.retry_after < 121:
			await ctx.reply('You can use this command again in *{0} seconds*.'.format(int(error.retry_after)), delete_after=5)
		else:
			await ctx.reply('You can use this command again in *{0} minutes*.'.format(int(error.retry_after / 60)), delete_after=5)
	elif isinstance(error, commands.CommandNotFound):
		await ctx.reply('That command doesn\'t exist!')

@bot.event
async def on_ready():
	print(' > Discord connected, bot on:')

if __name__ == '__main__':
	env = os.getenv('SLIME_DEV', 'True')
	dev = True if env == 'True' else False
	token = 'DISCORD_DEV' if dev else 'DISCORD_PROD'
	print(' > Dev Mode:', str(dev))

	# Load cogs and run
	bot.load_extension('cogs.slimes')
	bot.run(os.getenv(token), bot=True, reconnect=True)