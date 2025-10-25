import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import re
from datetime import timedelta
import os
from dotenv import load_dotenv

# --- Token betöltése .env fájlból ---
load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Beállítások ---
TICKET_CATEGORY_ID = 1429187595388325979
LOG_CHANNEL_ID = 1429397051090669568
INVITE_ALLOWED_CATEGORY_ID = 1429187595388325979
INVITE_EXEMPT_USER_ID = 826753238392111106

# --- Tárolók rangokhoz ---
ping_role = {}
rping_role = {}
ticket_visible_role = {}

# --- Ticket lezáró gomb ---
class CloseTicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket lezárása", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 A ticket 5 másodpercen belül lezárul...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- Félautomata partnerség embed ---
def create_partnership_embed(user: discord.Member):
    embed = discord.Embed(
        title="🤝 Félautomata partnerség",
        description=(
            f"Üdv {user.mention}!\n\n"
            "**1.** Küldd el a partnerségi szöveget!\n"
            "**2.** Csatolj képet bizonyítékként!\n\n"
            "⏰ *10 perced van mindkét lépésre!*"
        ),
        color=discord.Color.blue()
    )
    return embed

# --- Ticket gombok ---
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Félautomata Partnerség", style=discord.ButtonStyle.primary)
    async def partnership_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY_ID)
        rping = rping_role.get(guild.id)
        visible_role = ticket_visible_role.get(guild.id)

        existing = discord.utils.get(guild.text_channels, name=f"partner-{user.name.lower()}")
        if existing:
            await interaction.response.send_message(f"Már van nyitott ticketed: {existing.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if visible_role:
            overwrites[visible_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(f"partner-{user.name}", overwrites=overwrites, category=category)
        embed = create_partnership_embed(user)
        await channel.send(embed=embed, view=CloseTicketButton())
        if rping:
            await channel.send(f"{rping.mention}")

        await interaction.response.send_message(f"Ticket létrehozva: {channel.mention}", ephemeral=True)

        # Automatikus lezárás 10 perc inaktivitás után
        def check(m): return m.channel == channel and m.author == user
        try:
            await bot.wait_for("message", check=check, timeout=600)
        except asyncio.TimeoutError:
            await channel.send("⌛ Lejárt a 10 perc, lezárás...")
            await asyncio.sleep(5)
            await channel.delete()

    @discord.ui.button(label="❓Kérdés", style=discord.ButtonStyle.secondary)
    async def question_ticket(self, interaction: discord.Interaction, button: Button):
        await self.create_ticket(interaction, "kerdes")

    @discord.ui.button(label="👾TGF", style=discord.ButtonStyle.success)
    async def tgf_ticket(self, interaction: discord.Interaction, button: Button):
        await self.create_ticket(interaction, "tgf")

    @discord.ui.button(label="🛡️Help", style=discord.ButtonStyle.danger)
    async def help_ticket(self, interaction: discord.Interaction, button: Button):
        await self.create_ticket(interaction, "help")

    async def create_ticket(self, interaction: discord.Interaction, type_name: str):
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY_ID)
        ping = ping_role.get(guild.id)
        visible_role = ticket_visible_role.get(guild.id)

        existing = discord.utils.get(guild.text_channels, name=f"{type_name}-{user.name.lower()}")
        if existing:
            await interaction.response.send_message(f"Már van nyitott ticketed: {existing.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if visible_role:
            overwrites[visible_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(f"{type_name}-{user.name}", overwrites=overwrites, category=category)
        await channel.send(f"Üdv {user.mention}! {ping.mention if ping else ''} itt segítenek neked 💬", view=CloseTicketButton())
        await interaction.response.send_message(f"Ticket létrehozva: {channel.mention}", ephemeral=True)

# --- Rangok parancsok ---
@bot.command()
async def ping(ctx, role: discord.Role):
    ping_role[ctx.guild.id] = role
    await ctx.send(f"✅ `ping` rang beállítva: {role.mention}")

@bot.command()
async def rping(ctx, role: discord.Role):
    rping_role[ctx.guild.id] = role
    await ctx.send(f"✅ `rping` rang beállítva: {role.mention}")

@bot.command()
async def role(ctx, role: discord.Role):
    ticket_visible_role[ctx.guild.id] = role
    await ctx.send(f"✅ Ticket látható rang beállítva: {role.mention}")

# --- Ticket panel parancs ---
@bot.tree.command(name="ticketpanel", description="Ticket panel küldése")
async def ticketpanel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Ticket rendszer",
        description="Válassz a lenti gombok közül a megfelelő opcióhoz:",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=TicketView())

# --- Invite link védelem + log ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    invite_pattern = r"(discord\.gg/|discord\.com/invite/)"
    if re.search(invite_pattern, message.content, re.IGNORECASE):
        if (
            message.author.id != INVITE_EXEMPT_USER_ID and
            (not message.channel.category or message.channel.category.id != INVITE_ALLOWED_CATEGORY_ID)
        ):
            try:
                await message.delete()
                await message.author.edit(timeout=discord.utils.utcnow() + timedelta(minutes=10), reason="Tiltott invite link")

                log_channel = message.guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(title="🚫 Invite link törölve", color=discord.Color.red())
                    embed.add_field(name="Felhasználó", value=f"{message.author.mention} ({message.author.id})", inline=False)
                    embed.add_field(name="Csatorna", value=message.channel.mention, inline=False)
                    embed.add_field(name="Üzenet", value=f"```{message.content}```", inline=False)
                    embed.set_footer(text="Timeout: 10 perc • Automatikus invite védelem")
                    await log_channel.send(embed=embed)
            except Exception as e:
                print(f"⚠️ Invite logolási hiba: {e}")

    await bot.process_commands(message)

# --- Manuális ticket zárás parancs ---
@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    await ctx.send("🔒 Ticket 5 másodpercen belül lezárul...")
    await asyncio.sleep(5)
    await ctx.channel.delete()

# --- Bot indítás ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bejelentkezve mint {bot.user}")

bot.run(TOKEN)
