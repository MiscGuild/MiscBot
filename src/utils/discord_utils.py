import asyncio
from __main__ import bot
from datetime import datetime, timedelta
from io import BytesIO

import chat_exporter
import discord
import discord.ui as ui
from discord.ext import tasks

import src.utils.ui_utils as uiutils
from src.utils.consts import (config, dnkl_req,
                              gvg_requirements, log_channel_id, neg_color, neutral_color, staff_application_questions,
                              ticket_categories,
                              unknown_ign_embed, guild_handle, positive_responses, dnkl_creation_embed, dnkl_channel_id,
                              missing_permissions_embed)
from src.utils.db_utils import select_one, insert_new_dnkl, update_dnkl, delete_dnkl
from src.utils.minecraft_utils import get_player_gexp
from src.utils.request_utils import get_hypixel_player, get_mojang_profile, get_player_guild, get_guild_level


async def name_grabber(author: discord.Member) -> str:
    if not author.nick:
        return author.name
    return author.nick.split()[0]


async def is_linked_discord(player_data: dict, user: discord.User) -> bool:
    if not player_data:
        return False
    if "socialMedia" not in player_data:
        return False
    if not player_data["socialMedia"]:
        return False
    if "links" not in player_data["socialMedia"]:
        return False
    if not player_data["socialMedia"]["links"]:
        return False
    if "DISCORD" not in player_data["socialMedia"]["links"]:
        return False
    discord = player_data["socialMedia"]["links"]["DISCORD"]

    return (discord == str(user)[:-2]) or (discord == (str(user.id) + "#0000") or (discord == str(user)))


async def get_ticket_creator(channel: discord.TextChannel):
    return bot.guild.get_member(int(channel.topic.split("|")[0]))


async def close_ticket(channel: discord.TextChannel, author: discord.User, ign: str, uuid: str,
                       embed: discord.Embed, interaction: discord.Interaction):
    if author != interaction.user:
        await channel.send(embed=missing_permissions_embed)
        return None

    embed = discord.Embed(title="This ticket will be deleted in 20 seconds!", color=neg_color)

    # Send deletion warning and gather transcript
    await interaction.response.send_message(embed=embed)
    transcript = await chat_exporter.export(channel, limit=None)
    if transcript:
        transcript = discord.File(BytesIO(transcript.encode()),
                                  filename=f"transcript-{channel.name}.html")
        await bot.get_channel(log_channel_id).send(
            f"DNKL Request was denied and channel was deleted by {author}")
        await bot.get_channel(log_channel_id).send(file=transcript)

    # Sleep and delete channel
    await asyncio.sleep(20)
    await discord.TextChannel.delete(channel)


async def gvg_approve(channel: discord.TextChannel, author: discord.User, ign: str, uuid: str, embed: discord.Embed,
                      interaction: discord.Interaction):
    if bot.staff not in interaction.user.roles:
        await channel.send(embed=missing_permissions_embed)
        return None

    await interaction.response.send_message(embed=discord.Embed(
        title="Your application has been accepted!",
        description="Please await staff assistance for more information!",
        color=neutral_color))
    member = await bot.guild.fetch_member(author.id)
    await member.add_roles(bot.gvg)

    return True


async def gvg_deny(channel: discord.TextChannel, author: discord.User, ign: str, uuid: str, embed: discord.Embed,
                   interaction: discord.Interaction):
    if bot.staff not in interaction.user.roles:
        await channel.send(embed=missing_permissions_embed)
        return None

    await interaction.response.send_message(embed=discord.Embed(
        title="Your application has been denied!",
        description="Please await staff assistance for more information!",
        color=neg_color))

    return True


async def dnkl_error(channel: discord.TextChannel, author: discord.User, ign: str, uuid: str, embed: discord.Embed,
                     interaction: discord.Interaction):
    if bot.staff not in interaction.user.roles:
        await channel.send(embed=missing_permissions_embed)
        return None

    await interaction.response.send_message(embed=discord.Embed(
        title="Your application has been accepted, however there was an error!",
        description="Please await staff assistance!",
        color=neutral_color))
    return True


