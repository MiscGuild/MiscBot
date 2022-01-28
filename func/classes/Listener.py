# The following file contains: on_member_join, on_error, on_command_error, on_guild_channel_create, reactionroles, tickets

import traceback

import discord
from __main__ import bot
from discord.ext import commands
from discord.ui import Select, View, Button
from func.utils.consts import (error_channel_id, invalid_command_embed,
                               member_not_found_embed,
                               missing_permissions_embed, missing_role_embed,
                               neutral_color, not_owner_embed,
                               registration_channel_id, registration_embed)
from func.utils.discord_utils import create_ticket
from func.utils.request_utils import get_jpg_file


class Listener:
    def __init__(self, res):
        self.obj = res

    async def on_member_join(member):
        # Remove user's speaking perms and send info embed
        await member.add_roles(bot.new_member_role)
        await bot.get_channel(registration_channel_id).send(embed=registration_embed)

    async def on_error(event):
        # Grabs the error being handled, formats it and sends it to the error channel
        tb = traceback.format_exc()
        await bot.get_channel(error_channel_id).send(f"Ignoring exception in event {event}:\n```py\n{tb}\n```")

    async def on_command_error(ctx, error):
        # Prevents commands with local handlers or cogs with overwrritten on_command_errors being handled here
        if isinstance(error, commands.CommandNotFound):
            return await ctx.send(embed=invalid_command_embed)
        elif ctx.command.has_error_handler() or ctx.cog.has_error_handler():
            return

        # Checks for the original exception raised and send to CommandInvokeError
        error = getattr(error, "original", error)

        # Catch a series of common errors
        if isinstance(error, commands.NotOwner):
            await ctx.send(embed=not_owner_embed)
        elif isinstance(error, commands.MissingRole):
            await ctx.send(embed=missing_role_embed)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=missing_permissions_embed)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=member_not_found_embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            usage = f"{ctx.prefix}{ctx.command.name}"
            for key, value in ctx.command.clean_params.items():
                if not value.default:
                    usage += " [" + key + "]"
                else:
                    usage += " <" + key + ">"
            embed = discord.Embed(title=f" arguments",
                                description=f"Command usage:\n`{usage}`\nFor more help, see `{ctx.prefix}help {ctx.command}`",
                                color=0xDE3163)
            await ctx.send(embed=embed)

        # All other errors get sent to the error channel
        else:
            tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            if len(tb) <= 2000:
                await bot.get_channel(error_channel_id).send(f"Ignoring exception in command {ctx.command}:\n```py\n{tb}\n```")
            else:
                await bot.error_channel.send(
                    f"```An error occurred in command '{ctx.command}' that could not be sent in this channel, check the console for the traceback. \n\n'{error}'```")
                print("The below exception could not be sent to the error channel:")
                print(tb)

    # async def on_guild_channel_create():

    async def reactionroles():
        # Reaction roles
        reaction_roles_embed = discord.Embed(title="To get your desired role, click its respective button!",
                                            description="🪓 __**SkyBlock**__\nGives you the access to the SkyBlock category!\n\n"
                                                        "🕹 __**Minigames**__\nAllows you to play some Discord minigames!\n\n"
                                                        "❓  __**QOTD Ping**__\nThe staff team will mention this role when there's a new question of the day!\n\n"
                                                        "🎉 __**Giveaways/Events**__\nReact so you don't miss any giveaway or event\n\n"
                                                        "📖 __**Storytime Pings**__\nGet pinged whenever a storytime happens",
                                            color=neutral_color)

        class ReactionRoleButton(Button):
            def __init__(self, label: str, emoji: str):
                super().__init__(label=label, emoji=emoji)

            async def callback(self, interaction: discord.Interaction):
                if not isinstance(interaction.user, discord.Member): return

                role = discord.utils.get(interaction.guild.roles, name=self.label)
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role, reason="Pressed Button, removed role")
                    await interaction.response.send_message(f"Removed {self.label} role from you.", ephemeral=True)
                else:
                    await interaction.user.add_roles(role, reason="Pressed Button, added role")
                    await interaction.response.send_message(f"Added {self.label} role to you.", ephemeral=True)

        class ReactionRolesView(View):
            def __init__(self):
                super().__init__()

                for name, emoji, in [["Skyblock", "🪓",],
                                    ["Minigames", "🕹"],
                                    ["QOTD Ping", "❓"],
                                    ["Giveaways/Events", "🎉"],
                                    ["Storytimes", "📖"]]:
                    self.add_item(ReactionRoleButton(name, emoji))

        # Pronouns
        pronouns_embed = discord.Embed(title="Please select your pronouns",
                                        description="👨 He/Him"
                                                    "\n👩 She/Her"
                                                    "\n🏳‍🌈 They/Them"
                                                    "\n❓ Other",
                                        color=neutral_color)

        class PronounsSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Select your pronouns (Max 1)", min_values=1, max_values=1, options=[
                    discord.SelectOption(label="He/Him", emoji="👨"),
                    discord.SelectOption(label="She/Her", emoji="👩"),
                    discord.SelectOption(label="They/Them", emoji="🏳️‍🌈"),
                    discord.SelectOption(label="Other", emoji="❓"),
                ])

            async def callback(self, interaction: discord.Interaction):
                if not isinstance(interaction.user, discord.Member): return
                label = list(interaction.data.values())[0][0] if interaction.data.values() else None
                
                # User selected none, remove all roles
                if label == None:
                    await interaction.user.remove_roles(*[discord.utils.get(interaction.guild.roles, name=item.label) for item in self.options])
                    await interaction.respond(content=f"Removed all pronoun roles!")
                else:
                    # Fetch role
                    role = discord.utils.get(interaction.guild.roles, name=label)
                    # Remove single role if user already has it
                    if role in interaction.user.roles:
                        await interaction.user.remove_roles(role)
                        await interaction.respond(content=f"Removed {label}")
                    # Add the clicked role and remove all others
                    else:
                        await interaction.user.remove_roles(*[discord.utils.get(interaction.guild.roles, name=item.label) for item in self.options])
                        await interaction.user.add_roles(role)
                        await interaction.respond(content=f"Added {label}")

        pronouns_view = View(timeout=10.0)
        pronouns_view.add_item(PronounsSelect())

        return [reaction_roles_embed, ReactionRolesView()], [pronouns_embed, pronouns_view]

    async def tickets():
        embed = discord.Embed(title="Tickets",
                    description="""Tickets can be created for any of the following reasons:
                                > Do-not-kick-list Application
                                > Discord Nick/Role Change
                                > Problems/Queries/Complaints
                                > Player Report
                                > Milestone
                                > Staff Application
                                > Event
                                > Other
                                Once you have created a ticket by clicking the button, you will be linked to your ticket\n
                                The bot will ask you to choose the reason behind the creation of your ticket from a given list. Choose the appropriate reason and then proceed!\n
                                Once you have created your ticket, staff will respond within 24 hours.""",
                    color=neutral_color)

        embed.add_field(name="Do-not-kick-list Application",
                        value="You  must have a valid reason for applying and also meet the DNKL requiremnets.\n"
                              "Accepted Reasons:\n"
                              "> School\n"
                              "> Medical Reasons\n"
                              "> Situations out of your control\n"
                              "> Vacation\n\n"
                              "If your account is banned, it may be temporarily kicked until unbanned.",
                        inline=False)

        embed.add_field(name="Player Report",
                        value="When reporting a player, you're expected to explain the situation in maximum detail. Providing the following is considered the bare minimum:\n"
                              "> Username of the accused\n"
                              "> Explanantion of the offense\n"
                              "> Time of offense\n"
                              "> Proof of offense\n"
                              "If you wish to report a staff member, please DM the acting guild master with your report.",
                        inline=False)

        embed.add_field(name="Milestone",
                        value="You'll be prompted to present the milestone you've achieved and proof of its occurence. "
                              "Staff will review your milestone and if accepted, will be include it in the next week's milestone post!",
                        inline=False)

        embed.add_field(name="Staff Application",
                        value="After you're done with your application, the staff team will review your it and make a decision to accept or deny it.",
                        inline=False)

        embed.set_thumbnail(
            url=f"https://images-ext-1.discordapp.net/external/ziYSZZe7dPyKDYLxA1s2jqpKi-kdCvPFpPaz3zft-wo/%3Fwidth%3D671%26height%3D671/https/media.discordapp.net/attachments/523227151240134664/803843877999607818/misc.png")

        image = await get_jpg_file("https://media.discordapp.net/attachments/650248396480970782/873866686049189898/tickets.jpg")

        class TicketView(View):
            @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.blurple, emoji="✉️")

            async def callback(self, button, interaction: discord.Interaction):
                ticket = await create_ticket(interaction.user, f"ticket-{interaction.user.display_name}")
                await interaction.response.send_message(f"Click the following link to go to your ticket! <#{ticket.id}>", ephemeral=True)

        return image, embed, TicketView()
