import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button
import aiosqlite
import asyncio
import random
from PIL import Image, ImageDraw, ImageFont
import io
import datetime
import os

# Railway Variable se lega, nahi mila to niche wale se
TOKEN = os.getenv("TOKEN") or "YOUR_BOT_TOKEN_HERE"
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID") or "1553252269078907030")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="-", intents=intents)

async def init_db():
    async with aiosqlite.connect("ghostmc.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS invites (user_id INTEGER PRIMARY KEY, real INTEGER, fake INTEGER, left_inv INTEGER, bonus INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS tickets (channel_id INTEGER, user_id INTEGER, guild_id INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS autoresponder (guild_id INTEGER, trigger_word TEXT, response TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS giveaways (message_id INTEGER, channel_id INTEGER, end_time REAL, prize TEXT)")
        await db.commit()

def make_welcome_image(member):
    bg = Image.new('RGB', (1000, 400), (15, 15, 15))
    draw = ImageDraw.Draw(bg)
    draw.rectangle([(0,0),(1000,400)], outline=(0,255,100), width=8)
    draw.rectangle([(20,20),(980,380)], outline=(0,255,100), width=2)
    try:
        font_big = ImageFont.truetype("arial.ttf", 70)
        font_small = ImageFont.truetype("arial.ttf", 40)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    draw.text((50, 50), "WELCOME", fill=(0,255,100), font=font_big)
    draw.text((50, 140), f"{member.name}", fill=(255,255,255), font=font_big)
    draw.text((50, 250), f"TO GHOSTMC • YOU ARE {member.guild.member_count}TH MEMBER", fill=(180,180,180), font=font_small)
    draw.ellipse([(750, 100), (950, 300)], fill=(255,255,255))
    draw.text((800, 160), "👻", fill=(0,0,0), font=font_big)
    buffer = io.BytesIO()
    bg.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

@bot.event
async def on_ready():
    await init_db()
    print(f"Logged in as {bot.user} - GHOSTMC BOT Ready")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return
    img_buffer = make_welcome_image(member)
    file = discord.File(img_buffer, filename="welcome.png")
    embed = discord.Embed(
        title=f"Welcome to GHOSTMC, {member.name}! 👻",
        description=f"**Thanks for joining!**\n\n> Check <#rules> \n> Get roles in <#welcome>\n> Need help? Open ticket in <#support>\n\n**We now have {member.guild.member_count} members!**",
        color=0x00FF64
    )
    embed.set_image(url="attachment://welcome.png")
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="GHOSTMC • Best DC & MC Setups")
    await channel.send(content=f"{member.mention}", embed=embed, file=file)

@bot.command(name="info")
async def bot_info(ctx):
    embed = discord.Embed(title="GHOSTMC BOT • INFO", color=0x00FF64)
    embed.add_field(name="Servers", value=f"{len(bot.guilds)}")
    embed.add_field(name="Users", value=f"{len(set(bot.get_all_members()))}")
    embed.add_field(name="Ping", value=f"{round(bot.latency*1000)}ms")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

@bot.tree.command(name="say", description="Bot se kuch bulwao")
@app_commands.describe(message="Jo message bhejna hai", channel="Kis channel me bhejna hai")
async def say(interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("❌ No perms", ephemeral=True)
    ch = channel or interaction.channel
    await ch.send(message)
    await interaction.response.send_message(f"✅ Sent in {ch.mention}", ephemeral=True)

@bot.tree.command(name="status", description="Bot ka status change karo")
@app_commands.describe(type="playing/watching/listening", text="Status text")
@app_commands.choices(type=[
    app_commands.Choice(name="Playing", value="playing"),
    app_commands.Choice(name="Watching", value="watching"),
    app_commands.Choice(name="Listening", value="listening"),
])
async def status_cmd(interaction: discord.Interaction, type: str, text: str):
    if interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message("❌ Only owner can change status", ephemeral=True)
    if type == "playing":
        await bot.change_presence(activity=discord.Game(name=text))
    elif type == "watching":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))
    elif type == "listening":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=text))
    await interaction.response.send_message(f"✅ Status set to **{type} {text}**")

autoresponder_group = app_commands.Group(name="autoresponder", description="Autoresponder setup")

@autoresponder_group.command(name="add", description="Naya autoresponder add karo")
@app_commands.describe(trigger="Jis word pe reply de", response="Kya reply dena hai")
async def ar_add(interaction: discord.Interaction, trigger: str, response: str):
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ Manage Server perms chahiye", ephemeral=True)
    async with aiosqlite.connect("ghostmc.db") as db:
        await db.execute("INSERT INTO autoresponder VALUES (?,?,?)", (interaction.guild.id, trigger.lower(), response))
        await db.commit()
    await interaction.response.send_message(f"✅ Added autoresponder: `{trigger}` -> `{response}`", ephemeral=True)

@autoresponder_group.command(name="list", description="Saare autoresponder dekho")
async def ar_list(interaction: discord.Interaction):
    async with aiosqlite.connect("ghostmc.db") as db:
        async with db.execute("SELECT trigger_word, response FROM autoresponder WHERE guild_id=?", (interaction.guild.id,)) as cursor:
            rows = await cursor.fetchall()
    if not rows:
        return await interaction.response.send_message("Koi autoresponder nahi hai", ephemeral=True)
    desc = "\n".join([f"`{t}` -> {r}" for t,r in rows])
    embed = discord.Embed(title="Autoresponders", description=desc, color=0x00FF64)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@autoresponder_group.command(name="remove", description="Autoresponder hatao")
