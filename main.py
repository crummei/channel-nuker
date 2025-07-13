import os
import re
import asyncio
import discord
from discord.ext import commands
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=">", intents=intents)

# Nuke function
async def nukeMessages(ctx, option, deleteLimit, nukeChannel, amountToCheck, user=None, criteria=None, criteriaType=None):
            deleted = 0
            botMsg = await ctx.send(f"Nuke started. Deleted {deleted} messages so far.")
            async for message in nukeChannel.history(limit=amountToCheck):
            # Handle message if criteria is message based
                if option == "criteria":
                    match criteriaType:
                        case "start":
                            if message.content.startswith(criteria):
                                shouldDelete = True
                        case "contain":
                            if criteria in message.content:
                                shouldDelete = True
                        case "end":
                            if message.content.endswith(criteria):
                                shouldDelete = True
                        case "exact":
                            if message.content == criteria:
                                shouldDelete = True
                        case _:
                            shouldDelete = False

            # Handle message if criteria is user based
                elif option == "user":
                    shouldDelete = True if message.author == user else False

            # Delete message if marked for deletion
                if shouldDelete == True:
                    if deleteLimit and deleted >= deleteLimit:
                        logging.info("deleteLimit reached")
                        break
                    try:
                        logging.info(f"Deleting message {message.content}")
                        await message.delete()
                        await asyncio.sleep(0.2)
                        logging.info(f"Deleted message {message.content}")
                        deleted += 1
                        await botMsg.edit(content=f"Nuke started. Deleted {deleted} messages so far.")
                    except discord.Forbidden:
                        await ctx.send("I don't have permission to delete messages.")
                        return
                    except discord.HTTPException as e:
                        if e.status == 429:
                            if {e.retry_after}:
                                logging.warning(f"Rate limited! Waiting {e.retry_after}...")
                            else:
                                logging.warning(f"Rate limited! Waiting 5 seconds...")
                            await asyncio.sleep(e.retry_after or 5)
                        else:
                            logging.info(f"Failed to delete message: {e}")

            if option == "user":
                await botMsg.edit(content=f"Deleted **{deleted}** message(s) in {nukeChannel.mention} from {user.mention}.")
            elif option == "criteria":
                await botMsg.edit(content=f"Deleted **{deleted}** message(s) in {nukeChannel.mention} that matched {criteria}.")

# Main bot code
@bot.event
async def on_ready():
    logging.info(f'Bot: {bot.user} is ready\n-------------\n')

@bot.command()
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    def checkChannel(m):
        return m.author == ctx.author and m.channel == ctx.channel
