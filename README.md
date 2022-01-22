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
	- gen: Creates a given amount of random NFT's. Default of 100. Useful for testing out generation code.
- gen_amount is any integer. Dictates how many NFT's are created in gen mode.
- If 'c' is the last argument, the script will remove the old output image directories and create new empty ones. NOTE: this removes the generated images locally, but they will still persist in the database. This will break the view command described below.
- Example commands:
	- ./run gen 1000 c
	- ./run bot c
	- ./run 50
	- ./run c [Just removes old NFT's]

**Discord Bot Commands (Prefix: s!)**:
- help: Lists out basic descriptions for commands.
- gen: Generates a random "NFT" slime. 30 minute cooldown.
- view <id>: Queries the slimes and replies with an embed containing the matching one if it exists.
- [WIP] inv: Shows a navigatable embed menu with reaction buttons to scroll through owned slimes.

**TODO**
- Trading slimes with other people
- Viewing all your owned slimes in a navigatable embed
- Refactor NFT generation such that they're no longer saved locally, but instead only exist as an ID.
	- This entails needing to make slimes on-demand when s!view is used.
	- Saves on server storage space. Probably not as speed efficient.

**Credits**
- KingTenechi: Ideas and help with color verification.