async def dnkl_deny(channel: discord.TextChannel, author: discord.User, ign: str, uuid: str, embed: discord.Embed,
                    interaction: discord.Interaction, self_denial: bool = False):
    if bot.staff not in interaction.user.roles and not self_denial:
        await channel.send(embed=missing_permissions_embed)
        return None

    if not self_denial:
        await interaction.response.send_message("**This user's do-not-kick-list application has been denied!.**\n"
                                                "If you didn't mean to hit deny, you can add them using `/dnkl_add`.",
                                                ephemeral=True)

        embed = discord.Embed(title="Your do-not-kick-list application has been denied!",
                              description=f"You do not meet the DNKL requirements of {format(dnkl_req, ',d')} weekly guild experience.",
                              color=neg_color)
        embed.set_footer(
            text="If don't you think you can meet the requirements, you may rejoin the guild once your inactivity period has ended.")

    closeView = discord.ui.View(timeout=None)  # View for staff members to approve/deny the DNKL
    button = ("Close This Ticket", "close_ticket", discord.enums.ButtonStyle.red)
    closeView.add_item(
        uiutils.Button_Creator(channel=channel, author=author, ign=ign, uuid=uuid, button=button,
                               function=close_ticket))
    await channel.send(embed=embed, view=closeView)
    await delete_dnkl(ign)

    return True


async def dnkl_approve(channel: discord.TextChannel, author: discord.User, ign: str, uuid: str, embed: discord.Embed,
                       interaction: discord.Interaction):
    if bot.staff not in interaction.user.roles:
        await channel.send(embed=missing_permissions_embed)
        return None

    msg = await bot.get_channel(dnkl_channel_id).send(embed=embed)

    # Check if user is already on DNKL
    current_message = await select_one("SELECT message_id FROM dnkl WHERE uuid = (?)",
                                       (uuid,))
    # User is not currently on DNKL
    if not current_message:
        await insert_new_dnkl(msg.id, uuid, ign)
        return await interaction.response.send_message("**This user has been added to the do-not-kick-list!**")

    # User is already on DNKl
    # Try to delete current message
    try:
        current_message = await bot.get_channel(dnkl_channel_id).fetch_message(
            current_message)
        await current_message.delete()
    except Exception:
        pass

    await update_dnkl(msg.id, uuid)
    await interaction.response.send_message(
        "**Since this user was already on the do-not-kick-list, their entry has been updated.**")

    return True


