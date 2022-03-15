# The following file includes: name_grabber, log_event, has_tag_perms, check_tag, get_giveaway_status, roll_giveaway

from datetime import datetime, timedelta
from io import BytesIO

import chat_exporter
import discord
from __main__ import bot

from discord.ext import commands, tasks
from discord.ui import Select, View
from func.utils.db_utils import select_one, insert_new_dnkl, update_dnkl
from func.utils.consts import (config, dnkl_req, gvg_requirements, neg_color,
                               neutral_color, dnkl_channel_id, log_channel_id, invalid_date_msg, staff_application_questions,
                               ticket_categories, unknown_ign_embed, months)
from func.utils.minecraft_utils import get_player_gexp
from func.utils.request_utils import get_hypixel_player, get_mojang_profile


async def name_grabber(author: discord.User) -> str:
    if not author.nick:
        return author.name
    return author.nick.split()[0]

async def is_linked_discord(player_data: dict, user: discord.User) -> bool:
    if "socialMedia" not in player_data or "DISCORD" not in player_data["socialMedia"]["links"]:
        return False
    return player_data["socialMedia"]["links"]["DISCORD"] == str(user)

async def create_ticket(user: discord.Member, ticket_name: str, category_name: str=ticket_categories["generic"]):
    # Create ticket
    ticket: discord.TextChannel = await bot.guild.create_text_channel(ticket_name, category=discord.utils.get(bot.guild.categories, name=category_name))

    # Set perms
    await ticket.set_permissions(bot.guild.get_role(bot.guild.id), send_messages=False,
                                            read_messages=False)
    await ticket.set_permissions(bot.staff, send_messages=True, read_messages=True,
                                            add_reactions=True, embed_links=True,
                                            attach_files=True,
                                            read_message_history=True, external_emojis=True)
    await ticket.set_permissions(bot.helper, send_messages=True,
                                            read_messages=True,
                                            add_reactions=True, embed_links=True,
                                            attach_files=True,
                                            read_message_history=True, external_emojis=True)
    await ticket.set_permissions(user, send_messages=True, read_messages=True,
                                            add_reactions=True, embed_links=True,
                                            attach_files=True,
                                            read_message_history=True, external_emojis=True)
    await ticket.set_permissions(bot.new_member_role, send_messages=False,
                                            read_messages=False,
                                            add_reactions=True, embed_links=True,
                                            attach_files=True,
                                            read_message_history=True, external_emojis=True)

    # Send the dropdown for ticket creation
    class TicketTypeSelect(Select):
        def __init__(self):
            super().__init__()

            # Add default options
            self.add_option(label="Report a player", emoji="🗒️")
            self.add_option(label="Query/Problem", emoji="🤔")
            
            # Add milestone, DNKL application, staff application, GvG application if user is a member
            if bot.member_role in user.roles:
                self.add_option(label="Register a milestone", emoji="🏆")
                self.add_option(label="Do-not-kick-list application", emoji="<:dnkl:877657298703634483>")
                self.add_option(label="Staff application", emoji="🤵")
                self.add_option(label="GvG Team application", emoji="⚔️")

            # Add "Other" option last
            self.add_option(label="Other", emoji="❓")

        # Override default callback
        async def callback(self, interaction: discord.Interaction):
            ign, uuid = await get_mojang_profile(await name_grabber(interaction.user))
            # Set option var and delete Select so it cannot be used twice
            option = list(interaction.data.values())[0][0]
            await interaction.message.delete()

            # Logic for handling ticket types
            if option == "Report a player":
                await ticket.edit(name=f"report-{ign}", category=discord.utils.get(interaction.guild.categories, name=ticket_categories["report"]))
                await ticket.send(embed=discord.Embed(title=f"{ign} wishes to file a player report!",
                                                description="You are expected to provide maximum detail about the offense.\n"
                                                            "> Username of the accused\n> Time of offense\n> Explanation of offense\n> Proof of offense\n"
                                                            "If you wish to report a staff member, please DM the guild master or an admin.",
                                                color=neutral_color))
            if option == "Query/Problem":
                await ticket.edit(name=f"general-{ign}", category=discord.utils.get(interaction.guild.categories, name=ticket_categories["generic"]))
                await ticket.send(embed=discord.Embed(title=f"{ign} has a query/problem!",
                                        description="Please elaborate on your problem/query so that the staff team can help you out!",
                                        color=neutral_color))
            if option == "Register a milestone":
                await ticket.edit(name=f"milestone-{ign}", category=discord.utils.get(interaction.guild.categories, name=ticket_categories["milestone"]))
                await ticket.send(embed=discord.Embed(title=f"{ign} would like to register a milestone!",
                                                description="Please provide a small description and proof of your milestone!\nIf your milestone is approved, it'll be included in next week's milestone post!",
                                                color=neutral_color))
            if option == "Do-not-kick-list application":
                # Edit channel name and category
                await ticket.edit(name=f"dnkl-{ign}", category=discord.utils.get(interaction.guild.categories, name=ticket_categories["dnkl"]))

                # Notify user if they don't meet gexp req, however ask questions anyway
                _, weekly_gexp = await get_player_gexp(uuid)
                if weekly_gexp == None:
                    return await ticket.send(embed=unknown_ign_embed)
                if weekly_gexp < dnkl_req:
                    await ticket.send(embed=discord.Embed(title="You do not meet the do-not-kick-list requirements!",
                                                                        description="Even though you do not meet the requirements, your application may still be accepted.",
                                                                        color=neg_color))

                # DNKL application view
                class DnklApplicationView(View):
                    def __init__(self):
                        super().__init__()

                    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅")
                    async def approve_callback(self, _: discord.ui.Button, interaction: discord.Interaction):
                        if bot.staff not in interaction.user.roles: return
                        msg = await bot.get_channel(dnkl_channel_id).send(embed=embed) 

                        # Check if user is already on DNKL
                        current_message = await select_one("SELECT message_id FROM dnkl WHERE uuid = (?)", (uuid,))
                        # User is not currently on DNKL
                        if not current_message:
                            await insert_new_dnkl(msg.id, uuid, ign)
                            return await ticket.send("This user has been added to the do-not-kick-list!")

                        # User is already on DNKl
                        # Try to delete current message
                        try:
                            current_message = await bot.get_channel(dnkl_channel_id).fetch_message(current_message)
                            await current_message.delete()
                        except Exception:
                            pass

                        await update_dnkl(msg.id, uuid)
                        await ticket.send("Since this user was already on the do-not-kick-list, their entry has been updated.")

                    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="❌")
                    async def deny_callback(self, _: discord.ui.Button, interaction: discord.Interaction):
                        if bot.staff in interaction.user.roles:
                            await ticket.send(embed=discord.Embed(title="Your do-not-kick-list application has been denied!",
                                                                                color=neg_color))

                    @discord.ui.button(label="Error", emoji="📔")
                    async def error_callback(self, _: discord.ui.Button, interaction: discord.Interaction):
                        if bot.staff in interaction.user.roles:
                            await ticket.send(embed=discord.Embed(title="Your application has been accepted, however there was an error!",
                                                                                description="Please await staff assistance!",
                                                                                color=neutral_color))

                # Ask DNKL application questions and send preview embed
                embed = await dnkl_application(ign, uuid, ticket, interaction.user)
                await ticket.send("Staff, what do you wish to do with this application?", embed=embed, view=DnklApplicationView())
            if option == "Staff application":
                # Edit category and send info embed with requirements
                await ticket.edit(name=f"staff-application-{ign}", category=discord.utils.get(interaction.guild.categories, name=ticket_categories["generic"]))
                await ticket.send(embed=discord.Embed(title=f"{ign} wishes to apply for staff!",
                                        description="Please respond to the bot's prompts appropriately!",
                                        color=neutral_color).add_field(
                                        name="Do you meet the following requirements? (y/n)",
                                        value="• You must be older than 13 years.\n• You must have sufficient knowledge of the bots in this Discord."
                                                "\n• You must be active both on Hypixel and in the guild Discord.\n• You must have a good reputation amongst guild members.",
                                        inline=False))

                meets_requirements = await bot.wait_for("message", check=lambda x: x.channel == ticket and x.author == interaction.user)

                # If user doesn't meet requirements, deny application
                if meets_requirements.content not in ["y", "yes"]:
                    return await ticket.send(embed=discord.Embed(title="Your staff application has been denied!",
                                                                        description="Since you do not meet the requirements, your staff application has been denied.",
                                                                        color=neg_color))

                # Loop for all questions to gather info
                answers = {}
                for number, question in staff_application_questions.items():
                    # Ask question and wait for answer
                    await ticket.send(embed=discord.Embed(title=f"{number}. {question}", description="You must answer in one message.", color=neutral_color)) 
                    answer = await bot.wait_for("message", check=lambda x: x.channel == ticket and x.author == interaction.user)

                    # Place answer into array with question number
                    answers[number] = answer.content

                # Send completion message
                await ticket.send("Your staff application has been completed! Please wait while your answers are compiled.")

                # Create overview embed
                review_embed = discord.Embed(title=f"{ign}'s Staff Application", color=neutral_color)
                review_embed.set_footer(text="If you made a mistake, please notify a staff member.")
                for number, answer in answers.items():
                    review_embed.add_field(name=f"{number}. {staff_application_questions[number]}", value=answer, inline=False)
                
                # Send embed
                await ticket.send(embed=review_embed)
            if option == "GvG Team application":
                # Edit channel name and category
                await ticket.edit(name=f"gvg-application-{ign}", category=discord.utils.get(interaction.guild.categories, name=ticket_categories["generic"]))
                
                # Fetch player data
                player_data = await get_hypixel_player(ign)
                if player_data == None:
                    return await ticket.send(unknown_ign_embed)
                player_data = player_data["stats"]

                # Set vars for each stat
                bw_wins = player_data["Bedwars"]["wins_bedwars"]
                bw_fkdr = round(player_data["Bedwars"]["final_kills_bedwars"] / player_data["Bedwars"]["final_deaths_bedwars"], 2)
                sw_wins = player_data["SkyWars"]["wins"]
                sw_kdr = round(player_data["SkyWars"]["kills"] / player_data["SkyWars"]["deaths"], 2)
                duels_wlr = round(player_data["Duels"]["wins"] / player_data["Duels"]["losses"], 2)
                duels_kills = player_data["Duels"]["kills"]

                # Define dict for eligibility and set each gamemode boolean
                eligibility = {}
                eligibility["bedwars"] = False if bw_wins < gvg_requirements["bw_wins"] and bw_fkdr < gvg_requirements["bw_fkdr"] else True
                eligibility["skywars"] = False if sw_wins < gvg_requirements["sw_wins"] and sw_kdr < gvg_requirements["sw_kdr"] else True
                eligibility["duels"] = False if duels_wlr < gvg_requirements["duels_wlr"] and duels_kills < gvg_requirements["duels_kills"] else True
                
                # Polyvalent eligibility
                if all(eligibility.values()):
                    embed = discord.Embed(title="You are eligible for the polyvalent team!", color=neutral_color)
                    embed.set_footer(text="Please await staff assistance for further information!")
                    embed.add_field(name="Bedwars Wins", value=f"`{bw_wins}`")
                    embed.add_field(name="Bedwars FKDR", value=f"`{bw_fkdr}`")
                    embed.add_field(name="Skywars Wins", value=f"`{sw_wins}`")
                    embed.add_field(name="Skywars KDR", value=f"`{sw_kdr}`")
                    embed.add_field(name="Duels WLR", value=f"`{duels_wlr}`")
                    embed.add_field(name="Duels Kills", value=f"`{duels_kills}`")
                    await ticket.send(embed=embed)

                # User is not eligible for any team
                elif not all(eligibility.values()):
                    await ticket.send(embed=discord.Embed(title="You are ineligible for the GvG Team as you do not meet the requirements!",
                                                                        description="Please await staff assistance for further information!",
                                                                        color=neg_color))

                # User is eligible for at least one gamemode
                else:
                    # loop through all GvG gamemodes
                    for mode, req1_name, req1, req2_name, req2 in [["bedwars", "Wins", bw_wins, "FKDR", bw_fkdr], ["skywars", "Wins", sw_wins, "KDR", sw_kdr],
                                                                    ["duels", "WLR", duels_wlr, "Kills", duels_kills]]: 
                        # If user is eligible for that gamemode, create embed
                        if eligibility[mode]:
                            embed = discord.Embed(title=f"You are eiligible for the {mode.capitalize()} team!", color=neutral_color)
                            embed.set_footer(text="Please await staff assistance for further information!")
                            embed.add_field(title=req1_name, value=f"`{req1}`")
                            embed.add_field(title=req2_name, value=f"`{req2}`")

                            # Send embed and end loop
                            await ticket.send(embed=embed)
            if option == "Other":
                await ticket.edit(name=f"other-{ign}", category=discord.utils.get(interaction.guild.categories, name=ticket_categories["dnkl"]))
                await ticket.send(embed=discord.Embed(title="This ticket has been created for an unkown reason!", 
                                                                    description="Please specify why you have created this ticket!",
                                                                    color=neutral_color))
            

    # Create view and embed, send to ticket
    view = View()
    view.add_item(TicketTypeSelect())
    embed = discord.Embed(title="What did you make this ticket?",
                        description="Please select your reason from the dropdown given below!",
                        color=neutral_color)
    await ticket.send(embed=embed, view=view)

    # Return ticket for use
    return ticket

