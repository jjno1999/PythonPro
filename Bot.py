import discord
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import random
import asyncio

# Token de discord
TOKEN = 'Cambiar por token de discord'


# Habilitar intents específicos
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Listas para comandos de rol
WELCOME_CHANNEL_ID = 123456789012345678  # Reemplaza con el ID del canal de bienvenida

# Lista de palabras prohibidas
BANNED_WORDS = ['malapalabra1', 'malapalabra2', 'malapalabra3']

# Canal de sugerencias
SUGGESTION_CHANNEL_ID = 123456789012345678  # Reemplaza con el ID del canal de sugerencias

@bot.event
async def on_ready():
    print(f'{bot.user} se ha conectado a Discord!')
    change_status.start()

@tasks.loop(minutes=10)
async def change_status():
    statuses = ['Jugando en el servidor', 'Desarrollando bots', 'Escuchando música']
    await bot.change_presence(activity=discord.Game(random.choice(statuses)))

@bot.command(name='ping')
async def ping(ctx):
    latency = bot.latency
    await ctx.send(f'Pong! {latency * 1000:.2f}ms')

@bot.command(name='info')
async def info(ctx):
    server_name = ctx.guild.name
    member_count = ctx.guild.member_count
    await ctx.send(f'Este servidor se llama {server_name} y tiene {member_count} miembros.')

@bot.command(name='clear')
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f'Se han borrado {amount} mensajes.', delete_after=5)

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(f'¡Bienvenido al servidor, {member.mention}!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    for word in BANNED_WORDS:
        if word in message.content:
            await message.delete()
            await message.channel.send(f'{message.author.mention}, esa palabra está prohibida.')
            return

    await bot.process_commands(message)

@bot.command(name='kick')
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'{member.mention} ha sido expulsado por {reason}.')

@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'{member.mention} ha sido baneado por {reason}.')

@bot.command(name='unban')
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_name):
    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name == member_name:
            await ctx.guild.unban(user)
            await ctx.send(f'{user.mention} ha sido desbaneado.')
            return
    await ctx.send(f'No se encontró a {member_name} en la lista de baneados.')

@bot.command(name='mute')
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name='Muted')
    if not muted_role:
        muted_role = await ctx.guild.create_role(name='Muted')
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, speak=False, send_messages=False)
    await member.add_roles(muted_role)
    await ctx.send(f'{member.mention} ha sido silenciado.')

@bot.command(name='unmute')
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name='Muted')
    if muted_role:
        await member.remove_roles(muted_role)
        await ctx.send(f'{member.mention} ha sido desilenciado.')

@bot.command(name='addrole')
@commands.has_permissions(manage_roles=True)
async def add_role(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f'{member.mention} ahora tiene el rol {role.name}.')

@bot.command(name='removerole')
@commands.has_permissions(manage_roles=True)
async def remove_role(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f'{member.mention} ya no tiene el rol {role.name}.')

@bot.command(name='suggest')
async def suggest(ctx, *, suggestion):
    channel = bot.get_channel(SUGGESTION_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="Nueva Sugerencia", description=suggestion, color=discord.Color.blue())
        embed.set_footer(text=f'Sugerido por {ctx.author}', icon_url=ctx.author.avatar.url)
        await channel.send(embed=embed)
        await ctx.send('¡Gracias por tu sugerencia! Ha sido enviada al canal de sugerencias.')

@bot.event
async def on_reaction_add(reaction, user):
    if reaction.message.channel.id == SUGGESTION_CHANNEL_ID:
        if reaction.emoji == '👍':
            await reaction.message.channel.send(f'A {user.name} le gusta esta sugerencia.')
        elif reaction.emoji == '👎':
            await reaction.message.channel.send(f'A {user.name} no le gusta esta sugerencia.')

@bot.command(name='play')
async def play(ctx, url):
    if not ctx.author.voice:
        await ctx.send('¡Necesitas estar en un canal de voz para usar este comando!')
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client:
        await ctx.voice_client.disconnect()

    voice_client = await channel.connect()

    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop)
        voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    await ctx.send(f'Reproduciendo: {player.title}')

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Reproducción detenida y desconectado del canal de voz.')

# Clase para descargar música de YouTube
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        ytdl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0'
        }
        ytdl = youtube_dl.YoutubeDL(ytdl_opts)
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Opciones para FFmpeg
ffmpeg_options = {
    'options': '-vn'
}

bot.run(TOKEN)