async def create_ticket(user: discord.Member, ticket_name: str, category_name: str = ticket_categories["generic"]):
    # Create ticket
    ticket: discord.TextChannel = await bot.guild.create_text_channel(ticket_name,
                                                                      category=discord.utils.get(bot.guild.categories,
                                                                                                 name=category_name))
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
    if category_name != ticket_categories["registrees"]:
        # Send the dropdown for ticket creation
        class TicketTypeSelect(ui.Select):
            def __init__(self):
                super().__init__()

                if bot.guest in user.roles:
                    self.add_option(label=f"I want to join {guild_handle}", emoji="<:Misc:540990817872117780>")
                    self.add_option(label=f"I want to organize a GvG with {guild_handle}", emoji="⚔️")
                    self.add_option(label=f"My guild wishes to ally {guild_handle}", emoji="🤝")

                # Add milestone, DNKL application, staff application, GvG application if user is a member
                if bot.member_role in user.roles:
                    self.add_option(label="Register a milestone", emoji="🏆")
                    self.add_option(label="I am going to be inactive", emoji="<:dnkl:877657298703634483>")
                    self.add_option(label="I want to join the staff team", emoji="🤵")
                    self.add_option(label="I want to join the GvG team", emoji="⚔️")

                # Add default options
                self.add_option(label="Report a player", emoji="🗒️")
                self.add_option(label="Query/Problem", emoji="🤔")

                # Add "Other" option last
                self.add_option(label="Other", emoji="❓")

            # Override default callback
            async def callback(self, interaction: discord.Interaction):
                ign, uuid = await get_mojang_profile(await name_grabber(interaction.user))
                # Set option var and delete Select so it cannot be used twice
                option = list(interaction.data.values())[0][0]
                await ticket.purge(
                    limit=100)  # Deleting the interaction like this so that we can respond to the interaction later

                # Logic for handling ticket types
                if option == "Report a player":
                    await ticket.edit(name=f"report-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories["generic"]))
                    fields = [
                        ["What was the username of the accused", "", discord.InputTextStyle.short,
                         "Username of the accused"],
                        ["What was the offense?", "", discord.InputTextStyle.short, "Offense"],
                        ["When did this happen?", "", discord.InputTextStyle.short, "Time of Offense"],
                        ["Provide a brief description of what happened.",
                         "Answer the question in no more than 100 words.",
                         discord.InputTextStyle.long, "Description"]
                    ]
                    embed = discord.Embed(title="Player Report", color=neutral_color)
                    await interaction.response.send_modal(
                        modal=uiutils.ModalCreator(embed=embed, fields=fields, ign=ign, uuid=uuid,
                                                   title="Player Report"))
                if option == "Query/Problem":
                    await ticket.edit(name=f"general-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories["generic"]))
                    await ticket.send(embed=discord.Embed(title=f"{ign} has a query/problem!",
                                                          description="Please elaborate on your problem/query so that the staff team can help you out!",
                                                          color=neutral_color))
                if option == "Register a milestone":
                    await ticket.edit(name=f"milestone-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories[
                                                                     "milestone"]))
                    await ticket.send(embed=discord.Embed(title=f"{ign} would like to register a milestone!",
                                                          description="Please provide a small description and proof of your milestone!\nIf your milestone is approved, it'll be included in next week's milestone post!",
                                                          color=neutral_color))
                if option == "I am going to be inactive":
                    # Edit channel name and category
                    await ticket.edit(name=f"dnkl-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories["dnkl"]))

                    # Notify user if they don't meet gexp req, however ask questions anyway
                    _, weekly_gexp = await get_player_gexp(uuid)
                    if weekly_gexp is None:
                        return await ticket.send(embed=unknown_ign_embed)
                    await ticket.send(embed=dnkl_creation_embed)
                    if weekly_gexp < dnkl_req:
                        await ticket.send(
                            embed=discord.Embed(title="You do not meet the do-not-kick-list requirements!",
                                                description=f"Even though you do not meet the requirements, your application may still be accepted.\nYou have {format(weekly_gexp, ',d')} weekly guild experience!",
                                                color=neg_color))
                    else:
                        await ticket.send(embed=discord.Embed(title="You meet the do-not-kick-list requirements!",
                                                              description=f"You have {format(weekly_gexp, ',d')} weekly guild experience!",
                                                              color=neutral_color))
                    await dnkl_application(ign, uuid, ticket, interaction.user, weekly_gexp)
                if option == "I want to join the staff team":
                    # Edit category and send info embed with requirements
                    await ticket.edit(name=f"staff-application-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories["generic"]))
                    await ticket.send(embed=discord.Embed(title=f"{ign} wishes to apply for staff!",
                                                          description="Please respond to the bot's prompts appropriately!",
                                                          color=neutral_color).add_field(
                        name="Do you meet the following requirements? (y/n)",
                        value="• You must be older than 13 years.\n• You must have sufficient knowledge of the bots in this Discord."
                              "\n• You must be active both on Hypixel and in the guild Discord.\n• You must have a good reputation amongst guild members.",
                        inline=False))

                    meets_requirements = await bot.wait_for("message", check=lambda
                        x: x.channel == ticket and x.author == interaction.user)

                    # If user doesn't meet requirements, deny application
                    if (meets_requirements.content).lower() not in positive_responses:
                        return await ticket.send(embed=discord.Embed(title="Your staff application has been denied!",
                                                                     description="Since you do not meet the requirements, your staff application has been denied.",
                                                                     color=neg_color))

                    # Loop for all questions to gather info
                    answers = {}
                    for number, question in staff_application_questions.items():
                        # Ask question and wait for answer
                        await ticket.send(embed=discord.Embed(title=f"{number}. {question}",
                                                              description="You must answer in one message.",
                                                              color=neutral_color))
                        answer = await bot.wait_for("message",
                                                    check=lambda
                                                        x: x.channel == ticket and x.author == interaction.user)

                        # Place answer into array with question number
                        answers[number] = answer.content

                    # Send completion message
                    await ticket.send(
                        "Your staff application has been completed! Please wait while your answers are compiled.")

                    # Create overview embed
                    review_embed = discord.Embed(title=f"{ign}'s Staff Application", color=neutral_color)
                    review_embed.set_footer(text="If you made a mistake, please notify a staff member.")
                    for number, answer in answers.items():
                        review_embed.add_field(name=f"{number}. {staff_application_questions[number]}", value=answer,
                                               inline=False)

                    # Send embed
                    message = await ticket.send(embed=review_embed)
                    await ticket.edit(topic=f"{interaction.user.id}|{message.id}")
                if option == "I want to join the GvG team":
                    # Edit channel name and category
                    await ticket.edit(name=f"gvg-application-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories["generic"]))

                    # Fetch player data
                    player_data = await get_hypixel_player(uuid=uuid)
                    if not player_data:
                        return await ticket.send(embed=unknown_ign_embed)
                    player_data = player_data["stats"]

                    # Set vars for each stat
                    bw_wins = player_data["Bedwars"]["wins_bedwars"]
                    bw_fkdr = round(
                        player_data["Bedwars"]["final_kills_bedwars"] / player_data["Bedwars"]["final_deaths_bedwars"],
                        2)
                    sw_wins = player_data["SkyWars"]["wins"]
                    sw_kdr = round(player_data["SkyWars"]["kills"] / player_data["SkyWars"]["deaths"], 2)
                    duels_wlr = round(player_data["Duels"]["wins"] / player_data["Duels"]["losses"], 2)
                    duels_kills = player_data["Duels"]["kills"]

                    # Define dict for eligibility and set each gamemode boolean
                    eligibility = {}
                    eligibility["bedwars"] = False if bw_wins < gvg_requirements["bw_wins"] and bw_fkdr < \
                                                      gvg_requirements[
                                                          "bw_fkdr"] else True
                    eligibility["skywars"] = False if sw_wins < gvg_requirements["sw_wins"] and sw_kdr < \
                                                      gvg_requirements[
                                                          "sw_kdr"] else True
                    eligibility["duels"] = False if duels_wlr < gvg_requirements["duels_wlr"] and duels_kills < \
                                                    gvg_requirements["duels_kills"] else True

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

                    # User is not eligible for any team
                    elif not all(eligibility.values()):
                        embed = discord.Embed(
                            title="You are ineligible for the GvG Team as you do not meet the requirements!",
                            description="If you think this is incorrect, please await staff assistance",
                            color=neg_color)
                        embed.add_field(name="Bedwars Wins", value=f"`{bw_wins}`")
                        embed.add_field(name="Bedwars FKDR", value=f"`{bw_fkdr}`")
                        embed.add_field(name="Skywars Wins", value=f"`{sw_wins}`")
                        embed.add_field(name="Skywars KDR", value=f"`{sw_kdr}`")
                        embed.add_field(name="Duels WLR", value=f"`{duels_wlr}`")
                        embed.add_field(name="Duels Kills", value=f"`{duels_kills}`")
                        await ticket.send(embed=discord.Embed(
                            title="You are ineligible for the GvG Team as you do not meet the requirements!",
                            description="Please await staff assistance for further information!",
                            color=neg_color))

                    # User is eligible for at least one gamemode
                    else:
                        # loop through all GvG gamemodes
                        for mode, req1_name, req1, req2_name, req2 in [["bedwars", "Wins", bw_wins, "FKDR", bw_fkdr],
                                                                       ["skywars", "Wins", sw_wins, "KDR", sw_kdr],
                                                                       ["duels", "WLR", duels_wlr, "Kills",
                                                                        duels_kills]]:
                            # If user is eligible for that gamemode, create embed
                            if eligibility[mode]:
                                embed = discord.Embed(title=f"You are eiligible for the {mode.capitalize()} team!",
                                                      color=neutral_color)
                                embed.set_footer(text="Please await staff assistance for further information!")
                                embed.add_field(name=req1_name, value=f"`{req1}`")
                                embed.add_field(name=req2_name, value=f"`{req2}`")

                                # Send embed and end loop

                    GvGView = discord.ui.View(timeout=None)  # View for staff members to approve/deny the DNKL
                    buttons = (("Accept", "GvG_Application_Positive", discord.enums.ButtonStyle.green, gvg_approve),
                               ("Deny", "GvG_Application_Negative", discord.enums.ButtonStyle.red, gvg_deny))
                    # Loop through the list of roles and add a new button to the view for each role.
                    for button in buttons:
                        # Get the role from the guild by ID.
                        GvGView.add_item(
                            uiutils.Button_Creator(channel=ticket, ign=ign, button=button, author=user, uuid=uuid,
                                                   function=button[3]))

                    await ticket.send("Staff, what do you wish to do with this application?", embed=embed,
                                      view=GvGView)
                if option == f"I want to join {guild_handle}":
                    # Edit category and send info embed with requirements
                    await ticket.edit(name=f"join-request-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories["registrees"]))
                    await ticket.purge(limit=100)
                    await ticket.send(
                        embed=discord.Embed(title=f"{ign} wishes to join Miscellaneous!",
                                            description=f"Please await staff assistance!\nIn the meanwhile, you may explore the Discord!",
                                            color=neutral_color))
                    await interaction.user.add_roles(bot.guest, reason="Registration - Guest")
                if option == f"I want to organize a GvG with {guild_handle}":
                    await ticket.edit(name=f"gvg-request-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories["generic"]))
                    guild = await get_player_guild(uuid)
                    fields = []
                    if not guild:
                        fields.extend(
                            [["What is the name of your guild?", "", discord.InputTextStyle.short, "Guild Name"]])
                        embed = discord.Embed(title="GvG Request", color=neutral_color)
                    else:
                        embed = discord.Embed(
                            title=f"{ign} wishes to organize a GvG with Miscellaneous on behalf of {guild['name']}",
                            description=f"Guild Level: {await get_guild_level(guild['exp'])}",
                            color=neutral_color)
                    fields.extend(
                        [["What are your preferred gamemodes", "", discord.InputTextStyle.short, "Gamemode(s)"],
                         ["Do you have any special rules?", "", discord.InputTextStyle.long, "Rule(s)"],
                         ["Number of Players", "", discord.InputTextStyle.short, "Number of Players"],
                         ["Time & Timezone", "", discord.InputTextStyle.short, "Time & Timezone"]])
                    await interaction.response.send_modal(
                        modal=uiutils.ModalCreator(embed=embed, fields=fields, ign=ign, title="GvG Request"))
                    return
                if option == f"My guild wishes to ally  {guild_handle}":
                    await ticket.edit(name=f"alliance-request-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories["generic"]))
                    guild = await get_player_guild(uuid)
                    fields = []

                    if not guild:
                        fields.extend(
                            [["What is the name of your guild?", "", discord.InputTextStyle.short, "Guild Name"],
                             ["What is your guild's level?", "", discord.InputTextStyle.short, "Guild Level"]])
                        embed = discord.Embed(title="Alliance Request Request", color=neutral_color)
                    else:
                        embed = discord.Embed(
                            title=f"{ign} wishes to ally with Miscellaneous on behalf of {guild['name']}",
                            description=f"Guild Level: {await get_guild_level(guild['exp'])}",
                            color=neutral_color)
                    embed.set_footer(text="Please provide:\nGuild Logo\nGuild Advertisement Message")
                    fields.extend(
                        [["What is the IGN of your guild master?", "", discord.InputTextStyle.short, "Guild Master"],
                         ["What is your guild's preferred gamemode?", "If you don't have one, just say 'None'",
                          discord.InputTextStyle.short, "Guild's Preferred Gamemodes"],
                         [f"Why should we ally with you guys?", "", discord.InputTextStyle.long,
                          f"Benefits of allying with {guild['name']}"]])
                    await interaction.response.send_modal(
                        modal=uiutils.ModalCreator(embed=embed, fields=fields, ign=ign, uuid=uuid,
                                                   title="Alliance Request"))
                    return
                if option == "Other":
                    await ticket.edit(name=f"other-{ign}", topic=f"{interaction.user.id}|",
                                      category=discord.utils.get(interaction.guild.categories,
                                                                 name=ticket_categories["generic"]))
                    await ticket.send(embed=discord.Embed(title="This ticket has been created for an unknown reason!",
                                                          description="Please specify why you have created this ticket!",
                                                          color=neutral_color))

        # Create view and embed, send to ticket
        view = discord.ui.View()
        view.add_item(TicketTypeSelect())
        embed = discord.Embed(title="Why did you make this ticket?",
                              description="Please select your reason from the dropdown given below!",
                              color=neutral_color)
        await ticket.send(embed=embed, view=view)

    # Return ticket for use
    return ticket


async def log_event(title: str, description: str = None):
    embed = discord.Embed(title=title, description=description, color=neutral_color)
    await bot.get_channel(log_channel_id).send(embed=embed)


async def has_tag_perms(user: discord.User):
    return any(role in user.roles for role in bot.tag_allowed_roles)


async def check_tag(tag: str):
    tag = tag.lower()
    with open(r"src/utils/badwords.txt", "r") as f:
        badwords = f.read()

    if tag in badwords.split("\n"):
        return False, "Your tag may not include profanity."
    if not tag.isascii():
        return False, "Your tag may not include special characters unless it's the tag of an ally guild."
    if len(tag) > 6:
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


async def create_transcript(channel: discord.TextChannel, limit: int = None):
    transcript = await chat_exporter.export(channel, limit=limit)
    if not transcript:
        return None

    # Create and return file
    return discord.File(BytesIO(transcript.encode()), filename=f"transcript-{channel.name}.html")


async def dnkl_application(ign: str, uuid: str, channel: discord.TextChannel, author: discord.User, weekly_gexp: int):
    YearView = discord.ui.View()
    buttons = (("Approve", "DNKL_Approve", discord.enums.ButtonStyle.green, dnkl_approve),
               ("Deny", "DNKL_Deny", discord.enums.ButtonStyle.red, dnkl_deny),
               ("Error", "DNKL_Error", discord.enums.ButtonStyle.gray, dnkl_error))
    YearView.add_item(uiutils.StartYearSelect(channel=channel, ign=ign, uuid=uuid,
                                              weekly_gexp=weekly_gexp, buttons=buttons))  # Year Selection Dropdown
    embed = discord.Embed(title=f"In which year will {ign}'s inactivity begin?",
                          color=neutral_color)
    await channel.send(embed=embed, view=YearView)


async def get_ticket_properties(channel: discord.TextChannel):
    topic = channel.topic
    if not topic or '|' not in topic:
        return None
    return topic.split('|')


async def find_player_score(uuid):
    start_stats = await select_one("SELECT start_data FROM tournament WHERE uuid = (?)", (uuid,))
    week_number = await get_week_number()
    player_data = await get_hypixel_player(uuid=uuid)
    name = player_data["playername"]

    current_stats = await get_game_data(player_data)
    current_weekly_stats = None

    week1_stats = (await select_one("SELECT week1_data FROM tournament WHERE uuid = (?)", (uuid,)))[0]
    week2_stats = (await select_one("SELECT week2_data FROM tournament WHERE uuid = (?)", (uuid,)))[0]
    week3_stats = (await select_one("SELECT week3_data FROM tournament WHERE uuid = (?)", (uuid,)))[0]
    week3_end_stats = (await select_one("SELECT week3_end_data FROM tournament WHERE uuid = (?)", (uuid,)))[0]
    end_stats = (await select_one("SELECT end_data FROM tournament WHERE uuid = (?)", (uuid,)))[0]

    if week_number == -1:
        week1_points = await get_points_from_data(week1_stats, week2_stats)
        week2_points = await get_points_from_data(week2_stats, week3_stats)
        week3_points = await get_points_from_data(week3_stats, week3_end_stats)
        overall_points = await get_points_from_data(start_stats, end_stats)
    elif week_number >= 3:
        week1_points = await get_points_from_data(week1_stats, week2_stats)
        week2_points = await get_points_from_data(week2_stats, week3_stats)
        week3_points = await get_points_from_data(week3_stats, current_stats)
        overall_points = await get_points_from_data(start_stats, current_stats)
    elif week_number >= 2:
        week1_points = await get_points_from_data(week1_stats, week2_stats)
        week2_points = await get_points_from_data(week2_stats, current_stats)
        week3_points = None
        overall_points = await get_points_from_data(start_stats, current_stats)
    elif week_number >= 1:
        week1_points = await get_points_from_data(week1_stats, current_stats)
        week2_points = None
        week3_points = None
        overall_points = await get_points_from_data(start_stats, current_stats)

    scores_embed = discord.Embed(title=f"{name}'s Tournament Points",
                                 url=f"https://plancke.io/hypixel/player/stats/{name}", color=neutral_color)
    scores_embed.set_author(name=f"Miscellaneous Guild Experience Tournament",
                            url=f"https://discord.com/channels/522586672148381726/522861704921481229/1174807396686770339")
    scores_embed.set_thumbnail(url=f"https://minotar.net/helm/{uuid}/512.png")
    scores_embed.add_field(name="Week 1", value=f"{week1_points} points", inline=False)

    if week2_points:
        scores_embed.add_field(name="Week 2", value=f"{week2_points} points", inline=False)
    if week3_points:
        scores_embed.add_field(name="Week 3", value=f"{week3_points} points", inline=False)

    scores_embed.add_field(name="Overall", value=f"{overall_points} points", inline=False)

    return scores_embed


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
    bot.processing = discord.utils.get(bot.guild.roles, name="Processing")
    bot.guest = discord.utils.get(bot.guild.roles, name="Guest")
    bot.member_role = discord.utils.get(bot.guild.roles, name="Member")
    bot.active_role = discord.utils.get(bot.guild.roles, name="Active")
    bot.ally = discord.utils.get(bot.guild.roles, name="Ally")
    bot.server_booster = discord.utils.get(bot.guild.roles, name="Server Booster")
    bot.rich_kid = discord.utils.get(bot.guild.roles, name="Rich Kid")
    bot.gvg = discord.utils.get(bot.guild.roles, name="GvG Team")
    bot.giveaways_events = discord.utils.get(bot.guild.roles, name="Giveaways/Events")
    bot.veteran = discord.utils.get(bot.guild.roles, name="Veteran")
    bot.tag_allowed_roles = (bot.active_role, bot.staff, bot.former_staff,
                             bot.server_booster, bot.rich_kid, bot.gvg, bot.veteran)

    from src.utils.discord_utils import name_grabber
    bot.staff_names = [(await get_mojang_profile(await name_grabber(member)))[0] for member in bot.staff.members]

    from src.utils.loop_utils import check_giveaways, send_gexp_lb, update_invites
    check_giveaways.start()
    send_gexp_lb.start()
    update_invites.start()


@after_cache_ready.before_loop
async def before_cache_loop():
    print("Waiting for cache...")
    await bot.wait_until_ready()
    print("Cache filled")