async def log_event(title: str, description: str=None):
    embed = discord.Embed(title=title, description=description, color=neutral_color)
    await bot.get_channel(log_channel_id).send(embed=embed)

async def has_tag_perms(user: discord.User):
    return any(role in user.roles for role in bot.tag_allowed_roles)

async def check_tag(tag: str):
    tag = tag.lower()
    with open("func/utils/badwords.txt", "r") as f:
        badwords = f.read()

    if tag in badwords.split("\n"):
        return False, "Your tag may not include profanity."
    elif not tag.isascii():
        return False, "Your tag may not include special characters unless it's the tag of an ally guild."
    elif len(tag) > 6:
        return False, "Your tag may not be longer than 6 characters."
    # Tag is okay to use
    return True, None

async def is_valid_date(date: str):
    # Return False if parsing fails
    try:
        parsed = datetime.strptime(date, "%Y/%m/%d")
        # Validate time is within the last week
        if parsed < datetime.utcnow() - timedelta(days=7):
            return False, None, None, None
        return True, parsed.day, parsed.month, parsed.year
    except ValueError:
        return False, None, None, None

async def create_transcript(channel: discord.TextChannel):
    transcript = await chat_exporter.export(channel)
    if not transcript: return None

    # Create and return file
    return discord.File(BytesIO(transcript.encode()), filename=f"transcript-{channel.name}.html")