# Pick channel to nuke
    await ctx.send("Please mention the channel you wish to nuke (e.g. #general) or type channel ID:")

    try:
        nukeMsg = await bot.wait_for("message", check=checkChannel, timeout=60)
        nukeChannel = None

        if nukeMsg.channel_mentions:
            nukeChannel = nukeMsg.channel_mentions[0]
        else:
            nukeChannel = bot.get_channel(int(nukeMsg.content.strip()))

        if nukeChannel is None:
            await ctx.send("Invalid channel. Command cancelled.")
            return

    # Pick nuke type
        await ctx.send("Would you like to nuke messages:\n1. From user\n2. From criteria:")

        optionMsg = await bot.wait_for("message", check=checkChannel, timeout=60)
        
        if str(optionMsg.content.lower()) in ["1", "1.", "user", "from user"]:
            option = "user"
        elif str(optionMsg.content.lower()) in ["2", "2.", "criteria", "from criteria"]:
            option = "criteria"
        else:
            await ctx.send("Invalid choice. Command cancelled.")
            return

    # Select user to nuke
        if option == "user":
            await ctx.send("Mention the user whose messages you would like to nuke:")

            nukeUser = await bot.wait_for("message", check=checkChannel, timeout=60)        
            if nukeUser.mentions:
                user = nukeUser.mentions[0]
            else:
                # Try to extract a user ID from raw mention like <@123456789012345678>
                match = re.search(r"<@!?(\d+)>", nukeUser.content)
                if match:
                    user_id = int(match.group(1))
                    try:
                        user = await bot.fetch_user(user_id)  # works even if user isn't in the server
                    except discord.NotFound:
                        await ctx.send("Couldn't find that user. Command cancelled.")
                        return
                else:
                    await ctx.send("Invalid choice. Command cancelled.")
                    return

    # Select criteria
        if option == "criteria":
            await ctx.send("""Enter the criteria for the nuke to follow: ("All" for no criteria.)""")
            nukeCrit = await bot.wait_for("message", check=checkChannel, timeout=60)
            
            if nukeCrit.content.lower().strip() == "all":
                criteria = ""
                criteriaType = None
            
            elif nukeCrit.content.strip():
                criteria = nukeCrit.content.strip()

                await ctx.send(f"""Should the message:\n1. Start with "{criteria}"?\n2. Contain "{criteria}" anywhere?\n3. End with "{criteria}"?\n4. Match {criteria} exactly?""")
                criteriaTypeMsg = await bot.wait_for("message", check=checkChannel, timeout=60)
                
                if str(criteriaTypeMsg.content.strip().lower()) in ["1", "1.", "start", "start with", "startwith"]:
                    criteriaType = "start"
                
                elif str(criteriaTypeMsg.content.strip().lower()) in ["2", "2.", "contain", "contain anywhere", "anywhere"]:
                    criteriaType = "contain"
                
                elif str(criteriaTypeMsg.content.strip().lower()) in ["3", "3.", "end", "end with", "endwith"]:
                    criteriaType = "end"
                
                elif str(criteriaTypeMsg.content.strip().lower()) in ["4", "4.", "exact", "exact match", "exactmatch"]:
                    criteriaType = "exact"
                
                else:
                    await ctx.send("Invalid choice. Command cancelled.")
                    return

            else:
                await ctx.send("Invalid choice. Command cancelled.")
                return


    # Pick amount of messages
        await ctx.send("How many messages would you like to check? (0 for no limit)")

        amountToCheckMsg = await bot.wait_for("message", check=checkChannel, timeout=60)
        
        if amountToCheckMsg.content.strip().isdigit():
            amountToCheck = int(amountToCheckMsg.content.strip())
            if amountToCheck < 0:
                await ctx.send("Number cannot be negative. Command cancelled.")
                return
            elif amountToCheck == 0:
                amountToCheck = None
        else:
            await ctx.send("Invalid choice. Command cancelled.")
            return

    # Pick amount to delete
        await ctx.send("Would you like a limit to deleted messages?: (Enter 0 for no limit)")

        deleteLimitMsg = await bot.wait_for("message", check=checkChannel, timeout=60)
        
        if deleteLimitMsg.content.strip().isdigit():
            deleteLimit = int(deleteLimitMsg.content.strip())
            if deleteLimit < 0:
                await ctx.send("Number cannot be negative. Command cancelled.")
                return
        else:
            await ctx.send("Invalid choice. Command cancelled.")
            return
        
        if deleteLimit < 0:
            await ctx.send("Nuke is ready. Do you wish to launch?: (Yes/No)")
            confirmLaunchMsg = await bot.wait_for("message", check=checkChannel, timeout=60)
            if confirmLaunchMsg.content.lower() in ["yes", "y"]:
                confirm = True
            elif confirmLaunchMsg.content.lower() in ["no", "n"]:
                await ctx.send("Confirmation denied. Command cancelled.")
                return
            else:
                await ctx.send("Invalid choice. Command cancelled.")
                return

        elif deleteLimit == 0:
            await ctx.send("Nuke is ready. Do you wish to launch?: (Yes/No)\n**WARNING:** No delete limit selected, this will delete __**ALL**__ matching messages in the channel.")
            confirmLaunchMsg = await bot.wait_for("message", check=checkChannel, timeout=60)
            if confirmLaunchMsg.content.lower() in ["yes", "y"]:
                confirm = True
            elif confirmLaunchMsg.content.lower() in ["no", "n"]:
                await ctx.send("Confirmation denied. Command cancelled.")
                return
            else:
                await ctx.send("Invalid choice. Command cancelled.")
                return
        else:
            confirm = True
    
    # Launch nuke          
        if confirm == True:
            await nukeMessages(
                ctx,
                option=option,
                deleteLimit=deleteLimit,
                nukeChannel=nukeChannel,
                amountToCheck=amountToCheck,
                user=user if option == "user" else None,
                criteria=criteria if option == "criteria" else None, 
                criteriaType=criteriaType if criteriaType else None
            )

    except Exception as e:
        await ctx.send("Timed out or error occurred, command cancelled.")
        logging.warning(e)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    await bot.process_commands(message)

bot.run(os.environ.get('TOKEN'))
