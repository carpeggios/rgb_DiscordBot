# bot.py
from asyncio.windows_events import NULL
import os
import discord
import aiosqlite, asyncio
import sqlite3
import numpy as np
import pandas as pd
from sqlite3 import Error
from discord import Option
from discord.ext import commands
from discord_components import DiscordComponents, ComponentsBot, Button
from datetime import *
from threading import Timer
from dotenv import load_dotenv


load_dotenv()

#init env vars from .env file.
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
DB_PATH = os.path.join(os.getenv('ROOT_DIR'), 'member_data.db')

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents) #Server Members Intent, allows bot to see all members.
DiscordComponents(bot)

#Global Vars
global timers
timers = []

#QUERIES

#Insert a new member into 'perUser' db. Default value initialized. 
#Inserts if not existing, avoid duplciates and updates db to current member list. 
#Useful for when Bot has downtime, and members have joined.
def insert_newmember(id, name): #default table value.

    strID = str(id)
    strName = str(name)

    #https://stackoverflow.com/questions/5243596/python-sql-query-string-formatting
    fstringsql = (
        f'BEGIN '
        f'    IF NOT EXISTS(SELECT FROM perUser WHERE User_ID = {strID}) '
        f'    BEGIN '
        f'        INSERT INTO perUser VALUES ({strID},{strName}, 0, "0", 0, 0, 0) '
        f'    END '
        f'END;'
    )

    return fstringsql

#Inserts a nickname for a newmember or for nickname change on 'privData' db.
#Initializes nickname to be username in case user never customizes a nickname.
#Useful for nickname changes to include stats in nickname, so user can turn off nickname stats...
#and get back to their original nickname.
def insert_nick(id, nick): #default table value.

    strID = str(id)
    strNick = str(nick)
    #https://stackoverflow.com/questions/5243596/python-sql-query-string-formatting
    fstringsql = (
        f'BEGIN '
        f'    IF NOT EXISTS(SELECT FROM privData WHERE User_ID = {strID}) '
        f'    BEGIN '
        f'        INSERT INTO privData VALUES ({strID},{strNick}) '
        f'    END '
        f'END;'
    )

    return fstringsql

#Updates nickname for when user actually customizes nickname.
def update_nick(id, nick):
    query = 'UPDATE teamData SET User_Nick_Default = ' + str(nick) + ' WHERE User_ID = ' + str(id) + ';'
    return query

#On event (member_leave), to delete member's entries on perUser and privData db's.
def delete_member(id):
    query = 'DELETE FROM perUser(User_ID) VALUE(' + id + ');'
    return query

#On command (add, a, subtract), add's qty to db.
def add_gob(id, num):
    query = 'UPDATE perUser SET Gob_Qty = Gob_Qty + ' + str(num) + ' WHERE User_ID = ' + str(id) + ';'
    return query

#On command (member_join), adds member to privData db.
def insert_mempriv(id, name):
    query = 'INSERT INTO privData VALUES ("' + str(id) + '","' + str(name) + '");'
    return query

#On event (member_leave), removes member from privData db.
def delete_mempriv(id):
    query = 'DELETE FROM privData(User_ID) VALUE(' + id + ');'
    return query

#On command (a), adds gob to specific team on 'teamData' db.
def add_gobTeam(name):
    query = 'UPDATE teamData SET Gob_Qty = Gob_Qty + 1 WHERE Team_Name = "' + str(name) + '";'
    return query

#Initializes team list, will help expand team list later.
def add_team(team):
    query = 'INSERT INTO teamData VALUES ("'+str(team)+'", 0, 0, "0", 0);'
    return query

#Toggle db value for a user to keep track of user's stat-toggle state.
#1 = user wants stats on, update nickname to include stat. 
#0 = user wants stats off, update nickname to go back to previous nickname or default nickname 
def toggle_stats(id):
    temp_query = 'SELECT FROM Toggle_Stats FROM perUser WHERE User_ID = ' + str(id) + ';'
    if temp_query == 0:
        #OFF
        query = 'UPDATE perUser SET Toggle_Stats = 0 WHERE User_ID = ' + str(id) + ';'
    else:
        #ON
        query = 'UPDATE perUser SET Toggle_Stats = 1 WHERE User_ID = ' + str(id) + ';'
    return query

#get gob value for user id.
def get_gobs(id):
    query = 'SELECT Gob_Qty FROM perUser WHERE User_ID = ' + str(id) + ';'
    return query

#get timer value for current user's timer. 
def get_time(id):
    query = 'SELECT Time_Accrued FROM perUser WHERE User_ID = ' + str(id) + ';'
    return query

#get wings state.
def get_wings(id):
    query = 'SELECT Wings_Obtained FROM perUser WHERE User_ID = ' + str(id) + ';'
    return query

