# Slimes
*By Lavaskin*

**How to use**:
1. Make an /other/auth.json file in the form: {discordToken:"your token here"}
2. Create an /other/firebase.json file from the json Firebase gives you on their site after you initialize a firestore database.
3. Run using python3 directly or use the included bash script, "run". The code doesn't verify output directories exist, but the run file does, so it will probably crash if ran directly.

**How to use run file**:
- May need to give execution permissions (chmod +x ./run)
- General form: ./run <mode> <gen_amount [optional]> <c [optional]>
- Modes:
	- bot: Runs in discord bot mode
	- gen: Creates a given amount of random slimes. Default of 100. Useful for testing out generation code.
- gen_amount is any integer. Dictates how many slimes are created in gen mode.
- If 'c' is the last argument, the script will remove the old output image directories and create new empty ones. NOTE: this removes the generated images locally, but they will still persist in the database. This will break the view command described below.
- Example commands:
	- ./run gen 1000 c
	- ./run bot c
	- ./run 50
	- ./run c

**Discord Bot Commands (Prefix: s!)**:
- help: Lists out basic descriptions for commands.
- gen: Generates a unique random slime. 30 minute cooldown.
- view <slime id>: Queries the slimes and replies with an embed containing the matching one if it exists.
- inv <optional: filter>: Shows a navigatable embed menu with reaction buttons to scroll through owned slimes. Given a filter, it will only show slimes you own that fit it.
	- The filter type matches the slime id. It must be 8 characters long. If a '.' is used in the filter it means that part can be anything.
		- Example: The filter '????????' functions the same as running with no filter. The filter '0??????0' will only return slimes with a 0 in the first and last slot and whatever else in the middle.
- trade <other user> <your slime> <their slime>: Offers a trade to a given user.
- reset_self: Completely resets your account. Mostly for testing, but maybe users want this ability?

**Credits**
- PhinalDestination: SlimeV2 pixel art.
- KingTenechi: Ideas and help with color verification.