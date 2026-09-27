import discord
from discord.ext import commands
from discord import app_commands
import json, os
COINS_FILE = "coins.json"
REDEEM_FILE = "redeemcodes.json"

def load_json(path):
    try:
        with open(path, "r") as f: return json.load(f)
    except: return {}

def save_json(path, data):
    with open(path, "w") as f: json.dump(f, data, indent=4)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.invites = True

bot = commands.Bot(command_prefix=["-", "."], intents=intents)

def load(name):
    path = f"{name}.json"
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except:
            return {}
    return {}

def save(name, data):
    json.dump(data, open(f"{name}.json", "w"), indent=4)

invites_cache = {}
invite_logs = {} # guild_id -> log channel id

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")
    for g in bot.guilds:
        try:
            invs = await g.invites()
            invites_cache[g.id] = {i.code: i.uses for i in invs}
        except:
            pass
    try:
        await bot.tree.sync()
    except:
        pass

# 1. WELCOMESET
@bot.tree.command(name="welcomeset", description="Welcome channel set karo")
async def welcomeset(interaction: discord.Interaction, channel: discord.TextChannel):
    data = load("welcome")
    data[str(interaction.guild.id)] = channel.id
    save("welcome", data)
    await interaction.response.send_message(f"✅ Welcome set: {channel.mention}", ephemeral=True)

# 2. INVITESET
@bot.tree.command(name="inviteset", description="Invite log channel")
async def inviteset(interaction: discord.Interaction, channel: discord.TextChannel):
    data = load("invites")
    if "logs" not in data:
        data["logs"] = {}
    data["logs"][str(interaction.guild.id)] = channel.id
    save("invites", data)
    await interaction.response.send_message(f"✅ Invite log set: {channel.mention}", ephemeral=True)

# 3. LEFTSET
@bot.tree.command(name="leftset", description="Left channel set")
async def leftset(interaction: discord.Interaction, channel: discord.TextChannel):
    data = load("left")
    data[str(interaction.guild.id)] = channel.id
    save("left", data)
    await interaction.response.send_message(f"✅ Left set: {channel.mention}", ephemeral=True)

@bot.event
async def on_member_join(member):
    if member.bot:
        return

    # WELCOME
    w_data = load("welcome")
    w_ch_id = w_data.get(str(member.guild.id))
    if w_ch_id:
        ch = member.guild.get_channel(w_ch_id)
        if ch:
            desc = f"🔥 WELCOME TO **GHOSTMC CLOUD** 👻\n\n👋 Hey {member.mention}!!\n✨ GREAT TO HAVE YOU HERE!!"
            embed = discord.Embed(description=desc, color=0x2b2d31)
            embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await ch.send(content=f"🎉 WELCOME {member.mention} TO **{member.guild.name}**!!!", embed=embed)
            except:
                pass

    # INVITE TRACK
    try:
        new_invs = await member.guild.invites()
        old = invites_cache.get(member.guild.id, {})
        inviter = None
        for inv in new_invs:
            if inv.code in old and inv.uses > old[inv.code]:
                inviter = inv.inviter
                break

        invites_cache[member.guild.id] = {i.code: i.uses for i in new_invs}

        if inviter:
            gid = str(member.guild.id)
            uid = str(inviter.id)

            days_old = (discord.utils.utcnow() - member.created_at).days
            is_fake = days_old < 30

            data = load("invites")
            if gid not in data or not isinstance(data[gid], dict):
                data[gid] = {}

            # logs key ko alag rakho
            clean_data = {k:v for k,v in data.items() if k!= "logs"}
            if gid not in clean_data:
                clean_data[gid] = {}

            if not is_fake:
                if uid not in clean_data[gid]:
                    clean_data[gid][uid] = 0
                clean_data[gid][uid] += 1

            if "logs" in data:
                clean_data["logs"] = data["logs"]
            save("invites", clean_data)

            log_ch_id = clean_data.get("logs", {}).get(gid)
            if log_ch_id:
                log_ch = member.guild.get_channel(log_ch_id)
                if log_ch:
                    count = clean_data[gid].get(uid, 0)
                    tag = "❌ Fake" if is_fake else "✅ Real"
                    await log_ch.send(f"📨 **{member.name}** HAS BEEN INVITED BY **{inviter.name}** | TOTAL: {count} {tag}")
    except Exception as e:
        print(f"Invite Error: {e}")