async def ar_remove(interaction: discord.Interaction, trigger: str):
    async with aiosqlite.connect("ghostmc.db") as db:
        await db.execute("DELETE FROM autoresponder WHERE guild_id=? AND trigger_word=?", (interaction.guild.id, trigger.lower()))
        await db.commit()
    await interaction.response.send_message(f"✅ Removed `{trigger}`", ephemeral=True)

bot.tree.add_command(autoresponder_group)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.guild:
        async with aiosqlite.connect("ghostmc.db") as db:
            async with db.execute("SELECT trigger_word, response FROM autoresponder WHERE guild_id=?", (message.guild.id,)) as cursor:
                async for trigger, response in cursor:
                    if trigger.lower() in message.content.lower():
                        await message.channel.send(response)
                        break
    await bot.process_commands(message)

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🎉 Join Giveaway", style=discord.ButtonStyle.green, custom_id="join_giveaway")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ You entered the giveaway!", ephemeral=True)

@bot.tree.command(name="giveaway", description="Giveaway start karo")
@app_commands.describe(prize="Kya prize hai", duration="Kitne minute me khatam hoga", winners="Kitne winners")
async def giveaway(interaction: discord.Interaction, prize: str, duration: int, winners: int = 1):
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("❌ No perms", ephemeral=True)
    end_time = datetime.datetime.now() + datetime.timedelta(minutes=duration)
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>\n\nClick the button to enter!", color=0x00FF64)
    embed.set_footer(text=f"Hosted by {interaction.user.name} • GHOSTMC")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    view = GiveawayView()
    await interaction.response.send_message("Giveaway started!")
    await interaction.channel.send(embed=embed, view=view)
    await asyncio.sleep(duration*60)
    users = [m async for m in interaction.channel.history(limit=100) if not m.author.bot]
    if users:
        winner = random.choice(users).author.mention
        await interaction.channel.send(f"🎉 Giveaway Ended! Prize: **{prize}**\nWinner: {winner} Congratulations!")
# --- INVITE TRACKER ---
@bot.command(name="I", aliases=["i"])
async def invites_cmd(ctx):
    async with aiosqlite.connect("ghostmc.db") as db:
        async with db.execute("SELECT real, fake, left_inv, bonus FROM invites WHERE user_id=?", (ctx.author.id,)) as cur:
            row = await cur.fetchone()
    if not row:
        real, fake, left, bonus = 0,0,0,0
    else:
        real, fake, left, bonus = row
    
    total = real + bonus - left
    embed = discord.Embed(title=f"📨 {ctx.author.name} - Invites", color=0x00FF64)
    embed.add_field(name="Real", value=str(real), inline=True)
    embed.add_field(name="Fake", value=str(fake), inline=True)
    embed.add_field(name="Left", value=str(left), inline=True)
    embed.add_field(name="Rejoin", value="0", inline=True)
    embed.add_field(name="Total", value=str(total), inline=True)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

# --- TICKET SYSTEM ---
class CloseView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button):
        await interaction.response.send_message("Ticket 5 sec me band ho jayega...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }
        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        embed = discord.Embed(title="Ticket Created", description=f"{interaction.user.mention} Staff yaha ayega, apna issue batao.", color=0x00FF64)
        await channel.send(embed=embed, view=CloseView())
        await interaction.response.send_message(f"Ticket created {channel.mention}", ephemeral=True)

@bot.tree.command(name="ticket", description="Ticket panel bhejo")
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="GHOSTMC Support", description="Neeche button dabao ticket kholne ke liye!")
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Panel sent!", ephemeral=True)

@bot.command(name="close")
async def close_cmd(ctx):
    if "ticket-" in ctx.channel.name:
        await ctx.send("Closing ticket...")
        await asyncio.sleep(2)
        await ctx.channel.delete()
    else:
        await ctx.send("Ye command sirf ticket channel me kaam karta hai!")
# INVITE LOG FIXED
INV_FILE = "invites.json"
LOG_FILE = "invite_log.json"

invites_data = {}
if os.path.exists(INV_FILE):
    invites_data = json.load(open(INV_FILE))

INVITE_CH = None
if os.path.exists(LOG_FILE):
    INVITE_CH = json.load(open(LOG_FILE)).get("channel_id")

invite_cache = {}

def save_inv():
    json.dump(invites_data, open(INV_FILE, "w"))

@bot.tree.command(name="inviteset", description="Is channel me logs ayenge")
async def inviteset_slash(interaction: discord.Interaction):
    global INVITE_CH
    INVITE_CH = interaction.channel.id
    json.dump({"channel_id": INVITE_CH}, open(LOG_FILE, "w"))
    await interaction.response.send_message(f"Logs yaha ayenge {interaction.channel.mention}", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    for g in bot.guilds:
        try:
            lst = await g.invites()
            d = {}
            for i in lst:
                d[i.code] = i.uses
            invite_cache[g.id] = d
        except:
            pass

@bot.event
async def on_member_join(member):
    try:
        new = await member.guild.invites()
        old = invite_cache.get(member.guild.id, {})
        for inv in new:
            if inv.uses > old.get(inv.code, 0):
                uid = str(inv.inviter.id)
                invites_data[uid] = invites_data.get(uid, 0) + 1
                save_inv()
                if INVITE_CH:
                    ch = member.guild.get_channel(INVITE_CH)
                    if ch:
                        msg = f"**{member.name} HAS BEEN INVITED BY {inv.inviter.name} | TOTAL: {invites_data[uid]}**"
                        await ch.send(msg)
                break
        d2 = {}
        for i in new:
            d2[i.code] = i.uses
        invite_cache[member.guild.id] = d2
    except:
        pass

TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)


