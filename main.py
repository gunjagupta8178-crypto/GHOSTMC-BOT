import discord
from discord.ext import commands
import json, os

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

bot.run(os.getenv("TOKEN"))