@bot.event
async def on_member_remove(member):
    l_data = load("left")
    ch_id = l_data.get(str(member.guild.id))
    if ch_id:
        ch = member.guild.get_channel(ch_id)
        if ch:
            text = f"""👋 Bye bro {member.mention}!!

Asha karta hu wapis ayega kyuki aisi achi community nahi milegi 💙
Yaha regularly giveaways / events hote hai.

Agar kuch pasand nahi aaya to ticket me bata deta,
Agar koi bug / report hai to wo bhi ticket me bata deta,
Par aise bina bataye leave kyu kara? 😔

Wapas ka intezaar rahega! 👻"""
            try:
                await ch.send(text)
            except:
                pass

# 4. TICKET
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.blurple, custom_id="ticket_btn")
    async def ticket_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True)
        }
        channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        await channel.send(f"{interaction.user.mention} Apna issue yaha batao!")
        await interaction.response.send_message(f"Ticket bana: {channel.mention}", ephemeral=True)

@bot.tree.command(name="ticket", description="Ticket panel bhejo")
async def ticket_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 GHOSTMC SUPPORT", description="Support chahiye? Button dabao!", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Panel bhej diya ✅", ephemeral=True)

# 5. SAY
@bot.tree.command(name="say", description="Bot se bulwao")
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("Bhej diya ✅", ephemeral=True)
    await interaction.channel.send(message)

# 6. STATUS
@bot.command(name="status")
async def status_cmd(ctx, *, text: str):
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(f"✅ Status: {text}")

# 7. ICON
@bot.tree.command(name="icon", description="Server icon")
async def icon_cmd(interaction: discord.Interaction):
    if not interaction.guild.icon:
        await interaction.response.send_message("❌ Icon nahi hai", ephemeral=True)
        return
    embed = discord.Embed(title=interaction.guild.name, color=0x2b2d31)
    embed.set_image(url=interaction.guild.icon.url)
    await interaction.response.send_message(embed=embed)

