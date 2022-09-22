import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv


# Setup Bot
load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
activity = discord.Activity(type=discord.ActivityType.listening, name="s!help")
bot = commands.Bot(
	command_prefix='s!',
	activity=activity,
	case_insensitive=True,
	intents=intents
)


@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandOnCooldown):
		# Check if more than 2 minutes remaining
		if error.retry_after < 121:
			await ctx.reply('You can use this command again in *{0} seconds*.'.format(int(error.retry_after)), delete_after=5)
		else:
			await ctx.reply('You can use this command again in *{0} minutes*.'.format(int(error.retry_after / 60)), delete_after=5)
	if isinstance(error, commands.CommandNotFound):
		await ctx.reply('That command doesn\'t exist!')

@bot.event
async def on_ready():
	print(' > Discord connected, bot on:')


async def main():
	env = os.getenv('SLIME_DEV', 'True')
	dev = True if env == 'True' else False
	token = 'DISCORD_DEV' if dev else 'DISCORD_PROD'
	print(' > Dev Mode:', str(dev))

	# Load cogs and run
	await bot.load_extension('cogs.slimes')
	await bot.start(os.getenv(token), reconnect=True)

if __name__ == '__main__':
	# Catch CTRL+C
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		print(' > CTRL+C detected, exiting...')