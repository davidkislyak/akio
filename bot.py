import asyncio, discord, json, random, re, os, sys, hashlib
from discord.utils import get as disget
from datetime import datetime as dt
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

# global objects for the bot:discord.Client, db:dict, and fstr:str
bot = discord.Client()
with open("db.json") as f: db, fstr = json.load(f), f.read()

# a smol code that retrieves html content from urls
def gethtml(url:str):
    return BeautifulSoup(urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'})), "html.parser")

# user data management functions
def isval(uid:str, key:str):
    return True if db.get(uid) and db[uid].get(key) else False

def setval(uid:str, key:str, val):
    if not db.get(uid): db[uid] = {}
    db[uid][key] = val

def addval(uid:str, key:str, val:int, start=0):
    if not db.get(uid): db[uid] = {}
    db[uid][key] = db[uid][key] + val if db[uid].get(key) else start + val

def getval(uid:str, key:str, default):
    return db[uid].get(key, default) if db.get(uid) else default

# I have decided that global value functions are unnecessary since they are at the root of the database
# just use the db.get(key, default) and db[key] = val syntax for getting and setting global values

# a function that gets added as a bot loop task to automatically save the database to db.json
async def autosave():
    await bot.wait_until_ready()
    while not bot.is_closed:
        await asyncio.sleep(db.get("save-interval", 10))
        await save()

# database save function
async def save(andexit=False):
    global db, fstr
    dbstr:str = json.dumps(db, separators=(",", ":"))

    # if database content differs from last saved file content, save database content to db.json
    if dbstr != fstr:
        print("[.] Saving...")
        with open("db.json", "w") as f:
            f.write(dbstr)
            fstr = dbstr
        print("[-] Saved.")

    if andexit: sys.exit(0)

@bot.event
async def on_ready():
    print("[-] Ready.")

@bot.event
async def on_message(msg):

    # prepping some variables for replying to users, verifying commands, initializing 
    uid, uname, nname = msg.author.id, msg.author.name, msg.author.display_name
    pfx = db.get("prefix", ";")
    pfxlen = len(pfx)
    time, replytime = dt.now(), db.get("replytime", False)

    # check function to use on cookie reaction events
    def cookiecheck(react:discord.Reaction, user:discord.User):
        return user != bot.user and str(react.emoji).startswith(u"\U0001F36A")

    # searches a string for an ping and parses it
    # if it doesn't find one, searches members for a matching name
    def getuid(search:str):
        if search[:2] == "<@" and search[len(search)-1] == ">": return search[2:len(search)-1]
        user = disget(msg.server.members, name=search)
        if user: return user.id
        return None

    # reply function, embed parameter is optional, fade will delete messages after a certain amount of time
    async def reply(content:str, dest:discord.Channel=msg.channel, embed:discord.Embed=None, fade:int=None):
        if replytime: content += " (**" + str(int((dt.now()-time).total_seconds()*1000)) + "** ms)"
        sentmessage = await bot.send_message(dest, content, embed=embed)
        if fade:
            asyncio.sleep(fade)
            await bot.delete_message(sentmessage)
        else: return sentmessage

    # logging messages (not currently limiting to specific channels)
    print(str(time)[11:], end=" | ")
    try: print(uname, end=": ")
    except: print(uid, end=": ")
    try: print(str(msg.content)) # .encode("utf-8")
    except: print("[unprintable message]")

    # if the message was sent by the bot or the message is too short to be a command, exit this event
    if msg.author == bot.user or len(msg.content) <= pfxlen: return

    # process the command and args into a list
    cmdwithargs = [s for s in msg.content[pfxlen:].split() if s != ""]\
             if msg.content[:pfxlen] == pfx\
             else None

    # if the message is not a command
    if not cmdwithargs:
        # do non-command logic here!
        if random.random() < db.get("drop-chance", 0.03):
            drop = await reply("A cookie appeared! React with :cookie: to take it!")
            await bot.add_reaction(drop, u"\U0001F36A")
            result = await bot.wait_for_reaction(message=drop, check=cookiecheck)
            addval(result.user.id, "cookies", 1)
            await bot.edit_message(drop, f"`{result.user.display_name} took the cookie.`")
            await bot.clear_reactions(drop)

        return # since the message is not a command, exit this event

    # now for the command stuff,
    # break apart the command and the command arguments
    cmd, args = cmdwithargs[0], cmdwithargs[1:]
    # represent the list of arguments as a string as well (it's shit code i know)
    argstr = msg.content[pfxlen+len(cmd)+1:] if args else ""

    # finally, COMMANDS
    if cmd == "status" and args:
        setval(uid, "status", argstr)

    elif cmd in ("dbr", "danbooru"):
        page, tags = "1", ""
        for arg in args:
            if arg.isdigit(): page = int(arg)
            else: tags += arg + "+"
        try:
            await reply(gethtml("https://danbooru.donmai.us"+random.choice(gethtml(f"https://danbooru.donmai.us/posts?page={page}&tags={tags}").findAll("a",{'href':re.compile("/posts/\\d{7}$")})).get("href")).find("img",{"id":"image"}).get("src"))
        except Exception as e: print(e)

    elif cmd in ("uwo", "owu"):
        this = await bot.send_message(msg.channel, "uwo")
        states = ("owu", "uwo")
        for x in range(3):
            for state in states:
                await asyncio.sleep(0.75)
                await bot.edit_message(this, new_content=state)

    elif cmd in ("type", "typewriter") and args:
        this = await bot.send_message(msg.channel, argstr[0])
        for x in range(2, len(argstr)+1):
            await asyncio.sleep(0.5)
            await bot.edit_message(this, new_content=argstr[:x])

    elif cmd == "uid" and args:
        result = getuid(argstr)
        if not result: result = "UID not found."
        await reply(result)

    elif cmd == "mine":
        gold = random.randint(1, 100)
        addval(uid, "gold", gold)
        await reply(f"{uname}, you got **{gold}** gold.")

    elif cmd == "love" and len(args) == 2:
        char = hashlib.md5(args[0].encode("ascii")).hexdigest()[0]
        char2 = hashlib.md5(args[1].encode("ascii")).hexdigest()[0]
        #print(f"adding hash chars: {char} + {char2}")
        lovemeter = int((int(char, 16) + int(char2, 16)) / 3.0 * 10)
        await reply(f"Love meter: **{lovemeter}**%")

    elif cmd == "bal":
        await reply(f"{nname}, you have **{getval(uid, 'gold', 0)}**:large_orange_diamond:")

    elif cmd == "cookies":
        await reply(f"{nname}, you have **{getval(uid, 'cookies', 0)}** :cookie:.")

    elif cmd == "viru":
        await reply(random.choice(list(msg.server.members)).name + " is a binch <:grincat:399790921241067521>")

    elif cmd == "waifu":
        await bot.send_file(msg.channel, "./waifus/" + random.choice(os.listdir("./waifus")))

    # admin commands
    elif uid in db.get("admins", ["206896737934114819"]):
        if cmd in ("add", "addval", "set", "setval") and len(args) > 1:
            try:
                db[args[0]] = argstr[len(args[0])+1:]
                await reply("Value set.")
            except Exception as e:
                await reply(f"An error occured when saving value: {args[0]}")
                print(e)

        if cmd in ("data", "global", "globals"):
            gdb = {k: v for k, v in db.items() if (not k.isdigit() or len(k) != 18) and k != "token"}
            await reply(f"```json\n{json.dumps(gdb, indent=4, sort_keys=True)}\n```")

        if cmd in ("userdata", "udata", "users"):
            udb = {k: v for k, v in db.items() if k.isdigit() and len(k) == 18}
            await reply(f"```json\n{json.dumps(udb, indent=4, sort_keys=True)}\n```")

        if cmd in ("remove", "del", "delval", "delete") and args:
            try:
                if len(args) > 1:
                    del db[args[0]][args[1]]
                    await reply(f"Key {args[1]} was deleted for user with id: {args[0]}")
                else:
                    del db[args[0]]
                    await reply(f"Key {args[1]} deleted.")
            except KeyError as e:
                await reply("Key not found.")
                print(e)

        # if cmd in ("rst", "restart"):
        #     await reply("Restarting...")
        #     os.startfile(getgval("filepath", "C:\\Users\\Admin\\Documents\\GitHub\\akio\\bot.py"))
        #     sys.exit(0)

try:
    # add the autosave function to the bot loop
    bot.loop.create_task(autosave())
    bot.loop.run_until_complete(bot.start(db["token"]))
except KeyboardInterrupt:
    bot.loop.run_until_complete(save(andexit=True))