# 8. I / -I
@bot.command(name="i", aliases=["I", "inv", "invites"])
async def invite_check(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load("invites")
    real = data.get(str(ctx.guild.id), {}).get(str(member.id), 0) if isinstance(data.get(str(ctx.guild.id)), dict) else 0

    embed = discord.Embed(title="📨・INVITE STATS", description=f"👤 {member.mention}", color=0x2b2d31)
    embed.add_field(name="✅ Real", value=f"**{real}**", inline=True)
    embed.add_field(name="❌ Fake", value="**0**", inline=True)
    embed.add_field(name="👋 Left", value="**0**", inline=True)
    embed.add_field(name="🔄 Rejoin", value="**0**", inline=True)
    embed.add_field(name="📊 Total", value=f"**{real}**", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="GhostMc • Invite Tracker")
    await ctx.send(embed=embed)
    # --- FINAL LEVEL SYSTEM ---

if os.path.exists("levels.json"):
    with open("levels.json", "r") as f:
        try: levels = json.load(f)
        except: levels = {}
else: levels = {}

if os.path.exists("level_config.json"):
    with open("level_config.json", "r") as f:
        try: level_channels = json.load(f)
        except: level_channels = {}
else: level_channels = {}

def save_levels():
    with open("levels.json", "w") as f: json.dump(levels, f, indent=2)
def save_level_channels():
    with open("level_config.json", "w") as f: json.dump(level_channels, f, indent=2)
def get_level(xp):
    return math.floor(0.1 * math.sqrt(xp))

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    key = f"{message.guild.id}_{message.author.id}"
    if key not in levels: levels[key] = {"xp": 0, "level": 0}
    levels[key]["xp"] += random.randint(15, 25)
    new_level = get_level(levels[key]["xp"])
    if new_level > levels[key]["level"]:
        levels[key]["level"] = new_level
        gid = str(message.guild.id)
        # jaha /levelup-set kiya hai wahi bhejega
        if gid in level_channels:
            ch = bot.get_channel(level_channels[gid])
            if ch: await ch.send(f"GG {message.author.mention} tu **Level {new_level}** pe pahunch gaya! 🔥")
        else:
            await message.channel.send(f"GG {message.author.mention} tu **Level {new_level}** pe pahunch gaya! 🔥")
    save_levels()
    await bot.process_commands(message)

@bot.tree.command(name="levelup-set", description="Jaha ye likhoge wahi level up message ayega")
async def levelup_set(interaction: discord.Interaction):
    level_channels[str(interaction.guild.id)] = interaction.channel.id
    save_level_channels()
    await interaction.response.send_message(f"Done! ✅ Ab se level up message yahi ayega: {interaction.channel.mention}")
# --- AUTOROLE + GIVEAWAY SYSTEM ---

import asyncio
import datetime

# --- AUTOROLE CONFIG ---
if os.path.exists("autorole.json"):
    with open("autorole.json", "r") as f:
        try: autorole_config = json.load(f)
        except: autorole_config = {}
else: autorole_config = {}

def save_autorole():
    with open("autorole.json", "w") as f: json.dump(autorole_config, f, indent=2)

@bot.tree.command(name="autorole-set", description="Join par auto role dega")
async def autorole_set(interaction: discord.Interaction, role: discord.Role):
    autorole_config[str(interaction.guild.id)] = role.id
    save_autorole()
    await interaction.response.send_message(f"Done! ✅ Ab {role.mention} auto milega join par.", ephemeral=True)

# Welcome + AutoRole ek hi event me
@bot.event
async def on_member_join(member):
    # 1. AutoRole
    gid = str(member.guild.id)
    if gid in autorole_config:
        role = member.guild.get_role(autorole_config[gid])
        if role:
            try: await member.add_roles(role)
            except: pass

    # 2. Welcome (tera purana welcome code yaha rahega)
    if gid in welcome_channels:
        ch = bot.get_channel(welcome_channels[gid])
        if ch:
            embed = discord.Embed(description=f"Welcome {member.mention} to **{member.guild.name}**!", color=0x2b2d31)
            await ch.send(embed=embed)

@bot.event
async def on_member_remove(member):
    gid = str(member.guild.id)
    if gid in welcome_channels:
        ch = bot.get_channel(welcome_channels[gid])
        if ch:
            await ch.send(f"**{member.name}** left the server. 😢")

# --- GIVEAWAY SYSTEM ---
class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.users = []

    @discord.ui.button(label="🎉 Join", style=discord.ButtonStyle.green, custom_id="giveaway_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.users:
            self.users.append(interaction.user.id)
            await interaction.response.send_message("Tu giveaway me join ho gaya! 🎉", ephemeral=True)
        else:
            await interaction.response.send_message("Tu pehle se joined hai!", ephemeral=True)

@bot.tree.command(name="giveaway", description="Giveaway start karo")
async def giveaway(interaction: discord.Interaction, prize: str, winners: int, minutes: int):
    view = GiveawayView()
    end_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>\n\nNeeche button dabao join karne ke liye!", color=0xFFD700)
    await interaction.response.send_message(embed=embed, view=view)

    await asyncio.sleep(minutes * 60)

    if len(view.users) == 0:
        await interaction.followup.send("Koi join nahi hua 😢")
        return

    win_list = random.sample(view.users, min(winners, len(view.users)))
    mentions = ", ".join([f"<@{uid}>" for uid in win_list])
    await interaction.followup.send(f"Congratulations {mentions}! Tum jeet gaye **{prize}**! 🎉")
# ===== OWO SYSTEM - DYNAMIC SET =====
import random, json, os
OWO_FILE = "owo_data.json"
OWO_CHANNEL_FILE = "owo_channels.json"

if not os.path.exists(OWO_FILE):
    with open(OWO_FILE, "w") as f: json.dump({}, f)
if not os.path.exists(OWO_CHANNEL_FILE):
    with open(OWO_CHANNEL_FILE, "w") as f: json.dump([], f)

def get_owo_data():
    with open(OWO_FILE, "r") as f: return json.load(f)
def save_owo_data(data):
    with open(OWO_FILE, "w") as f: json.dump(data, f, indent=4)
def get_owo_channels():
    with open(OWO_CHANNEL_FILE, "r") as f: return json.load(f)

def is_owo_channel():
    async def predicate(interaction: discord.Interaction):
        channels = get_owo_channels()
        if interaction.channel.id not in channels:
            await interaction.response.send_message(f"❌ Is channel me OWO set nahi hai! Pehle yaha `/owoset` likho.", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate)

@bot.tree.command(name="owoset", description="Is channel me OWO on karo")
@discord.app_commands.checks.has_permissions(administrator=True)
async def owoset(interaction: discord.Interaction):
    channels = get_owo_channels()
    if interaction.channel.id not in channels:
        channels.append(interaction.channel.id)
        with open(OWO_CHANNEL_FILE, "w") as f: json.dump(channels, f)
        await interaction.response.send_message(f"✅ OWO system is channel me SET ho gaya! Ab yaha `/hunt` chalega.")
    else:
        await interaction.response.send_message(f"✅ Pehle se hi set hai yaha!")

@bot.tree.command(name="owounset", description="Is channel se OWO hatao")
@discord.app_commands.checks.has_permissions(administrator=True)
async def owounset(interaction: discord.Interaction):
    channels = get_owo_channels()
    if interaction.channel.id in channels:
        channels.remove(interaction.channel.id)
        with open(OWO_CHANNEL_FILE, "w") as f: json.dump(channels, f)
        await interaction.response.send_message(f"❌ OWO system hata diya is channel se.")
    else:
        await interaction.response.send_message(f"Yaha pe set hi nahi tha!")

@bot.tree.command(name="hunt", description="Hunt animals like OWO")
@is_owo_channel()
async def hunt(interaction: discord.Interaction):
    data = get_owo_data()
    uid = str(interaction.user.id)
    animals = ["🦌 Deer", "🐰 Bunny", "🐺 Wolf", "🐻 Bear", "🦊 Fox", "🐯 Tiger"]
    found = random.choice(animals)
    if uid not in data: data[uid] = {"cash": 0, "zoo": []}
    data[uid]["zoo"].append(found)
    data[uid]["cash"] += random.randint(10, 50)
    save_owo_data(data)
    await interaction.response.send_message(f"You hunted and found **{found}**!")

@bot.tree.command(name="battle", description="Battle and earn cash")
@is_owo_channel()
async def battle(interaction: discord.Interaction):
    data = get_owo_data()
    uid = str(interaction.user.id)
    if uid not in data: data[uid] = {"cash": 0, "zoo": []}
    earn = random.randint(20, 100)
    data[uid]["cash"] += earn
    save_owo_data(data)
    await interaction.response.send_message(f"You won! +{earn} cowoncy ⚔️")

@bot.tree.command(name="zoo", description="Check your zoo")
@is_owo_channel()
async def zoo(interaction: discord.Interaction):
    data = get_owo_data()
    uid = str(interaction.user.id)
    zoo_list = data.get(uid, {}).get("zoo", [])
    await interaction.response.send_message(f"**Zoo:**\n" + "\n".join(zoo_list[-20:]) if zoo_list else "Zoo khali hai!")

@bot.tree.command(name="cash", description="Check your cash")
@is_owo_channel()
async def cash(interaction: discord.Interaction):
    data = get_owo_data()
    bal = data.get(str(interaction.user.id), {}).get("cash", 0)
    await interaction.response.send_message(f"💰 You have **{bal} cowoncy**")
    
@bot.tree.command(name="redeemcodecreate", description="Naya redeem code banao")
@app_commands.describe(code="Code naam jaise GHOSTMC", coins="Kitne coins milenge", max_use="Kitne log use kar sakte hai")
async def redeemcodecreate(interaction: discord.Interaction, code: str, coins: int, max_use: int = 100):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Only Admin can use!", ephemeral=True)
    db = load_json(REDEEM_FILE)
    code = code.upper()
    db[code] = {"coins": coins, "max_use": max_use, "used_by": [], "uses": 0}
    save_json(REDEEM_FILE, db)
    await interaction.response.send_message(f"✅ Code Created: **{code}** = {coins} Coins | Max: {max_use}")


@bot.tree.command(name="redeem", description="Code redeem karo")
async def redeem(interaction: discord.Interaction, code: str):
    code = code.upper()
    rdb = load_json(REDEEM_FILE)
    cdb = load_json(COINS_FILE)
    if code not in rdb:
        return await interaction.response.send_message("❌ Invalid code!", ephemeral=True)
    d = rdb[code]
    if interaction.user.id in d["used_by"]:
        return await interaction.response.send_message("❌ Tu already redeem kar chuka hai!", ephemeral=True)
    if d["uses"] >= d["max_use"]:
        return await interaction.response.send_message("❌ Code expire ho gaya!", ephemeral=True)
    uid = str(interaction.user.id)
    cdb[uid] = cdb.get(uid, 0) + d["coins"]
    d["used_by"].append(interaction.user.id)
    d["uses"] += 1
    save_json(REDEEM_FILE, rdb)
    save_json(COINS_FILE, cdb)
    await interaction.response.send_message(f"🎉 Redeemed! Tujhe **{d['coins']} Coins** mil gaye!")

@bot.tree.command(name="addcoins", description="Kisi ko coins do")
async def addcoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator: return
    db = load_json(COINS_FILE)
    db[str(member.id)] = db.get(str(member.id), 0) + amount
    save_json(COINS_FILE, db)
    await interaction.response.send_message(f"✅ {member.mention} ko {amount} coins diye. Total: {db[str(member.id)]}")

@bot.tree.command(name="removecoins", description="Kisi ke coins hatao")
async def removecoins(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator: return
    db = load_json(COINS_FILE)
    db[str(member.id)] = max(0, db.get(str(member.id), 0) - amount)
    save_json(COINS_FILE, db)
    await interaction.response.send_message(f"✅ {member.mention} se {amount} coins hata diye. Bache: {db[str(member.id)]}")

@bot.tree.command(name="coins", description="Apne coins check karo")
async def coins_cmd(interaction: discord.Interaction):
    db = load_json(COINS_FILE)
    bal = db.get(str(interaction.user.id), 0)
    await interaction.response.send_message(f"💰 Tere paas **{bal} Coins** hai.")

@bot.tree.command(name="shop", description="Coin shop dekho")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 GhostMC Coin Shop", color=0x9b59b6)
    embed.add_field(name="400 Coins", value="= 40K In-Game Money", inline=False)
    embed.add_field(name="600 Coins", value="= 70K In-Game Money", inline=False)
    embed.add_field(name="800 Coins", value="= 90K In-Game Money", inline=False)
    embed.add_field(name="1600 Coins", value="= 200K In-Game Money", inline=False)
    embed.add_field(name="2000 Coins", value="= VIP RANK", inline=False)
    embed.add_field(name="\u200b", value="**Make ticket to exchange** 🎫", inline=False)
    await interaction.response.send_message(embed=embed)

bot.run(os.getenv("TOKEN"))
