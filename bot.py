import discord, toml, aiohttp, asyncio, json, sys
from discord.ext import commands, tasks
from cogs.utils import hypixel
import logging

logging.basicConfig(level=logging.INFO)

config = toml.load('config.toml')

intents = discord.Intents.default()
intents.reactions = True
intents.members = True

client = commands.Bot(command_prefix=commands.when_mentioned_or(config['bot']['prefix']), intents=intents, status=discord.Status.idle, activity=discord.Game(config['bot']['status']))
client.config = config
client.token = config['bot']['token']
client.api_tokens = config['hypixel']['api_keys']
client.owner_id = config['bot']['ownerID']
client.resident_req = int(50000)
client.active = int(275000)
client.inactive = int(100000)
client.dnkl = int(200000)
client.new_member = int(25000)
client.error_channel = None

class HelpCommand(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            embed = discord.Embed(description=page, color=0x8368ff)
            await destination.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=self.get_command_signature(command), color=0x8368ff)
        embed.add_field(name="Help", value=command.help)
        alias = command.aliases
        if alias:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

client.help_command = HelpCommand(command_attrs={'hidden': True})

initial_extensions = ['cogs.fun', 'cogs.hypixel', 'cogs.mod', 'cogs.staff', 'cogs.ticket', 'cogs.owner']

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            client.load_extension(extension)
            print(f'{extension} Loaded!')
        except Exception as e:
            print(f'Failed to load extention {extension}', file=sys.stderr)

@client.event
async def on_ready():
    try:
        print('The Bot is up and running!')

        with open('dnkl.json', 'r') as f:
            data = str(f.read()).replace("'", '"')
        with open('dnkl.json', 'w') as f:
            f.write(data)
    except Exception as e:
        print(e)

# Error Message
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(title='Your soul lacks the strength to utilize this command!',
                                    description="You are not the owner of this bot!", color=0xff0000)
            await ctx.send(embed=embed)

@client.event
async def on_member_join(member):
    try:
        channel = client.get_channel(714882620001091585)
        role = discord.utils.get(member.guild.roles, name="New Member")
        await member.add_roles(role)

        embed = discord.Embed(title=f"Welcome to the Miscellaneous Discord, {member.name}", color=0x8368ff)
        embed.add_field(name="Register using the following command:", value="**,register** `Your Minecraft Name`", inline=False)
        embed.set_footer(text="Example:\n,register John")

        await channel.send(embed=embed)

    except Exception as e:
        print(e)

"------------------------------------------------------------------------------------------------------------------Tickets------------------------------------------------------------------------------------------------------"