async def dnkl_application(ign: str, uuid: str, channel: discord.TextChannel, author: discord.User):
    # Recursively ask for start date
    while True:
        await channel.send("**What is the start date?** (YYYY/MM/DD)")
        start_date = await bot.wait_for("message", check=lambda x: x.channel == channel and x.author == author)
        valid_date, sd, sm, sy = await is_valid_date(start_date.content)
        if valid_date:
            break
        await channel.send(invalid_date_msg)
        

    # Recursively ask for end date
    while True:
        await channel.send("**What is the end date?** (YYYY/MM/DD)")
        end_date = await bot.wait_for("message", check=lambda x: x.channel == channel and x.author == author)
        valid_date, ed, em, ey = await is_valid_date(end_date.content)
        if valid_date:
            break
        await channel.send(invalid_date_msg)

    # Ask for reason
    await channel.send("**What is the reason for their inactivity?**")
    reason = await bot.wait_for("message", check=lambda x: x.channel == channel and x.author == author)
    reason = reason.content

    # Get worded months (1 = January)
    sm = months[sm]
    em = months[em]

    # Create and return embed
    embed = discord.Embed(title=ign, url=f'https://plancke.io/hypixel/player/stats/{ign}', color=neutral_color)
    embed.set_thumbnail(url=f'https://crafatar.com/renders/body/{uuid}')
    embed.add_field(name="IGN:", value=f"{ign}", inline=False)
    embed.add_field(name="Start:", value=f"{sd} {sm} {sy}", inline=False)
    embed.add_field(name="End:", value=f"{ed} {em} {ey}", inline=False)
    embed.add_field(name="Reason", value=f"{reason}", inline=False)

    return embed

