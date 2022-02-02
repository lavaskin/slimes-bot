# slimes-bot
*By Lavaskin*

**How to use**:
1. Fill out all the relevant information in a '.env' file.
2. Create an /other/firebase.json file from the json Firebase gives you on their site after you initialize a firestore database.
1. Run bot.py using python3 directly.

**Bot Commands (Prefix: s!)**:
- help: Lists out basic descriptions for commands.
- gen: Generates a unique random slime. 30 minute cooldown.
- view <slime id>: Queries the slimes and replies with an embed containing the matching one if it exists.
- inv <optional: filter>: Shows a navigatable embed menu with reaction buttons to scroll through owned slimes. Given a filter, it will only show slimes you own that fit it.
	- The filter type matches the slime id. It must be 8 characters long. If a '.' is used in the filter it means that part can be anything.
		- Example: The filter '????????' functions the same as running with no filter. The filter '0??????0' will only return slimes with a 0 in the first and last slot and whatever else in the middle.
- trade <other user> <your slime> <their slime>: Offers a trade to a given user.
- reset_self: Completely resets your account. Mostly for testing, but maybe users want this ability?
- fav <slime id>: Adds a given slime to your favorites (Max of 9)
- favs <optional: clear>: Creates a collage of all favorited slimes. If optional argument is given (clear/c), wipes all favorites.

**Credits**
- PhinalDestination: SlimeV2 pixel art.
- KingTenechi: Ideas and help with color verification.