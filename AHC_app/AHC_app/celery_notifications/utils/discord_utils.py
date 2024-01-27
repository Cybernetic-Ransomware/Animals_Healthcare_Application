import asyncio

from discord import Client, Intents
from discord.ext import commands
from django.conf import settings

TOKEN = settings.DISCORD_TOKEN


def send_via_discord(user_id: int, user_message: str) -> None:
    def init_bot() -> Client:
        intents = Intents.default()
        intents.members = True
        intents.message_content = True

        # discord_client = Client(intents=intents)
        discord_client = commands.Bot(command_prefix="!", intents=intents)

        return discord_client

    client = init_bot()

    @client.event
    async def on_ready():
        for guild in client.guilds:
            user = guild.get_member(user_id)
            if user:
                await user.send(user_message)

        await asyncio.sleep(2)
        await client.close()

    client.run(TOKEN)