#get hunts qty.
def get_hunts(id):
    query = 'SELECT Hunts FROM perUser WHERE User_ID = ' + str(id) + ';'
    return query

#get team ID so bot can use the ID to do channel/team mentions channel.send('<@{teamID}>')
def get_teamID(team):
    query = 'SELECT Channel_ID FROM teamData WHERE Team_Name = "' + str(team) + '";'
    return query

'''
#start timer thread for the user.
def timer_thread(userID, teamID, close):

    if close==0:
        timer = time.Time()
        fut = asyncio.run_coroutine_threadsafe(timer, asyncio.get_event_loop())
        asyncio.Task.current_task().name = userID
        asyncio.Task.current_task().team = teamID
        timers.append(fut)
        fut.result()  # wait for the result
    else: 
        return timer
'''


@bot.command(
    help="says hello!",
    brief="says hello back to user."
)
@commands.is_owner()
async def hello(ctx) :
    await ctx.channel.send("hello " + str(ctx.author.nick))

@bot.command(
    help="Add X amount to your tracked goblin qty.",
    brief="Add X amount to your tracked goblin qty."
)
@commands.is_owner()
#allows user to add X amt of gobs to their qty. Useful for initial setup.
#broadcasts user's addition to channel.
async def add(ctx, arg) :
    gobimg = await ctx.guild.fetch_emoji(995038023282597958)
    cnn = sqlite3.connect(DB_PATH)
    cs = cnn.cursor()
    cs.execute('Select Username From perUser;')
    cs.execute(add_gob(str(ctx.author.id), arg))
    gobs = str(cs.execute(get_gobs(str(ctx.author.id))).fetchone()[0])
    await ctx.channel.send("added " + str(arg) + f"{gobimg} (Total: " + gobs + ")")
    cnn.commit()
    cnn.close()

@bot.command(
    help="Add 1 to Gob Count!",
    brief="Just found one!"
)
@commands.is_owner()
#meant to be the main command to +1. 
#broadcasts user's addition to channel(s), to also include team and current total data.
# "User(36) in team Eld(90) found a gob!"
async def a(ctx) :
    gobimg = await ctx.guild.fetch_emoji(995038023282597958)
    teamID = ctx.author.top_role.id
    nameID = ctx.author.id
    cnn = sqlite3.connect(DB_PATH)
    cs = cnn.cursor()
    cs.execute('Select Username From perUser;')
    cs.execute(add_gob(str(ctx.author.id), 1))
    cs.execute('Select * From teamData;')
    cs.execute(add_gobTeam((str(ctx.author.top_role)).strip()))
    channelID = str(cs.execute(get_teamID(str(ctx.author.top_role).strip())).fetchone()[0])

    await ctx.channel.send("<@" + str(nameID) + "> in team <#" + str(channelID) + f"> found a {gobimg}!")
    cnn.commit()
    cnn.close()

@bot.command(
    help="Subtract X amount to your tracked goblin qty.",
    brief="Subtract X amount to your tracked goblin qty."
)
@commands.is_owner()
#allows user to add -X amt of gobs to their qty. Useful for initial setup.
async def subtract(ctx, arg) :
    gobimg = await ctx.guild.fetch_emoji(995038023282597958)
    cnn = sqlite3.connect(DB_PATH)
    cs = cnn.cursor()
    cs.execute('Select Username From perUser;')
    cs.execute(add_gob(str(ctx.author.id), -(int(arg))))
    gobs = str(cs.execute(get_gobs(str(ctx.author.id))).fetchone()[0])
    await ctx.channel.send("subtracted "  + str(arg) + f"{gobimg} (Total: " + gobs + ")")
    cnn.commit()
    cnn.close()

@bot.command(
    help="Start timer to track hunt time. (Accumulative.)",
    brief="Start timer to track hunt time. (Accumulative.)"
)
@commands.is_owner()
#starts a timer for the user. threaded so each timer is unique to user.
#timer should count towards user's total time, as well as contribute to team's time.
#but only on 'end hunt'.
async def starthunt(ctx) :
    await ctx.channel.send("starting timer...")
    #await timer_thread(ctx.author.id, 0)


@bot.command(
    help="End timer hunt time.",
    brief="End timer hunt time."
)
@commands.is_owner()
#stops timer. increments hunt qty +1. Add elapsed time to user's and team's total times.
async def endhunt(ctx) :
    #time = await timer_thread(ctx.author.id, 1)
    await ctx.channel.send("ending timer.")
    

