import asyncio, discord, json, random, os, sys, hashlib
from discord.utils import get as disget
from datetime import datetime as dt

# global objects for the bot:discord.Client and db:dict
bot = discord.Client()
with open("db.json") as f: db:dict = json.load(f)

# database functions

def isval(uid:str, key:str):
    return True if db.get(uid) and db[uid].get(key) else False

def isgval(key:str):
    return True if db.get(key) else False

def setval(uid:str, key:str, val):
    if not db.get(uid): db[uid] = {}
    db[uid][key] = val

def setgval(key:str, val):
    db[key] = val

def addval(uid:str, key:str, val:int, start=0):
    if not db.get(uid): db[uid] = {}
    db[uid][key] = db[uid][key] + val if db[uid].get(key) else start + val

def addgval(key:str, val:int, start=0):
    db[key] += val if db.get(key) else start + val

def getval(uid:str, key:str, default):
    return db[uid].get(key, default) if db.get(uid) else default

def getgval(key:str, default):
    return db.get(key, default)

# define a function to automatically save our database in db.json
async def autosave():
    await bot.wait_until_ready()
    while not bot.is_closed:
        await asyncio.sleep(getgval("save-interval", 10))
        with open("db.json") as f: fstr = f.read()
        dbstr = json.dumps(db, separators=(",", ":"))
        if fstr == dbstr: continue # if file content == database content, sleep again
        print("Saving... ", end="")
        with open("db.json", "w") as f: f.write(dbstr)
        print("saved.")

@bot.event
async def on_ready():
    print("READDDYYYY!!!!1!!!")

@bot.event
async def on_message(msg):

    def cookiecheck(react:discord.Reaction, user:discord.User):
        return user != bot.user and str(react.emoji).startswith(u"\U0001F36A")

    def getuid(search:str):
        if search[:2] == "<@" and search[len(search)-1] == ">": return search[2:len(search)-1]
        user = disget(msg.server.members, name=search)
        if user: return user.id
        return None

    # store the current time and decide if any replies should show the response time
    time, timer = dt.now(), getgval("timer", False)

    # reply function, embed parameter is optional
    async def reply(content:str, dest:discord.Channel=msg.channel, embed:discord.Embed=None, fade:int=None):
        if timer: content += " (**" + str(int((dt.now()-time).total_seconds()*1000)) + "** ms)"
        sentmessage = await bot.send_message(dest, content, embed=embed)
        if fade:
            asyncio.sleep(fade)
            await bot.delete_message(sentmessage)
        else: return sentmessage

    # getting some values necessary for command handling and reply formatting
    uid = msg.author.id
    uname = msg.author.name
    pfx = getgval("prefix", ";")
    pfxlen = len(pfx)

    # logging
    print(str(time)[11:], end="| ")
    try: print(uname, end=": ")
    except: print(uid, end=": ")
    try: print(msg.content)
    except: print("[unprintable message]")

    # if message sent by bot or message too short for command, ignore
    if msg.author == bot.user or len(msg.content) <= pfxlen: return

    if random.random() < getgval("drop-chance", 0.3):
        drop = await reply("A cookie appeared! React with :cookie: to take it!")
        await bot.add_reaction(drop, u"\U0001F36A")
        result = await bot.wait_for_reaction(message=drop, check=cookiecheck)
        addval(result.user.id, "cookies", 1)
        await bot.edit_message(drop, f"`{result.user.name} took the cookie.`")
        await bot.clear_reactions(drop)

    # command processing, ignore if the message is not a command
    args = [s for s in msg.content[pfxlen:].split() if s != ""]\
             if msg.content[:pfxlen] == pfx\
             else None
    if not args: return
    cmd, args = args[0], args[1:]
    argstr = msg.content[pfxlen+len(cmd)+1:] if args else ""

    # commands
    if cmd == "status" and args:
        setval(uid, "status", argstr)

    elif cmd == "inew" and args:
        if isval("imageboard", args[0]):
            await reply("Tag already exists.", fade=5)
            return
        else:
            setval("imageboard", args[0], {})
            await reply("Tag created.", fade=5)

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
        await reply(f"{uname}, you have **{getval(uid, 'gold', 0)}**:large_orange_diamond:")

    elif cmd == "cookies":
        await reply(f"{uname}, you have **{getval(uid, 'cookies', 0)}** :cookie:.")

    elif cmd == "viru":
        await reply(random.choice(list(msg.server.members)).name + " is a binch <:grincat:399790921241067521>")

    elif cmd == "waifu":
        await bot.send_file(msg.channel, "./waifus/" + random.choice(os.listdir("./waifus")))

    # def check(msg): return msg.startswith(";pick")
    # usermessage = await bot.wait_for_message(author=msg.author)
    # if msg.content

    # admin commands
    elif uid in db["admins"]:
        if cmd in ("add", "addval", "set", "setval") and len(args) > 1:
            try:
                db[args[0]] = argstr[len(args[0])+1:]
                await reply("Value set.")
            except: await reply(f"Could not create key for arg: {args[0]}")

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
            except KeyError:
                await reply("Key not found.")

        if cmd in ("rst", "restart"):
            await reply("Restarting...")
            os.startfile(getgval("filepath", "C:\\Users\\Admin\\Documents\\Python\\bot\\bot.py"))
            await bot.logout()
            sys.exit(0)

# add the autosave function to the bot loop
bot.loop.create_task(autosave())
bot.run(db["token"])
