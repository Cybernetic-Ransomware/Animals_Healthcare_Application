import asyncio

from discord import Client, Intents
from django.conf import settings

TOKEN = settings.DISCORD_TOKEN


def init_bot() -> Client:
    intents = Intents.default()
    intents.message_content = True

    client = Client(intents=intents)

    return client


async def send_via_discord(user_id: int, user_message: str) -> None:
    bot = init_bot()
    bot.run(TOKEN)

    @bot.event
    async def on_ready():
        user = bot.get_user(user_id)
        print(user_id)

        if user:
            await user.send(user_message)

        print(user_message)

        await asyncio.sleep(2)
        await bot.close()

    await bot.start(TOKEN)
