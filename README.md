# [Slimes! Discord Bot](https://slimes.lavask.in)

A discord bot where you can generate, trade and collect uniquely generated slimes! \
The bot has an econemy system, use s!claim to claim coins every hour and s!generate to create a slime!

### **How to build the bot**:
1. Fill out all the relevant information in a '.env' file. Use .env-example.txt as a reference.
2. Create an /other/firebase.json file from the json Firebase gives you on their site after you initialize a firestore database.
1. Run bot.py using python3 directly.
1. Note that I'm not going out of my way to support forks of the project so don't ask for help on setting it up.

### **Bot Commands (Prefix: s!)**:
See [this description file](https://github.com/Lavaskin/slimes-bot/blob/main/other/commands.json) as I'm too lazy to maintain two lists, or use s!help on the bot.

### **TODO**
- Create custom help command.
	- Default command is restrictive in its formatting and looks bad.
- Make favorites appear at the top of the inventory list
- Make it possible for specific hats to go behind the slime body layer
- Remove slime files from firebase/storage when s!reset is used
- Add s!sell to sell slimes you don't want.
	- Add a reaction option when generating a slime to automatically sell it w/o s!sell.

### **Credits**
- PhinalDestination: SlimeV2 pixel art. General testing.
- KingTenechi: Ideas and help with color verification.
- Sinful Dante: General testing.
- Mr. Pt: General testing.
- Holmesian: Tons of assets added in [this commit](https://github.com/Lavaskin/slimes-bot/commit/e0ab292ff4e4977a9c3004bfe95d3316373c5c93)!