# Ticket Handling
@client.event
async def on_guild_channel_create(channel):
    try:
        while True:
            if channel.category.name == "RTickets":
                embed = discord.Embed(title="Do you wish to join Miscellaneous in-game?", color=0x8368ff)
                embed.add_field(name="If you do", value="Type `Yes`")
                embed.add_field(name="If you don't", value="Type `No`")
                await channel.send(embed=embed)
                reply = await client.wait_for('message', check=lambda x: x.channel == channel)
                reply = reply.content
                reply = reply.capitalize()
                try:
                    if reply in ('Yes', 'Yeah', 'Ye', 'Yea'):
                        await channel.send(
                            'Alright. Kindly wait until staff get in contact with you.'
                            '\n`You are recommended to leave your present guild (if any) so that staff can invite you to Miscellaneous ASAP`'
                            '\nIf you get in the guild and want the member role in the discord, use ,sync `Your Minecraft Name` ! ')
                        await asyncio.sleep(3)
                        embed1 = discord.Embed(title="Miscellaneous Guild Requirements",
                                               description="These requirements are subject to change!",
                                               color=0x8368ff)
                        embed1.set_author(name="While you wait, kindly take a look a the guild requirements!")
                        embed1.add_field(name="Active",
                                         value=f"•  {format(client.active,',d')} Weekly Guild Experience",
                                         inline=False)
                        embed1.add_field(name="Do Not Kick List Eligibility",
                                         value=f"•  {format(client.dnkl,',d')} Weekly Guild Experience",
                                         inline=False)
                        embed1.add_field(name="Resident", value=f"•  {format(client.resident_req,',d')} Weekly Guild Experience",
                                         inline=False)
                        embed1.add_field(name="Member",
                                         value=f"•  {format(client.inactive,',d')} Weekly Guild Experience",
                                         inline=False)
                        embed1.add_field(name="New Member",
                                         value=f"•  {format(client.new_member,',d')} Daily Guild Experience",
                                         inline=False)
                        embed1.set_footer(text="You are considered a New Member for the first 7 days after joining the guild"
                                               "\nIf you fail to meet the New Member/Member requirements, you will be kicked!")
                        await channel.send(embed=embed1)
                        break
                    elif reply in ('No', 'Nah', 'Nope'):
                        embed = discord.Embed(title="Did you join the discord to organize a GvG with Miscellaneous?",
                                              color=0x8368ff)
                        embed.add_field(name="If yes", value="Type `Yes`")
                        embed.add_field(name="If not", value="Type `No`")
                        await channel.send(embed=embed)
                        noreply = await client.wait_for('message', check=lambda x: x.channel == channel)
                        noreply = noreply.content
                        noreply = noreply.capitalize()
                        if noreply in ('Yes', 'Yeah', 'Ye', 'Yea'):
                            embed = discord.Embed(title="In order to organize a GvG with miscellaneous, "
                                                        "kindly list the following and await staff assistance!",
                                                  description="• Your guild's plancke"
                                                              "\n• Your preferred gamemode"
                                                              "\n• Your preferred timezone"
                                                              "\n• Number of players",
                                                  color=0x8368ff)
                            embed.set_footer(text="Upon completion of all of the above, kindly await staff assistance!")
                            await channel.send(embed=embed)
                            break
                        elif noreply == "No":
                            await channel.send(
                                "**Okay, kindly specify your reason behind joining the Miscellaneous discord and then await staff help!**")
                            break
                        else:
                            embed = discord.Embed(title="My massive computer brain thinks you made a mistake.",
                                                  color=0xff0000)
                            embed.add_field(name="If this is true", value="Type `Yes`", inline=False)
                            embed.add_field(name="If this is false", value="Type `No`", inline=False)
                            await channel.send(embed=embed)
                            errorreply = await client.wait_for('message', check=lambda x: x.channel == channel)
                            errorreply = errorreply.content
                            errorreply = errorreply.capitalize()
                            if errorreply in ('Yes', 'Yeah', 'Ye', 'Yea'):
                                embed = discord.Embed(title="Great! Let's start over!",
                                                      color=0x8368ff)
                                await channel.send(embed=embed)
                            else:
                                embed = discord.Embed(title="Alright! Kindly specify why you joined the discord and await staff assistance!",
                                                      color=0x8368ff)
                                await channel.send(embed=embed)
                                break
                    else:
                        embed = discord.Embed(title="My massive computer brain thinks you made a mistake.",
                                              color=0xff0000)
                        embed.add_field(name="If this is true", value="Type `Yes`", inline=False)
                        embed.add_field(name="If this is false", value="Type `No`", inline=False)
                        await channel.send(embed=embed)
                        errorreply = await client.wait_for('message', check=lambda x: x.channel == channel)
                        errorreply = errorreply.content
                        errorreply = errorreply.capitalize()
                        if errorreply in ('Yes', 'Yeah', 'Ye', 'Yea'):
                            embed = discord.Embed(title="Great! Let's start over!",
                                                  color=0x8368ff)
                            await channel.send(embed=embed)
                        else:
                            embed = discord.Embed(title="Alright! Kindly specify why you joined the discord and await staff assistance!",
                                                  color=0x8368ff)
                            await channel.send(embed=embed)
                            break
                except Exception as e:
                    embed = discord.Embed(title="Alright! Kindly specify why you joined the discord and await staff assistance!",
                                          color=0x8368ff)
                    await channel.send(embed=embed)
                    print(e)
                    await client.error_channel.send(
                        f"Error in {channel.name} while dealing with registration tickets\n{e}\n<@!326399363943497728>")

                    break
            elif channel.category.name == '🎫 Ticket Section':
                await asyncio.sleep(3)
                embed = discord.Embed(title="What's your reason behind creating this ticket?",
                                      description="Please reply with your reason from the list given below!",
                                      color=0x8368ff)
                embed.add_field(name="Do-Not-Kick-List", value="Reply with `DNKL`", inline=False)
                embed.add_field(name="Role/Username Change", value="Reply with `Role`", inline=False)
                embed.add_field(name="Report", value="Reply with `Report`", inline=False)
                embed.add_field(name="Problem/Query/Complaint/Suggestion", value="Reply with `General`", inline=False)
                embed.add_field(name="Milestone", value="Reply with `Milestone`", inline=False)
                embed.add_field(name="Staff Application", value="Reply with `Staff`", inline=False)
                embed.add_field(name="GvG Application", value="Reply with `GvG`", inline=False)
                embed.add_field(name="Event", value="Reply with `Event`",inline=False)
                embed.add_field(name="Other", value="Reply with `Other`", inline=False)
                await channel.send(embed=embed)
                reply = await client.wait_for('message', check=lambda x: x.channel == channel)
                author = reply.author
                name = author.nick
                if name is None:
                    name = author.name
                reply = reply.content
                reply = reply.capitalize()

                if reply in ("Dnkl", "Do not kick list", "Do-Not-Kick-List"):

                    if name is None:
                        x = author.name
                        name = x
                    await channel.edit(name=f"DNKL-{name}", category=discord.utils.get(channel.guild.categories, name="DNKL"))
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://api.mojang.com/users/profiles/minecraft/{name}') as resp:
                            request = resp
                        if request.status != 200:
                            await channel.send('Unknown IGN!')
                        request = await request.json()
                        await session.close()
                    name = request['name']
                    uuid = request['id']
                    api = hypixel.get_api()
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://api.hypixel.net/guild?key={api}&player={uuid}') as resp:
                            data = await resp.json()
                            await session.close()
                    gname = data['guild']['name']
                    if gname != 'Miscellaneous':
                        await channel.send('You are not in Miscellaneous')
                    if len(data) < 2:
                        print("The user is not in any guild!")
                        await channel.send('You are not in any guild')
                    else:
                        for member in data["guild"]["members"]:
                            if uuid == member["uuid"]:
                                member = member
                                totalexp = member['expHistory']
                                totalexp = int(sum(totalexp.values()))
                                if totalexp >= 200000:
                                    eligiblity = True
                                else:
                                    eligiblity = False
                                totalexp = (format(totalexp, ',d'))
                                if eligiblity is False:
                                    embed = discord.Embed(title=name,
                                                            url=f'https://visage.surgeplay.com/full/832/{uuid}',
                                                            color=0xff3333)
                                    embed.set_thumbnail(
                                        url=f'https://visage.surgeplay.com/full/832/{uuid}')
                                    embed.set_author(name="Do-not-kick-list: Eligibility Check")
                                    embed.set_footer(text="Miscellaneous Bot | Coded by Rowdies")
                                    embed.add_field(name="You are not eligible to apply for the do not kick list.",
                                                    value=f"You need a minimum of {format(client.dnkl,',d')} weekly guild experience."
                                                            f"\n You have {totalexp} weekly guild experience.",
                                                    inline=True)
                                    await channel.send(embed=embed)
                                    await channel.send(
                                        "Even though you do not meet the requirements, "
                                        "you might still be accepted so we shall proceed with the application process!")

                                    await channel.send("**When will your inactivity begin? (Start date) (DD/MM/YYYY)**")
                                    start = await client.wait_for('message', check=lambda x: x.author == author and x.channel == channel)
                                    start = start.content
                                    await channel.send('**When will your inactivity end? (End date) (DD/MM/YYYY)**')
                                    end = await client.wait_for('message', check=lambda x: x.author == author and x.channel == channel)
                                    end = end.content
                                    await channel.send("**What's the reason behind your inactivity?**")
                                    reason = await client.wait_for('message', check=lambda x: x.author == author and x.channel == channel)
                                    reason = reason.content

                                    await channel.send(
                                        f"Alright! Kindly await staff assistance!"
                                        f"\n**Start:** {start}"
                                        f"\n**End:** {end}"
                                        f"\n**Reason:** {reason}"
                                        f"\n*If you made an error, kindly notify staff by typing after this message*"
                                        f"\n\n||,dnkladd {name} {author.mention} {start} {end} {reason}||"
                                        )

                                else:
                                    embed = discord.Embed(title=name,
                                                            url=f'https://visage.surgeplay.com/full/832/{uuid}',
                                                            color=0x333cff)
                                    embed.set_thumbnail(
                                        url=f'https://visage.surgeplay.com/full/832/{uuid}')
                                    embed.set_author(name='Do-not-kick-list: Eligibility Check')
                                    embed.set_footer(text="Miscellaneous Bot | Coded by Rowdies")
                                    embed.add_field(name="You are eligible to apply for the do not kick list.",
                                                    value=f"You meet the minimum of {format(client.dnkl,',d')} weekly guild experience."
                                                            f"\n You have {totalexp} weekly guild experience.",
                                                    inline=True)
                                    await channel.send(embed=embed)

                                    await channel.send("**When will your inactivity begin? (Start date) (DD/MM/YYYY)**")
                                    start = await client.wait_for('message', check=lambda x: x.author == author and x.channel == channel)
                                    start = start.content
                                    await channel.send('**When will your inactivity end? (End date) (DD/MM/YYYY)**')
                                    end = await client.wait_for('message', check=lambda x: x.author == author and x.channel == channel)
                                    end = end.content
                                    await channel.send("**What's the reason behind your inactivity?**")
                                    reason = await client.wait_for('message', check=lambda x: x.author == author and x.channel == channel)
                                    reason = reason.content

                                    await channel.send(
                                        f"Alright! Kindly await staff assistance!"
                                        f"\n**Start:** {start}"
                                        f"\n**End:** {end}"
                                        f"\n**Reason:** {reason}"
                                        f"\n*If you made an error, kindly notify staff by typing after this message*"
                                        f"\n\n||,dnkladd {name} {author.mention} {start} {end} {reason}||"
                                        )

                                    await channel.send("**Staff, what do you wish to do with this dnkl request?**"
                                                        f"\nReply with `Approve` to approve the do-not-kick-list request"
                                                        f"\nReply with `Deny` to deny the do-not-kick-list request"
                                                        f"\nReply with `Error` if the user made an error while applying for the do not kick list")

                                    while True:
                                        action = await client.wait_for('message', check=lambda
                                            x: staff in x.author.roles)
                                        action = (action.content).capitalize()
                                        if action in ('Approve','Deny','Error'):
                                            if action == "Approve":
                                                a, b, c = start.split('/')
                                                p, q, r = end.split('/')
                                                ign = hypixel.get_dispname(name)
                                                rank = hypixel.get_rank(name)
                                                dates = {1: "January", 2: "February", 3: "March", 4: "April",
                                                            5: "May",
                                                            6: "June", 7: "July", 8: "August", 9: "September",
                                                            10: "October", 11: "November", 12: "December"}
                                                start_month = dates.get(int(b))
                                                end_month = dates.get(int(q))

                                                embed = discord.Embed(title=f"{rank} {ign}",
                                                                        url=f'https://plancke.io/hypixel/player/stats/{ign}',
                                                                        color=0x0ffff)
                                                embed.set_thumbnail(
                                                    url=f'https://visage.surgeplay.com/full/832/{uuid}')
                                                embed.add_field(name="IGN:", value=f"{ign}", inline=False)
                                                embed.add_field(name="Start:", value=f"{a} {start_month} {c}",
                                                                inline=False)
                                                embed.add_field(name="End:", value=f"{p} {end_month} {r}",
                                                                inline=False)
                                                embed.add_field(name="Reason", value=f"{reason}", inline=False)
                                                embed.set_author(name="Do not kick list")
                                                await channel.channel.purge(limit=1)
                                                dnkl_channel = client.get_channel(629564802812870657)
                                                message = await dnkl_channel.send(embed=embed)

                                                with open('dnkl.json') as f:
                                                    data = json.load(f)
                                                dnkl_dict = {ign: message.id}

                                                data.update(dnkl_dict)
                                                with open('dnkl.json', 'w') as f:
                                                    json.dump(data, f)
                                                break

                                            elif action == "Deny":
                                                await channel.send("**This do not kick list request has been denied!")

                                            elif action == "Error":
                                                await channel.send(
                                                    "**What is the name of the user you wish to add to the do not kick list?**")

                                                name = await client.wait_for('message', check=lambda
                                                    x: x.channel == channel.channel)
                                                name = name.content
                                                ign = hypixel.get_dispname(name)
                                                rank = hypixel.get_rank(name)
                                                async with aiohttp.ClientSession() as session:
                                                    async with session.get(f'https://api.hypixel.net/guild?key={api}&player={uuid}') as resp:
                                                        request = await resp.json()
                                                        uuid = request['id']
                                                        with open('dnkl.json') as f:
                                                            data = json.load(f)
                                                        if resp.status != 200:
                                                            await channel.send('Unknown IGN!')
                                                        else:
                                                            await channel.send("**What is the start date?** (DD/MM/YYYY)")
                                                            start_date = await client.wait_for('message',
                                                                                                check=lambda
                                                                                                    x: x.channel == channel.channel)
                                                            start_date = start_date.content
                                                            await channel.send("**What is the end date?** (DD/MM/YYYY)")
                                                            end_date = await client.wait_for('message',
                                                                                                check=lambda
                                                                                                    x: x.channel == channel.channel)
                                                            end_date = end_date.content
                                                            a, b, c = start_date.split('/')
                                                            p, q, r = end_date.split('/')

                                                            await channel.send("**What's the reason for inactivity?**")
                                                            reason = await client.wait_for('message',
                                                                                                check=lambda
                                                                                                    x: x.channel == channel.channel)
                                                            reason = reason.content

                                                            if int(b) > 12:
                                                                embed = discord.Embed(title='Please enter a valid date!',
                                                                                        description="`DD/MM/YYYY`",
                                                                                        color=0xff0000)
                                                                await channel.send(embed=embed)
                                                            if int(q) > 12:
                                                                embed = discord.Embed(title='Please enter a valid date!',
                                                                                        description="`DD/MM/YYYY`",
                                                                                        color=0xff0000)
                                                                await channel.send(embed=embed)
                                                            if int(b) & int(q) <= 12:
                                                                dates = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May",
                                                                            6: "June", 7: "July", 8: "August", 9: "September",
                                                                            10: "October", 11: "November", 12: "December"}
                                                                start_month = dates.get(int(b))
                                                                end_month = dates.get(int(q))

                                                                embed = discord.Embed(title=f"{rank} {ign}",
                                                                                        url=f'https://plancke.io/hypixel/player/stats/{ign}',
                                                                                        color=0x0ffff)
                                                                embed.set_thumbnail(url=f'https://visage.surgeplay.com/full/832/{uuid}')
                                                                embed.add_field(name="IGN:", value=f"{ign}", inline=False)
                                                                embed.add_field(name="Start:", value=f"{a} {start_month} {c}",
                                                                                inline=False)
                                                                embed.add_field(name="End:", value=f"{p} {end_month} {r}", inline=False)
                                                                embed.add_field(name="Reason", value=f"{reason}", inline=False)
                                                                embed.set_author(name="Do not kick list")
                                                                await channel.channel.purge(limit=1)
                                                                dnkl_channel = client.get_channel(629564802812870657)
                                                                message = await dnkl_channel.send(embed=embed)


                                                                dnkl_dict = {ign: message.id}

                                                                data.update(dnkl_dict)
                                                                with open('dnkl.json', 'w') as f:
                                                                    json.dump(data, f)
                                                        await session.close()
                                        else:
                                            continue


                    break

                elif reply in ("Role", "Username", "Name"):
                    await channel.edit(name=f"Role/NameChange-{name}",category=discord.utils.get(channel.guild.categories, name="OTHER"))
                    await channel.send('What is your minecraft username?')
                    role_reply = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                    name = role_reply.content
                    ign = hypixel.get_dispname(name)
                    if ign is None:
                        await channel.send('Please enter a valid ign!')
                        await channel.send("I'll restart the process. If you think I made an error, select 'Other' upon restart")
                    else:
                        guild_name = hypixel.get_guild(ign)
                        guest = discord.utils.get(channel.guild.roles, name="Guest")
                        member = discord.utils.get(channel.guild.roles, name="Member")
                        awaiting_app = discord.utils.get(channel.guild.roles, name="Awaiting Approval")
                        xl_ally = discord.utils.get(channel.guild.roles, name="XL - Ally")
                        await author.edit(nick=ign)
                        if guild_name == "Miscellaneous":
                            await author.remove_roles(guest, awaiting_app)
                            await author.add_roles(member)
                            embed = discord.Embed(title="Your nick and role was successfully changed!",
                                                  description="await staff assistance.",
                                                  color=0x8368ff)
                            embed.set_footer(text="Member of Miscellaneous"
                                                  "\n• Guest & Awaiting Approval were removed"
                                                  "\n• Member was given")
                            await channel.send(embed=embed)

                        elif guild_name == "XL":
                            await author.remove_roles(member, awaiting_app)
                            await author.add_roles(guest, xl_ally)
                            embed = discord.Embed(title="Your nick and role was successfully changed!",
                                                  description="If this wasn't the change you anticipated, "
                                                              "await staff assistance.",
                                                  color=0x8368ff)
                            embed.set_footer(text="Member of XL"
                                                  "\n• Member & Awaiting Approval were removed"
                                                  "\n• Guest & XL - Ally were given")
                            await channel.send(embed=embed)

                        elif guild_name not in ("Miscellaneous","XL"):
                            if str(channel.channel.category.name) == "RTickets":
                                await channel.send("You aren't in Miscellaneous in-game. Kindly await staff assistance!")
                            else:
                                await author.remove_roles(member,awaiting_app)
                                await author.add_roles(guest)
                                embed = discord.Embed(title="Your nick and role was successfully changed!",
                                                      description="If this wasn't the change you anticipated, "
                                                                  "await staff assistance.",
                                                      color=0x8368ff)
                                embed.set_footer(text=f"Member of {guild_name}"
                                                      f"\n• Member & Awaiting Approval were removed"
                                                      f"\n• Guest was given")
                                await channel.send(embed=embed)

                elif reply in "Report":
                    await channel.edit(name=f"Report-{name}", category=discord.utils.get(channel.guild.categories, name="REPORTS"))
                    await channel.send(
                        "Alright. Please provide adequate details about the user and await staff assistance!")
                    break
                elif reply in ("General", "Problem", "Query", "Complaint", "Suggestion"):
                    await channel.edit(name=f"General-{name}", category=discord.utils.get(channel.guild.categories, name="OTHER"))
                    await channel.send(
                        "Alright. Kindly specify the reason you created this ticket and wait for staff assistance!")
                    break
                elif reply == "Milestone":
                    await channel.edit(name=f"Milestone-{name}", category=discord.utils.get(channel.guild.categories, name="MILESTONES"))
                    await channel.send(
                        "Kindly provide a screenshot followed by a message specifying your milestone and then await staff assistance!")
                    break
                elif reply in ('Staff', 'Staff Application', 'Staff App'):
                    embed = discord.Embed(title="To be eligible to apply for staff,"
                                                " you must meet the following requirements.",
                                          description="• You must be older than 13 years."
                                                      "\n• You must have enough knowledge about the bots in this Discord."
                                                      "\n• You must be active both on Hypixel and in the guild Discord."
                                                      "\n• You must have a good reputation amongst guild members.",
                                          color=0x4b89e4)
                    await channel.send(embed=embed)
                    await channel.send("**Do you meet these requirements? (Yes/No)**")

                    reqs = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                    reqs = reqs.content
                    reqs = reqs.capitalize()

                    if reqs in ('Yes', 'Ye', 'Yup', 'Y', 'Yeah', 'Yus'):
                        embed = discord.Embed(title="Does your discord nick match your Minecraft Username?",
                                              description="Kindly reply with a Yes or No",
                                              color=0x4b89e4)
                        await channel.send(embed=embed)
                        nickmatching = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                        nickmatching = nickmatching.content
                        nickmatching = nickmatching.capitalize()
                        if nickmatching in ('Yes', 'Ye', 'Yup', 'Y', 'Yeah', 'Yus'):
                            if name is None:
                                x = author.name
                                name = x
                            async with aiohttp.ClientSession() as session:
                                async with session.get(f'https://api.mojang.com/users/profiles/minecraft/{name}') as resp:
                                    request = await resp.json()
                                    await session.close()
                            uuid = request['id']
                            await channel.edit(name=f"Staff-Application-{name}", category=discord.utils.get(channel.guild.categories, name="OTHER"))
                            '''AGE'''
                            embed = discord.Embed(title="What is your age?",
                                                  description="Kindly reply with a number",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            age = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            age = age.content

                            '''VETERENCY'''
                            embed = discord.Embed(title="For how long have you been in Miscellaneous?",
                                                  description="You can check this through \"/g menu\" ingame",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            veterency = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            veterency = veterency.content

                            '''PAST INFRACTIONS'''
                            embed = discord.Embed(title="Have you had any past infractions on Hypixel?",
                                                  description="Kindly reply with a Yes or No",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            infractions = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            infractions = infractions.content
                            infractions = infractions.capitalize()

                            embed = discord.Embed(title="Kindly make sure that your answers are as detailed as possible."
                                                        "\nGiving short answers will hinder your chances at getting staff.",
                                                  description="When answering, answer in the form of one message. One question, one message!",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            await asyncio.sleep(3)

                            '''------------------------------------------------------Questions------------------------------------------------'''

                            '''WHY STAFF'''
                            embed = discord.Embed(title="Why have you decided to apply for staff?",
                                                  description="Please make sure that you respond in one message",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            whystaff = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            whystaff = whystaff.content

                            '''WHY MISC'''
                            embed = discord.Embed(title="What brought you to Miscellaneous, and what has kept you here?",
                                                  description="Please make sure that you respond in one message",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            whymisc = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            whymisc = whymisc.content

                            '''Suggest'''
                            embed = discord.Embed(title="What is something that you could suggest that could improve the guild?",
                                                  description="Please make sure that you respond in one message",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            suggestion = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            suggestion = suggestion.content

                            '''SCENARIO 1'''
                            embed = discord.Embed(title="You have just started as a trial officer and an officer starts arguing with another member. "
                                                        "This argument starts to get serious quite quickly. What do you do? ",
                                                  description="Make your answer as detailed as possible!",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            scen1 = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            scen1 = scen1.content

                            '''SCENARIO 2'''
                            embed = discord.Embed(title="Suppose it's your first week of being a trial officer and you guild-mute a well-known player. "
                                                        "Your guildmates start spamming you calling you a bad officer and telling you to unmute them. "
                                                        "What would you do?",
                                                  description="Make your answer as detailed as possible!",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            scen2 = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            scen2 = scen2.content

                            '''SCENARIO 3'''
                            embed = discord.Embed(title="Upon joining a game and you discover that a guild member is in your game and is hacking. "
                                                        "What do you do?",
                                                  description="Please make sure that you respond in one message",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            scen3 = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            scen3 = scen3.content

                            '''STAFF'''
                            embed = discord.Embed(title="Have you been staff in any other guild or on any server? "
                                                        "If yes, which one?",
                                                  description="Please make sure that you respond in one message",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            staff = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            staff = staff.content

                            '''TIME'''
                            embed = discord.Embed(title="How much time do you have to contribute to the role? (Per day)",
                                                  description="Please make sure that you respond in one message",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            time_ = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            time_ = time_.content

                            '''GENERAL QUESTION'''
                            embed = discord.Embed(title="Tell us about a time you made a mistake within the last year. "
                                                        "How did you deal with it? What did you learn?",
                                                  escription="Make your answer as detailed as possible!",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            question = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            question = question.content

                            '''ANYTHING ELSE'''
                            embed = discord.Embed(title="Anything else you would like us to know?",
                                                  color=0x4b89e4)
                            await channel.send(embed=embed)
                            random = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            random = random.content

                            await channel.send("Great! You're done with the application!"
                                               "\nI'm working on compiling the application and I'll send it once I'm done compiling!")

                            embed = discord.Embed(title=f"{name}'s Staff Application", color=0x4b89e4)
                            embed.set_thumbnail(url=f'https://visage.surgeplay.com/full/832/{uuid}')
                            embed.add_field(name="1) What is your age?", value=age, inline=False)
                            embed.add_field(name="2) How long have you been in the guild for?", value=veterency, inline=False)
                            embed.add_field(name="3) Have you had any past infractions on Hypixel?", value=infractions, inline=False)
                            embed.add_field(name="4) Why have you decided to apply for staff?", value=whystaff, inline=False)
                            embed.add_field(name="5) What brought you to Miscellaneous, and what has kept you here?", value=whymisc, inline=False)
                            embed.add_field(name="6) What is something you could suggest that would improve the guild?", value=suggestion, inline=False)
                            embed.add_field(name="7) You have just started as a trial officer and an officer starts arguing with another member. This argument starts to get serious quite quickly. What do you do?", value=scen1, inline=False)
                            embed.add_field(name="8) Suppose it's your first week of being a trial officer and you guild-mute a well-known player. Your guildmates start spamming you calling you a bad officer and telling you to unmute them. What would you do?", value=scen2, inline=False)
                            embed.add_field(name="9) Upon joining a game and you discover that a guild member is in your game and is hacking. What do you do?", value=scen3, inline=False)
                            embed.add_field(name="10) Have you been staff in any other guild or on any server? If yes, which one?", value=staff, inline=False)
                            embed.add_field(name="11) How much time do you have to contribute to the role? (Per day)", value=time_, inline=False)
                            embed.add_field(name="12) Tell us about a time you made a mistake within the last year. How did you deal with it? What did you learn?", value=question, inline=False)
                            embed.add_field(name="13) Anything else you would us to know?", value=random, inline=False)
                            await channel.send(embed=embed)
                            await channel.send("If you made any error, make a new ticket, rectify your mistake and copy paste your answer.")
                            break

                        else:
                            await channel.send('What is your minecraft username?')
                            role_reply = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                            name = role_reply.content
                            ign = hypixel.get_dispname(name)
                            if ign is None:
                                await channel.send('Please enter a valid ign!')
                                await channel.send(
                                    "I'll restart the process. "
                                    "If you think I made an error, select 'Other' upon restart")
                            else:
                                guild_name = hypixel.get_guild(name)

                                guest = discord.utils.get(channel.guild.roles, name="Guest")
                                member = discord.utils.get(channel.guild.roles, name="Member")
                                awaiting_app = discord.utils.get(channel.guild.roles, name="Awaiting Approval")

                                await author.edit(nick=ign)
                                if guild_name == "Miscellaneous":
                                    await author.remove_roles(awaiting_app)
                                    await author.remove_roles(guest)
                                    await author.add_roles(member)
                                    embed = discord.Embed(title="Your nick and role was successfully changed!",
                                                          description="Now let's proceed to your application!",
                                                          color=0x8368ff)
                                    await channel.send(embed=embed)

                                else:
                                    await author.remove_roles(member)
                                    await author.add_roles(guest)
                                    embed = discord.Embed(title="Your nick and role was successfully changed!",
                                                          description="Now let's proceed to your application!",
                                                          color=0x8368ff)
                                    await channel.send(embed=embed)

                                async with aiohttp.ClientSession() as session:
                                    async with session.get(f'https://api.mojang.com/users/profiles/minecraft/{name}') as resp:
                                        request = await resp.json()
                                        await session.close()
                                uuid = request['id']

                                await channel.edit(name=f"Staff-Application-{name}", category=discord.utils.get(channel.guild.categories, name="OTHER"))
                                '''AGE'''
                                embed = discord.Embed(title="What is your age?",
                                                      description="Kindly reply with a number",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                age = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                age = age.content

                                '''VETERENCY'''
                                embed = discord.Embed(title="For how long have you been in Miscellaneous?",
                                                      description="You can check this through \"/g menu\" ingame",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                veterency = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                veterency = veterency.content

                                '''PAST INFRACTIONS'''
                                embed = discord.Embed(title="Have you had any past infractions on Hypixel?",
                                                      description="Kindly reply with a Yes or No",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                infractions = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                infractions = infractions.content
                                infractions = infractions.capitalize()

                                embed = discord.Embed(title="Kindly make sure that your answers are as detailed as possible."
                                                            "\nGiving short answers will hinder your chances at getting staff.",
                                                      description="When answering, answer in the form of one message. "
                                                                  "One question, one message!",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                await asyncio.sleep(3)
    #------------------------------------------------------Questions------------------------------------------------

                                #WHY STAFF
                                embed = discord.Embed(title="Why have you decided to apply for staff?",
                                                      description="Please make sure that you respond in one message",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                whystaff = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                whystaff = whystaff.content


                                #WHY MISC
                                embed = discord.Embed(title="What brought you to Miscellaneous, "
                                                            "and what has kept you here?",
                                                      description="Please make sure that you respond in one message",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                whymisc = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                whymisc = whymisc.content


                                #Suggest
                                embed = discord.Embed(title="What is something that you could suggest that could improve the guild?",
                                                      description="Please make sure that you respond in one message",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                suggestion = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                suggestion = suggestion.content


                                #SCENARIO 1
                                embed = discord.Embed(title="You have just started as a trial officer and an officer starts arguing with another member."
                                                            " This argument starts to get serious quite quickly. What do you do? ",
                                                      description="Make your answer as detailed as possible!",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                scen1 = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                scen1 = scen1.content


                                #SCENARIO 2
                                embed = discord.Embed(title="Suppose it's your first week of being a trial officer and you guild-mute a well-known player."
                                                            " Your guildmates start spamming you calling you a bad officer and telling you to unmute them."
                                                            " What would you do?",
                                                      description="Make your answer as detailed as possible!",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                scen2 = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                scen2 = scen2.content


                                #SCENARIO 3
                                embed = discord.Embed(title="Upon joining a game and you discover that a guild member is in your game and is hacking."
                                                            " What do you do?",
                                                      description="Please make sure that you respond in one message",
                                                      color=0x4b89e4)
                                await channel.send(embed=embed)
                                scen3 = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                scen3 = scen3.content


                                #STAFF
                                embed = discord.Embed(title="Have you been staff in any other guild or on any server? If yes, which one?", description="Please make sure that you respond in one message", color=0x4b89e4)
                                await channel.send(embed=embed)
                                staff = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                staff = staff.content


                                #TIME
                                embed = discord.Embed(title="How much time do you have to contribute to the role? (Per day)", description="Please make sure that you respond in one message", color=0x4b89e4)
                                await channel.send(embed=embed)
                                time_ = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                time_ = time_.content


                                #GENERAL QUESTION
                                embed = discord.Embed(title="Tell us about a time you made a mistake within the last year. How did you deal with it? What did you learn?", description="Make your answer as detailed as possible!", color=0x4b89e4)
                                await channel.send(embed=embed)
                                question = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                question = question.content

                                #ANYTHING ELSE
                                embed = discord.Embed(title="Anything else you would like us to know?", color=0x4b89e4)
                                await channel.send(embed=embed)
                                random = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                                random = random.content


                                msg = await channel.send("Great! You're done with the application!\n I'm working on compiling the application and I'll send it once I'm done compiling!")
                                try:
                                    embed = discord.Embed(title=f"{name}'s Staff Application", color=0x4b89e4)
                                    embed.set_thumbnail(url=f'https://visage.surgeplay.com/full/832/{uuid}')
                                    embed.add_field(name="1) What is your age?", value=age, inline=False)
                                    embed.add_field(name="2) How long have you been in the guild for?", value=veterency, inline=False)
                                    embed.add_field(name="3) Have you had any past infractions on Hypixel?", value=infractions, inline=False)
                                    embed.add_field(name="4) Why have you decided to apply for staff?", value=whystaff, inline=False)
                                    embed.add_field(name="5) What brought you to Miscellaneous, and what has kept you here?", value=whymisc, inline=False)
                                    embed.add_field(name="6) What is something you could suggest that would improve the guild?", value=suggestion, inline=False)
                                    embed.add_field(name="7) You have just started as a trial officer and an officer starts arguing with another member. This argument starts to get serious quite quickly. What do you do?", value=scen1, inline=False)
                                    embed.add_field(name="8) Suppose it's your first week of being a trial officer and you guild-mute a well-known player. Your guildmates start spamming you calling you a bad officer and telling you to unmute them. What would you do?", value=scen2, inline=False)
                                    embed.add_field(name="9) Upon joining a game and you discover that a guild member is in your game and is hacking. What do you do?", value=scen3, inline=False)
                                    embed.add_field(name="10) Have you been staff in any other guild or on any server? If yes, which one?", value=staff, inline=False)
                                    embed.add_field(name="11) How much time do you have to contribute to the role? (Per day)", value=time_, inline=False)
                                    embed.add_field(name="12) Tell us about a time you made a mistake within the last year. How did you deal with it? What did you learn?", value=question, inline=False)
                                    embed.add_field(name="13) Anything else you would us to know?", value=random, inline=False)
                                    await channel.send(embed=embed)
                                    await channel.send("If you made any error, make a new ticket, rectify your mistake and copy paste your answer.")
                                except Exception as e:
                                    if e == "400 Bad Request (error code: 50035): Invalid Form Body\nIn embed.fields.9.value: Must be 1024 or fewer in length.":
                                        await msg.edit(content='Failed to compile the data since your message is too long!\n No worries though, the staff team will still go through your application!')


                                break

                    else:
                        await channel.send("Since you don't meet the requirements, there's no point proceeding with the application. Kindly reapply once you meet all the requirements.")
                        break
                elif reply == "Gvg":
                    await channel.edit(name=f"GvG-Application-{name}", category=discord.utils.get(channel.guild.categories, name="OTHER"))
                    embed = discord.Embed(title="To be eligible to apply for the GvG Team, you must meet any one of the following game-specific requirements.", color=0x00FFFF)
                    embed.add_field(name="Bedwars", value="500 Wins\n1.6 Final Kill-Death Ratio", inline=False)
                    embed.add_field(name="Skywars", value="1000 Wins\n1.2 Kill-Death Ratio", inline=False)
                    embed.add_field(name="Duels", value="2000 Wins\n1.5 Kill-Death Ratio", inline=False)
                    embed.add_field(name="Polyvalent (All gamemodes)", value="Must fulfill all requirements", inline=False)
                    await channel.send(embed=embed)

                    req = hypixel.get_data(name)
                    if req["player"] is None:
                        embed = discord.Embed(title='Unknown IGN', description='Kindly create a new ticket to sync your name and then create another ticket for the GvG Application!', color=0xff0000)
                        await channel.send(embed=embed)
                    else:
                        req = hypixel.get_data(name)
                        uuid = req['player']['uuid']

                        x=0
                        y=0
                        z=0

                        #Bedwars
                        bw_wins = int(req['player']['stats']['Bedwars']['wins_bedwars'])
                        bw_final_kills = int(req['player']['stats']['Bedwars']['final_kills_bedwars'])
                        bw_final_deaths = int(req['player']['stats']['Bedwars']['final_deaths_bedwars'])
                        bw_fkdr = bw_final_kills/bw_final_deaths
                        bw_fkdr = round(bw_fkdr, 2)

                        if bw_wins > 500:
                            x = x + 1
                        if bw_fkdr > 1.6:
                            x = x + 1



                        #Skywars
                        sw_wins_overall = int(req['player']['stats']['SkyWars']['wins'])
                        sw_wins_solo = int(req['player']['stats']['SkyWars']['wins_solo'])
                        sw_wins_doubles = int(req['player']['stats']['SkyWars']['wins_team'])
                        sw_kills = int(req['player']['stats']['SkyWars']['kills'])
                        sw_deaths = int(req['player']['stats']['SkyWars']['deaths'])
                        sw_kdr = sw_kills/sw_deaths
                        sw_kdr = round(sw_kdr, 2)
                        if sw_wins_overall > 1000:
                            y = y + 1
                        if sw_kdr > 1.2:
                            y = y + 1



                        #Duel
                        duels_wins = int(req['player']['stats']['Duels']['wins'])
                        duels_losses = int(req['player']['stats']['Duels']['losses'])
                        duels_kills = int(req['player']['stats']['Duels']['kills'])
                        duels_wlr = duels_wins/duels_losses
                        duels_wlr = round(duels_wlr, 2)

                        if duels_wins > 2000:
                            z = z + 1
                        if duels_wlr > 1.5:
                            z = z + 1


                        if x >= 2 and y >= 2 and z >= 2:
                            embed1 = discord.Embed(title="You're eligible for the Polyvalent GvG Team!", description="Kindly await staff assistance for further information!", color=0xff00f6)
                            embed1.add_field(name="Bedwars Wins", value=f'`{bw_wins}`')
                            embed1.add_field(name="Bedwars FKDR", value=f'`{bw_fkdr}`')
                            embed1.add_field(name="Skywars Wins (Overall)", value=f'`{sw_wins_overall}`')
                            embed1.add_field(name="Skywars Wins (Solo)", value=f'`{sw_wins_solo}`')
                            embed1.add_field(name="Skywars Wins (doubles)", value=f'`{sw_wins_doubles}`')
                            embed1.add_field(name="Skywars KDR", value=f'`{sw_kdr}`')
                            embed1.add_field(name="Duels Wins", value=f'`{duels_wins}`')
                            embed1.add_field(name="Duels WLR", value=f'`{duels_wlr}`')
                            await channel.send(embed=embed1)
                            break

                        elif x == 1 and y == 1 and z == 1:
                            embed1 = discord.Embed(title="You're eligible for any two of the teams!\n You will be assigned to any two teams on the basis of your stats!",
                                                   description="Kindly await staff assistance for further information!",
                                                   color=0xff00f6)
                            embed1.add_field(name="Bedwars Wins", value=f'`{bw_wins}`')
                            embed1.add_field(name="Bedwars FKDR", value=f'`{bw_fkdr}`')
                            embed1.add_field(name="Skywars Wins (Overall)", value=f'`{sw_wins_overall}`')
                            embed1.add_field(name="Skywars Wins (Solo)", value=f'`{sw_wins_solo}`')
                            embed1.add_field(name="Skywars Wins (doubles)", value=f'`{sw_wins_doubles}`')
                            embed1.add_field(name="Skywars KDR", value=f'`{sw_kdr}`')
                            embed1.add_field(name="Duels Wins", value=f'`{duels_wins}`')
                            embed1.add_field(name="Duels WLR", value=f'`{duels_wlr}`')
                            await channel.send(embed=embed1)
                            break

                        elif x >= 1 and y >= 1:
                            embed1 = discord.Embed(title="You're eligible for the Bedwars and Skywars GvG Teams!", description="Kindly await staff assistance for further information!", color=0xff00f6)
                            embed1.add_field(name="Bedwars Wins", value=f'`{bw_wins}`')
                            embed1.add_field(name="Bedwars FKDR", value=f'`{bw_fkdr}`')
                            embed1.add_field(name="Skywars Wins (Overall)", value=f'`{sw_wins_overall}`')
                            embed1.add_field(name="Skywars Wins (Solo)", value=f'`{sw_wins_solo}`')
                            embed1.add_field(name="Skywars Wins (doubles)", value=f'`{sw_wins_doubles}`')
                            embed1.add_field(name="Skywars KDR", value=f'`{sw_kdr}`')
                            embed1.set_footer(text=f"Duels wins - {duels_wins}\nDuels WLR - {duels_wlr}")
                            await channel.send(embed=embed1)
                            break
                                
                        elif x >= 1 and z >= 1:
                            embed1 = discord.Embed(title="You're eligible for the Bedwars and Duels GvG Teams!", description="Kindly await staff assistance for further information!", color=0xff00f6)
                            embed1.add_field(name="Bedwars Wins", value=f'`{bw_wins}`')
                            embed1.add_field(name="Bedwars FKDR", value=f'`{bw_fkdr}`')
                            embed1.add_field(name="Duels Wins", value=f'`{duels_wins}`')
                            embed1.add_field(name="Duels WLR;", value=f'`{duels_wlr}`')
                            embed1.set_footer(text=f"Skywars Wins (Overall) - {sw_wins_overall}\nSkywars Wins (Solo) - {sw_wins_solo}\nSkywars Wins (Doubles) - {sw_wins_doubles}\nSkywars KDR - {sw_kdr}")
                            await channel.send(embed=embed1)
                            break

                        elif y >= 1 and z >= 1:
                            embed1 = discord.Embed(title="You're eligible for the Skywars and Duels GvG Teams!", description="Kindly await staff assistance for further information!", color=0xff00f6)
                            embed1.add_field(name="Skywars Wins (Overall)", value=f'`{sw_wins_overall}`')
                            embed1.add_field(name="Skywars Wins (Solo)", value=f'`{sw_wins_solo}`')
                            embed1.add_field(name="Skywars Wins (doubles)", value=f'`{sw_wins_doubles}`')
                            embed1.add_field(name="Skywars KDR", value=f'`{sw_kdr}`')
                            embed1.add_field(name="Duels Wins", value=f'`{duels_wins}`')
                            embed1.add_field(name="Duels WLR", value=f'`{duels_wlr}`')
                            embed1.set_footer(text=f"Bedwars Wins - {bw_wins}\nBedwars FKDR - {bw_fkdr}")
                            await channel.send(embed=embed1)
                            break
                        elif x >= 1:
                            embed1 = discord.Embed(title="You're eligible for the Bedwars GvG Team!", description="Kindly await staff assistance for further information!", color=0xff00f6)
                            embed1.add_field(name="Bedwars Wins", value=f'`{bw_wins}`')
                            embed1.add_field(name="Bedwars FKDR", value=f'`{bw_fkdr}`')
                            embed1.set_footer(text=f"Skywars Wins (Overall) - {sw_wins_overall}\nSkywars Wins (Solo) - {sw_wins_solo}\nSkywars Wins (Doubles) - {sw_wins_doubles}\nSkywars KDR - {sw_kdr}\nDuels wins - {duels_wins}\nDuels Kills - {duels_kills}\nDuels WLR - {duels_wlr}")
                            await channel.send(embed=embed1)
                            break
                        elif y >= 1:
                            embed1 = discord.Embed(title="You're eligible for the Skywars GvG Team!", description="Kindly await staff assistance for further information!", color=0xff00f6)
                            embed1.add_field(name="Skywars Wins (Overall)", value=f'`{sw_wins_overall}`')
                            embed1.add_field(name="Skywars Wins (Solo)", value=f'`{sw_wins_solo}`')
                            embed1.add_field(name="Skywars Wins (doubles)", value=f'`{sw_wins_doubles}`')
                            embed1.add_field(name="Skywars KDR", value=f'`{sw_kdr}`')
                            embed1.set_footer(text=f"Bedwars Wins - {bw_wins}\nBedwars FKDR - {bw_fkdr}\nDuels wins - {duels_wins}\nDuels WLR - {duels_wlr}")
                            await channel.send(embed=embed1)
                            break
                        elif z >= 1:
                            embed1 = discord.Embed(title="You're eligible for the Duels GvG Team!", description="Kindly await staff assistance for further information!", color=0xff00f6)
                            embed1.add_field(name="Duels Wins", value=f'`{duels_wins}`')
                            embed1.add_field(name="Duels WLR", value=f'`{duels_wlr}`')
                            embed1.set_footer(text=f"Bedwars Wins - {bw_wins}\nBedwars FKDR - {bw_fkdr}\nSkywars Wins (Overall) - {sw_wins_overall}\nSkywars Wins (Solo) - {sw_wins_solo}\nSkywars Wins (Doubles) - {sw_wins_doubles}\nSkywars KDR - {sw_kdr}")
                            await channel.send(embed=embed1)
                            break
                        else:
                            embed1 = discord.Embed(title="You're ineligible to apply GvG Team because you don't meet the requirements!", description="Kindly await staff assistance for further information!", color=0xcd5c5c)
                            embed1.set_footer(text=f"Bedwars Wins - {bw_wins}\nBedwars FKDR - {bw_fkdr}\nSkywars Wins (Overall) - {sw_wins_overall}\nSkywars Wins (Solo) - {sw_wins_solo}\nSkywars Wins (Doubles) - {sw_wins_doubles}\nSkywars KDR - {sw_kdr}\nDuels wins - {duels_wins}\nDuels WLR - {duels_wlr}")
                            await channel.send(embed=embed1)
                            break

                elif reply == "Demotion":

                    admin = discord.utils.get(channel.guild.roles, name="Admin")
                    if admin in author.roles:
                        await channel.purge(limit=10)
                        embed = discord.Embed(title="Who would you like to demote?", description="Kindly mention them", color=0x00FFFF)
                        await channel.send(embed=embed)
                        user = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                        user = user.mentions[0]

                        username = user.nick
                        if username is None:
                            username = user.name

                        await channel.edit(name=f"Demotion-{username}")

                        embed = discord.Embed(title=f"What's the reason behind {username}'s demotion?", color=0x00FFFF)
                        await channel.send(embed=embed)
                        reason = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                        reason = reason.content

                        await channel.set_permissions(user, send_messages=True, read_messages=True,
                                                      add_reactions=True, embed_links=True,
                                                      attach_files=True, read_message_history=True,
                                                      external_emojis=True)
                        await channel.purge(limit=10)
                        embed = discord.Embed(title=f"{username} you are being demoted from the Miscellaneous staff team!", description=f"This is due to {reason}", color=0x8368ff)
                        await channel.send(embed=embed)
                        await channel.send(user.mention)
                        break
                    else:
                        embed = discord.Embed(title="My massive computer brain thinks you made a mistake.", color=0xff0000)
                        embed.add_field(name="If this is true", value="Type `Yes`", inline=False)
                        embed.add_field(name="If this is false", value="Type `No`", inline=False)
                        await channel.send(embed=embed)
                        mistake = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                        mistake = mistake.content
                        mistake = mistake.capitalize()
                        if mistake == "Yes":
                            await channel.send("Great! Let's start over!")
                        else:
                            await channel.send(
                                "Hmm, seems like I'm dumb.\nKindly specify your reason behind creating this ticket and await staff assistance!")
                            break

                elif reply == "Event":
                    await channel.edit(name=f"Event-{name}", category=discord.utils.get(channel.guild.categories, name="EVENT"))
                    await channel.send("Alright, kindly enter the requested details for registering!")

                    name_embed = discord.Embed(title="What is your Minecraft Username?",color=0x4b89e4)
                    await channel.send(embed=name_embed)
                    name = await client.wait_for('message',
                                                       check=lambda x: x.channel == channel and x.author == author)
                    name = name.content
                    ign = hypixel.get_dispname(name)
                    if ign is None:
                        await channel.send('Please enter a valid ign!')
                        await channel.send(
                            "I'll restart the process. "
                            "If you think I made an error, select 'Other' upon restart")

                    else:
                        await author.edit(nick=ign)
                        div_embed = discord.Embed(title="Which division would you like to partcipaticate in? Division 1 or Division 2?",
                                                  description="Please reply with the following:\n"
                                                              "`Division 1: 3rd July, 8:00 pm UTC/GMT`\n"
                                                              "`Division 2: 4th July, 7:00 am UTC/GMT`",
                                                  color=0x4b89e4)
                        div_embed.set_footer(text="If you have any difficulty interpreting the time, make another ticket and await staff assistance!\n"
                                              "Reply with 1 for division 1"
                                              "\nReply with 2 for division 2")
                        await channel.send(embed=div_embed)
                        division = await client.wait_for('message',
                                                     check=lambda x: x.channel == channel and x.author == author)
                        division = division.content
                        division = division.capitalize()
                        if str(division) in ("1", "One", 'Div1', 'Division 1', 'Division1', 'Div 1', 'Division 1: 3rd July, 8:00 pm UTC/GMT'):
                            division = 1
                        elif str(division) in ("2", "Two", 'Div2', 'Division 2', 'Division2', 'Div 2', 'Division 2: 4th July, 7:00 am UTC/GMT'):
                            division = 2



                        rules_embed = discord.Embed(
                            title="Rules",
                            description="• The screenshots MUST NOT be cropped. We will only accept screenshots of your entire screen.\n"
                                        "• Cross-teaming/boosting is disallowed.\n"
                                        "• Cheating, use of blacklisted modifications is disallowed.\n"
                                        "• Forging of screenshots is disallowed.\n",
                            color=0x4b89e4)
                        rules_embed.set_footer(text="Violation of any of these rules (except the first will result) in immediate disqualification along with a temporary/permanent blacklist.")
                        await channel.send(embed=rules_embed)
                        await channel.send("**Do you agree to abide by these rules and face the consequences if any of the rules are broken?**\n(Yes/No)")
                        rules = await client.wait_for('message',
                                                     check=lambda x: x.channel == channel and x.author == author)
                        rules = (rules.content).capitalize()

                        if rules in ('Yes', 'Y', 'Yeah', 'Yup', 'Ya', 'Yea', 'Ye'):
                            with open('eventparticipants.json','r') as event_participants:
                                eventparticipants = json.load(event_participants)
                                if division == 1:
                                    await channel.edit(category=discord.utils.get(channel.guild.categories, name="Event-Div-1"))
                                    participants_list = eventparticipants.get("div1")
                                    participants_list.append(ign)
                                    eventparticipants["div1"] = participants_list
                                elif division == 2:
                                    await channel.edit(category=discord.utils.get(channel.guild.categories, name="Event-Div-2"))
                                    participants_list = eventparticipants.get("div2")
                                    participants_list.append(ign)
                                    eventparticipants["div2"] = participants_list
                            with open('eventparticipants.json','w') as event_participants:
                                json.dump(eventparticipants, event_participants)
                            await channel.send(f"**You've been added to the list of participants!**\nIn division {division}, you are participant number: {len(participants_list)}")

                        else:
                            await channel.send("**In order to participate in the event, you must agree to abide by all the rules."
                                               "\nIf you have any queries regarding the rules, create a new ticket and select the category as 'other'**"
                                               "\n*This ticket will be deleted in 1 minute*")
                            await asyncio.sleep(60)
                            await discord.TextChannel.delete(channel)
                    break

                elif reply == "Other":
                        await channel.edit(name=f"Unknown-{name}", category=discord.utils.get(channel.guild.categories, name="OTHER"))
                        await channel.send(
                            "Okay. Kindly specify your reason behind creating this ticket and wait for staff to help you!")
                        break
                else:
                    embed = discord.Embed(title="My massive computer brain thinks you made a mistake.", color=0xff0000)
                    embed.add_field(name="If this is true", value="Type `Yes`", inline=False)
                    embed.add_field(name="If this is false", value="Type `No`", inline=False)
                    await channel.send(embed=embed)
                    mistake = await client.wait_for('message', check=lambda x: x.channel == channel and x.author == author)
                    mistake = mistake.content
                    mistake = mistake.capitalize()
                    if mistake == "Yes":
                        embed = discord.Embed(title="Great! Let's start over!",
                                              color=0x8368ff)
                        await channel.send(embed=embed)
                    else:
                        await channel.send(
                            "Hmm, seems like I'm dumb.\nKindly specify your reason behind creating this ticket and await staff assistance!")
                        break
                
    except Exception as e:
        if str(e) == "Expecting value: line 1 column 1 (char 0)":
            embed = discord.Embed(title="The Hypixel API is down!", description="You may proceed by elaborating on why you created this ticket so that the staff team can help you!",
                                  color=0xff0000)
            await channel.send(embed=embed)
            print(e)
        else:
            print(e)
            await client.error_channel.send(f"Error in {channel}\n{e}\n<@!326399363943497728>")

@tasks.loop()
async def get_error_channel():
    await client.wait_until_ready()
    client.error_channel = client.get_channel(523743721443950612)

get_error_channel.start()
client.run(client.token)
