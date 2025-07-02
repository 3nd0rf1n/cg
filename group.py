from telethon import TelegramClient, events

api_id = 23530914
api_hash = '5a5590fb1466c424a344c15502c944b7'
bot_token = '7450692138:AAHiERBibay9XI56FhpSwFFclfKZmZNWoVM'
group_username = 'now4G'  # username групи без @

client = TelegramClient('session_bot', api_id, api_hash)

@client.on(events.NewMessage(pattern='/getmembers'))
async def handler(event):
    if event.is_private:
        members = []
        async for user in client.iter_participants(group_username):
            username = f"@{user.username}" if user.username else 'No username'
            name = user.first_name or ''
            members.append(f"{username} ({name})")

        text = '\n'.join(members)

        # Розбиваємо повідомлення на частини по ~4000 символів
        chunk_size = 4000
        for i in range(0, len(text), chunk_size):
            await event.respond(text[i:i+chunk_size])
    else:
        await event.respond("Будь ласка, використовуйте команду в особистому чаті.")

async def main():
    await client.start(bot_token=bot_token)
    print("Bot started")
    await client.run_until_disconnected()

import asyncio
asyncio.run(main())
