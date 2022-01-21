# Botty
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
	- gen: Creates a given amount of random NFT's. Default of 100. Also defaults to randomly picking between the 3 different types of NFT's included, but this can be changed by swapping the called function in main to something like genSlime().
- gen_amount is any integer. Dictates how many NFT's are created in gen mode.
- If 'c' is the last argument, the script will remove the old output image directories and create new empty ones. NOTE: this removes the generated images locally, but they will still persist in the database. This will break the view command described below.
- Example commands:
	- ./run gen 1000 c
	- ./run bot c
	- ./run 50
	- ./run c [Just removes old NFT's]

**Discord Bot Commands (Prefix: b!)**:
- help: Lists out basic descriptions for commands.
- gen <type [optional]>: Generates a random "NFT". Default generates a slime NFT and posts it. Given an optional argument of the type (dots, planets or slime), it will create that type instead.
- view <id>: Queries the slimes and replies with an embed containing the matching one if it exists.
- [WIP] inv: Shows a navigatable embed menu with reaction buttons to scroll through owned slimes.

**TODO**
- Timer for NFT generation.
- Database integration for "owning" an NFT
	- Trading with others
	- Viewing your owned NFT's
- Refactor NFT generation such that they're no longer saved locally, but instead only exist as an ID.
	- This entails needing to make slimes on-demand when b!view is used.
	- Saves on server storage space. Probably not as speed efficient.

**Credits**
- KingTenechi: Ideas and help with color verification.