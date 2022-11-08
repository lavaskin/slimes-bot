# [Slimes! Discord Bot](https://slimes.lavask.in)

A discord bot where you can generate, trade and collect uniquely generated slimes! \
The bot has an econemy system, use s!claim to claim coins every hour and s!generate to create a slime!

### **Setting up Firebase/Firestore**
- Needed collections: 
  1. users
  1. users-dev
  1. ...
- In users and users-dev, create a document called "ranch" with the array fields: slimes, favs. This is where sold slimes will be added to.

### **How to build the bot**:
1. Fill out all the relevant information in a '.env' file. Use .env-example.txt as a reference.
1. Create an /other/firebase.json file from the json Firebase gives you on their site after you initialize a firestore database.
1. Run bot.py using python3 directly.
1. Note that I'm not going out of my way to support forks of the project so don't ask for help on setting it up.

### **Bot Commands (Prefix: s!)**:
See [this description file](https://github.com/Lavaskin/slimes-bot/blob/main/other/commands.json) as I'm too lazy to maintain two lists, or use s!help on the bot.

### **TODO**
There is a [Trello board](https://trello.com/invite/b/PQAkZuv1/9c4206afa51bd6153ae5931649f0bfd8/slimes) that I'm not paying to have an observer option on, but I usually make features I'm working on/planning known.

### **Credits**
- Art:
  - tutbot: SlimeV2 pixel art and various assets for slimes-bot.
  - [Holmesian](https://holmesian.carrd.co/ ): Tons of assets added in [this commit](https://github.com/Lavaskin/slimes-bot/commit/e0ab292ff4e4977a9c3004bfe95d3316373c5c93)!
- Testing:
  - Sinful Dante
  - Mr. Pt
  - tutbot
- Other:
  - KingTenechi: Ideas and help with color verification.