@bot.command(
    help="Use command if you find wings!",
    brief="Use command if you find wings!"
)
@commands.is_owner()
#user to report to bot they have found wings.
#report find and stats to entire channel (with prio?)
#change nickname stats to show wings, and send msg to them...
#send proof of wings to admin, for role change to wings role.
async def cosmic(ctx) :
    wings = await ctx.guild.fetch_emoji(995000357413474407)
    cnn = sqlite3.connect(DB_PATH)
    cs = cnn.cursor()
    cs.execute('Select Username From perUser;')
    gobs = str(cs.execute(get_gobs(str(ctx.author.id))).fetchone()[0])
    time = str(cs.execute(get_time(str(ctx.author.id))).fetchone()[0])
    cnn.commit()
    cnn.close()
    await ctx.channel.send(f"gratz! {wings}")
    await ctx.channel.send("@" + str(ctx.author.name) + " in team " + str(ctx.author.top_role) + f" found the {wings}! They achieved this after " + gobs + " gobs and " + time + " time hunted!")

@bot.command(
    help="Prints stats for yourself.",
    brief="Prints stats for yourself."
)
@commands.is_owner()
#print out stats for self.
async def statself(ctx) :
    cnn = sqlite3.connect(DB_PATH)
    cs = cnn.cursor()
    cs.execute('Select Username From perUser;')
    gobs = str(cs.execute(get_gobs(str(ctx.author.id))).fetchone()[0])
    time = str(cs.execute(get_time(str(ctx.author.id))).fetchone()[0])
    wings = str(cs.execute(get_wings(str(ctx.author.id))).fetchone()[0])
    if wings == 1:
        wingsBool = "Found!"
    else:
        wingsBool = "Not Found."
    hunts = str(cs.execute(get_hunts(str(ctx.author.id))).fetchone()[0])
    await ctx.channel.send("@" + str(ctx.author.name) + " in team " + str(ctx.author.top_role) + f"-Gobs(" + gobs + ")-Time(" + time + ")-Hunts(" + hunts + ")-Wings(" + wingsBool + ")")
    cnn.commit()
    cnn.close()

@bot.command(
    help="Toggle Nickname Stats.",
    brief="Toggle Nickname Stats."
)
@commands.is_owner()
#turn on/off stats in nickname.
#will display basic gob qty in nickname. [OFF] username -> [ON] username(36)
async def togglestat(ctx) :
    cnn = sqlite3.connect(DB_PATH)
    cs = cnn.cursor()
    cs.execute('Select Toggle_Stats From perUser;')
    cs.execute(toggle_stats(str(ctx.author.id)))
    temp_query = 'SELECT Toggle_Stats FROM perUser WHERE User_ID = ' + str(id) + ';'
    prev_name = 'SELECT User_Nick_Default FROM privData WHERE User_ID = ' + str(id) + ';'
    gobs = str(cs.execute(get_gobs(str(ctx.author.id))).fetchone()[0])
    time = str(cs.execute(get_time(str(ctx.author.id))).fetchone()[0])
    #ON->OFF
    if temp_query == 0:
        await ctx.member.edit(nick = str(prev_name))
        await ctx.channel.send('Set to OFF.')
    #OFF->ON
    else:
        await ctx.author.edit(nick = str(ctx.author.nick) + "#" + str(ctx.author.top_role) + "(" + str(time) + ")" + "(" + str(gobs) + ")")
        await ctx.channel.send('Set to ON.')

    cnn.commit()
    cnn.close()

@bot.command(
    help="Post an interface.",
    brief="Post an interface."
)
@commands.is_owner()
#admin command to post a message that includes buttons/interface for team usage.
#commandless way to control bot to track stats.
#button1 = !a command. (!a command for each user in channel.)
#button2 = !starthunt command. (start timer for each user in channel.)
#button3 = !endhunt command. (end timer for each user in channel, and tally time elapsed.)
async def menu(ctx) :
    gobimg = await ctx.guild.fetch_emoji(995038023282597958)
    channelID = ctx.message.channel.id
    await ctx.send("<#" + str(channelID) + "> Hunting Menu", components = [Button(label = f'+1', emoji=gobimg), Button(label='Start Hunt!', style=2), Button(label='End Hunt.', style=4)],)


    #gob_interact = await bot.wait_for()

'''
@bot.command(
    help="Print out stats for your team.",
    brief="Print out stats for your team."
)
@commands.is_owner()
#print out stats for team.
async def statteam(ctx, arg) :
    cnn = sqlite3.connect(DB_PATH)
    cs = cnn.cursor()
    cs.execute('Select Username From perUser;')
    gobs = str(cs.execute(get_gobs(str(ctx.author.id))).fetchone()[0])
    time = str(cs.execute(get_time(str(ctx.author.id))).fetchone()[0])
    hunts = str(cs.execute(get_hunts(str(ctx.author.id))).fetchone()[0])
    await ctx.channel.send("Team " + ctx.member.top_role + f"-Gobs(" + gobs + ")-Time(" + time + ")-Hunts(" + hunts + ")")
    cnn.commit()
    cnn.close()

@bot.command(
    help="Print out stats for the server.",
    brief="Print out stats for the server."
)
#print out top 30 stats for server.
async def stat30(ctx, arg) :
    cnn = sqlite3.connect(DB_PATH)
    cs = cnn.cursor()
    cs.execute('Select Username From perUser;')
    gobs = str(cs.execute(get_gobs(str(ctx.author.id))).fetchone()[0])
    time = str(cs.execute(get_time(str(ctx.author.id))).fetchone()[0])
    hunts = str(cs.execute(get_hunts(str(ctx.author.id))).fetchone()[0])
    await ctx.channel.send("Team " + ctx.member.top_role + f"-Gobs(" + gobs + ")-Time(" + time + ")-Hunts(" + hunts + ")")
    cnn.commit()
    cnn.close()
'''

