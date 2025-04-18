import discord
from discord import app_commands
import aiohttp
import random
from typing import Optional
import asyncio

E621_USER_AGENT = "e1242/1.0"
MAX_TAGS = 5
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

async def fetch_posts(tags: list[str], limit: int = 100) -> Optional[list[dict]]:
    if len(tags) > MAX_TAGS:
        tags = tags[:MAX_TAGS]
        
    url = f"https://e621.net/posts.json?tags={'+'.join(tags)}&limit={limit}"
    headers = {"User-Agent": E621_USER_AGENT}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as response:
                response.raise_for_status()
                if 'application/json' not in response.headers.get('Content-Type', ''):
                    raise ValueError("Response was not JSON")
                data = await response.json()
                return data.get("posts", [])
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return None

def is_image(post: dict) -> bool:
    if not (file := post.get('file')):
        return False
    if not (url := file.get('url')):
        return False
    return any(url.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)

@tree.command(name="random", description="Fetch a random e621 image post by tags")
@app_commands.describe(
    tags="Space-separated tags",
    filter="Filter by rating: safe, questionable, explicit"
)
async def random_image(interaction: discord.Interaction, tags: str = "", filter: str = ""):
    if not interaction.channel.is_nsfw():
        return await interaction.response.send_message(
            "This command can only be used in NSFW channels!", ephemeral=True
        )

    await interaction.response.defer(thinking=True)
    
    tag_list = [t.strip() for t in tags.split() if t.strip()] if tags else []
    
    rating_map = {
        'safe': 'rating:s',
        'questionable': 'rating:q',
        'explicit': 'rating:e'
    }
    if filter.lower() in rating_map:
        tag_list.append(rating_map[filter.lower()])

    posts = await fetch_posts(tag_list)
    if not posts:
        return await interaction.followup.send(
            f"No posts found with tags: {' '.join(tags)}" + (f" and filter: {filter}" if filter else ""),
            ephemeral=True
        )

    image_posts = [post for post in posts if is_image(post)]
    if not image_posts:
        return await interaction.followup.send(
            "No image posts found matching your search",
            ephemeral=True
        )

    post = random.choice(image_posts)
    media_url = post.get('file', {}).get('url')
    rating = post.get('rating', '?').upper()

    embed = discord.Embed(
        title=f"Random Image (Rating: {rating})",
        color=discord.Color.blue()
    )
    embed.set_image(url=media_url)
    embed.set_footer(text=f"Tags: {tags}" if tags else "Random image post")
    
    await interaction.followup.send(embed=embed)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

async def main():
    token = input("Enter your Discord bot token: ").strip()
    
    if not token:
        print("No token provided, exiting...")
        return
    
    try:
        async with client:
            await client.start(token)
    except discord.LoginFailure:
        print("Invalid token provided")
    except Exception as e:
        print(f"Error running bot: {e}")

if __name__ == "__main__":
    print("Starting e1242 Discord bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")