@tasks.loop(count=1)
async def after_cache_ready():
    # Set owner id(s) and guild
    bot.owner_ids = config["owner_ids"]
    bot.guild = bot.get_guild(config["guild_id"])

    # Set roles
    bot.admin = discord.utils.get(bot.guild.roles, name="Admin")
    bot.staff = discord.utils.get(bot.guild.roles, name="Staff")
    bot.helper = discord.utils.get(bot.guild.roles, name="Helper")
    bot.former_staff = discord.utils.get(bot.guild.roles, name="Former Staff")
    bot.new_member_role = discord.utils.get(bot.guild.roles, name="New Member")
    bot.guest = discord.utils.get(bot.guild.roles, name="Guest")
    bot.member_role = discord.utils.get(bot.guild.roles, name="Member")
    bot.active_role = discord.utils.get(bot.guild.roles, name="Active")
    bot.ally = discord.utils.get(bot.guild.roles, name="Ally")
    bot.server_booster = discord.utils.get(bot.guild.roles, name="Server Booster")
    bot.rich_kid = discord.utils.get(bot.guild.roles, name="Rich Kid")
    bot.giveaways_events = discord.utils.get(bot.guild.roles, name="Giveaways/Events")
    bot.tag_allowed_roles = (bot.active_role, bot.staff, bot.former_staff, bot.server_booster, bot.rich_kid)

    from func.utils.discord_utils import name_grabber
    bot.staff_names = [await name_grabber(member) for member in bot.staff.members]

    # Initialise chat_exporter
    chat_exporter.init_exporter(bot)

    # Set help command
    class HelpCommand(commands.MinimalHelpCommand):
        async def send_pages(self):
            destination = self.get_destination()
            for page in self.paginator.pages:
                embed = discord.Embed(description=page, color=neutral_color)
                await destination.send(embed=embed)

        async def send_command_help(self, command):
            embed = discord.Embed(title=self.get_command_signature(command), color=neutral_color)
            embed.add_field(name="Help", value=command.help)
            alias = command.aliases
            if alias:
                embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

            channel = self.get_destination()
            await channel.send(embed=embed)

    bot.help_command = HelpCommand(command_attrs={"hidden": True})

@after_cache_ready.before_loop
async def before_cache_loop():
    print("Waiting for cache...")
    await bot.wait_until_ready()
    print("Cache filled")