''' #Bot Listener Template
@bot.event
async def on_message(message):
	if message.content == "hello":
		await message.channel.send("pies are better than cakes. change my mind.")

	await bot.process_commands(message) #Key line to allow bot to listen and process !commands.
'''

@bot.event
#create entries in tables 'perUser' and 'privData' for new member.
async def on_member_join(member):
    try:
        cnn = sqlite3.connect(DB_PATH)
        print('connecting to database (on member join)...\n')
        cs = cnn.cursor()
        cs.execute('Select Username From perUser;')
        print('adding member ' + member.name + ' - ' + str(member.id) + '\n')
        cs.execute(insert_newmember(str(member.id), str(member.name)))
        if type(member.nick) == type(None):
            cs.execute(insert_mempriv(str(member.id), str(member.name)))
        else:
            cs.execute(insert_mempriv(str(member.id), str(member.nick)))
        cs.commit()
    except Error as e:
        print(e)
    finally:
        if cnn:
            cnn.close()
    print('member added.')


@bot.event
#delete entries in tables 'perUser' and 'privData' for leaving member.
async def on_member_leave(member):
    try:
        cnn = sqlite3.connect(DB_PATH)
        print('connecting to database (on member leave)...\n')
        cs = cnn.cursor()
        cs.execute('Select Username From perUser;')
        print('deleting member ' + member.name + ' - ' + str(member.id) + '\n')
        cs.execute(delete_member(str(member.id)))
        cs.execute(delete_mempriv(str(member.id)))
        cs.commit()
    except Error as e:
        print(e)
    finally:
        if cnn:
            cnn.close()
    print('member deleted.')


@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == GUILD:
            break

    #sql map file init <https://www.youtube.com/watch?v=xkKvJVs3DR8> setup.
    try:
        with open('member_data.sql', 'r') as sql_file:
            sql = sql_file.read()
        cnn = sqlite3.connect(DB_PATH)
        print('connecting to database...')
        cs= cnn.cursor()
        #cs.executescript(sql) #sql is init sql file. (First time/reformat only)
        #cnn.commit() #sql is init sql file. (First time/reformat only)
        
        cs.execute('Select * From perUser;') #Distinct helps prevent duplicate. 
        print('building db from current member list...')
        for member in guild.members:
            print('adding member ' + member.name + ' - ' + str(member.id))
            cs.execute(insert_newmember(str(member.id), str(member.name))) #see def. table init to current member list.
        cnn.commit()
        
        '''
        cs.execute('Select * From teamData;')
        print('building db from current team list...')
        try:
            for teams in guild.roles:
                print('adding team ' + teams.name)
                cs.execute(add_team(str(teams.name))) #see def. table init to current member list.
            cnn.commit()
        except Error as e2:
            print(e2)
        '''
        
        cs.execute('Select * From privData;')
        print('building db from current nick list...')
        for member in guild.members:
            print('adding nick ' + str(member.nick))
            if type(member.nick) == type(None):
                cs.execute(insert_nick(str(member.id), str(member.name))) #see def. table init to current member list.
            else:
                cs.execute(insert_nick(str(member.id), str(member.nick))) #see def. table init to current member list.
        cnn.commit()

        
        print('printing member list from db...\n')
        #reset cursor
        cs.execute('Select * From perUser;')
        #print complete db. (Tabulate and Panda imports. https://www.delftstack.com/howto/python/data-in-table-format-python/)
        table = cs.fetchall()
        cs.execute('Select * From teamData;')
        table2 = cs.fetchall()
        data = pd.DataFrame(table, columns = ['User_ID','Username','Gob_Qty','Time_Accrued','Hunts','Wings_Obtained', 'Toggle_Stats'])
        data2 = pd.DataFrame(table2, columns = ['Team_Name', 'Channel_ID', 'Gob_Qty', 'Time_Accrued', 'Wings_Found'])
        print(data)
        print(data2)
    except Error as e:
        print(e)
    finally:
        if cnn:
            cnn.close()
    print('db init done.')

bot.run(TOKEN)
