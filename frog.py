import asyncio
from aiogram import Bot, Dispatcher, F, html, Router
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from typing import Any, Dict
from aiogram.utils.chat_action import ChatActionSender
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import paramiko
import servers
import keys
import logging
import ipinfo
import sys
import json
import sqlite3
import string
import random
import requests
import aiohttp

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
print(TOKEN)

access_token = '01431b5e19745e'
handler = ipinfo.getHandler(access_token)


UDP_CUSTOM = '-1001653400671'
XTUNEL = '-1001837669085'

force = False

# User states
user_states = {}
STATE_NONE = 'none'
XTERIA_CREATE = 'awaiting_userename'
admins = [1383981132, 1940595419]
dp = Dispatcher()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


class Form(StatesGroup):
    username = State()
    ip_add = State()
    mesg = State()


# Establish a connection to the SQLite database
def get_db_connection():
    return sqlite3.connect('user_data.db')


# Initialize the database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_user_id INTEGER NOT NULL,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        role TEXT DEFAULT 'user'
    )
    ''')

    # Check if the column exists in the table
    cursor.execute("PRAGMA table_info(users);")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]

    if 'users_id' not in column_names:
        # Alter table to add 'balance' column if it doesn't exist
        cursor.execute("ALTER TABLE users ADD COLUMN users_id DECIMAL(10, 2) DEFAULT 0.00;")
        conn.commit()
    conn.close()


init_db()


def remove_from_database(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE bot_user_id = ?', (user_id,))
    conn.commit()
    conn.close()

#IPLOCATION HELPER(I only need ISP from it)




async def get_all_bot_user_ids():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT bot_user_id FROM users')
    bot_user_ids = cursor.fetchall()
    conn.close()
    return [user_id[0] for user_id in bot_user_ids]



async def get_isp_data(ip_address):
    # Define the API endpoint and the IP address
    api_url = "https://api.iplocation.net/"
    params = {"ip": ip_address}

    try:
        # Make the GET request to the API
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                # Check if the request was successful
                if response.status == 200:
                    # Parse the JSON response
                    data = await response.json()

                    # Extract relevant data
                    country_code2 = data.get("country_code2")
                    isp = data.get("isp")
                    resp_code = data.get("response_code")
                    resp_msg = data.get("response_message")
                    is_alive = f"{resp_code} {resp_msg}"
                    return isp, country_code2, is_alive
                else:
                    print(f"Failed to retrieve data: {response.status}")
                    return None
    except aiohttp.ClientError as e:
        print(f"An error occurred: {e}")
        return None




async def do_req(ip_address):
    details = handler.getDetails(ip_address)
    isp_data = await get_isp_data(ip_address)
    if isp_data:
        isp, country_code2, is_alive = isp_data
        if is_alive == '200 OK':
            statex = "Online ✅"
        else:
            statex = "Dead"

        detos = (f"<i><b><u>Details About This IP address:</u></b></i>\n\nIP: {ip_address}\n\n"
                 f"<b>🌎 Country:</b> {details.country_name}\n\n"
                 f"<b>🌆 City:</b> {details.city}\n\n"
                 f"<b>🎯 Region:</b> {details.region}\n\n"
                 f"<b>🛜 ISP:</b> {isp}\n\n"
                 f"<b>📭 Postal Code:</b> {details.postal}\n\n"
                 f"<b>🟣 Server State:</b> {statex}\n\n"
                 f"<b>⏰ Time Zone:</b> {details.timezone}")
        return detos

async def add_to_database(user_id):
    try:
        # Establish a new connection to the SQLite database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the user already exists in the database
        cursor.execute('SELECT * FROM users WHERE bot_user_id = ?', (user_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            return f'You already exist on the server! Come back after 3 days.'
        else:
            # Insert the new user into the database with role='user'
            cursor.execute('INSERT INTO users (bot_user_id) VALUES (?)',
                           (user_id,))
            conn.commit()
            conn.close()
            return 'success'
    except Exception as e:
        logging.error(f"Error in handle_seller_command: {e}")
        return f'Error: {str(e)}'


async def cancel(state: FSMContext) -> None:
    await state.clear()


async def check_subscription(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking subscription status: {e}")
        return False


# Establish SSH connection
async def establish_ssh_connection(server):
    try:
        credentials = servers.SERVER_CREDENTIALS[server]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(credentials['host'], username=credentials['username'], password=credentials['password'])
        return ssh
    except Exception as e:
        logging.error(f"Error establishing SSH connection to {server}: {e}")
        return None


async def reload_hysteria_daemon(ssh):
    try:
        stdin, stdout, stderr = ssh.exec_command('sudo systemctl daemon-reload')
        stdout.channel.recv_exit_status()  # Wait for the command to complete
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        if error:
            logging.error(f"Error output: {error}")
            return f"Error reloading daemon: {error}"
        else:
            logging.info(f"Command output: {output}")
            return "Daemon Reload was successful"
    except Exception as e:
        logging.error(f"Error reloading daemon: {e}")
        return f"Error reloading daemon: {e}"


# Function to read the JSON file from the remote server
def read_remote_json_file(ssh, remote_file_path):
    try:
        sftp = ssh.open_sftp()
        with sftp.open(remote_file_path, 'r') as file:
            json_data = json.load(file)
        sftp.close()
        return json_data
    except Exception as e:
        logging.error(f"Error reading JSON file from {remote_file_path}: {e}")
        return None


# Function to write the JSON file to the remote server
def write_remote_json_file(ssh, remote_file_path, data):
    try:
        sftp = ssh.open_sftp()
        with sftp.open(remote_file_path, 'w') as file:
            json.dump(data, file, indent=4)
        sftp.close()



    except Exception as e:
        logging.error(f"Error writing JSON file to {remote_file_path}: {e}")


# Function to delete a user from the config
async def delete_hysteria_user(server, username):
    ssh = await establish_ssh_connection(server)
    if ssh:
        try:
            remote_file_path = '/etc/hysteria/config.json'
            data = read_remote_json_file(ssh, remote_file_path)
            if data is None:
                logging.error("Error reading JSON file")
                return

            if 'auth' in data and 'config' in data['auth'] and username in data['auth']['config']:
                data['auth']['config'].remove(username)
                write_remote_json_file(ssh, remote_file_path, data)
                await reload_hysteria_daemon(ssh)
                logging.info(f"Deleted user {username} from {server}")


        except Exception as e:
            logging.error(f"Deleting user failed: {e}")

        finally:
            ssh.close()
    else:
        logging.error("SSH connection error")


# Add user to server
async def add_hysteria_user(server, username):
    ssh = await establish_ssh_connection(server)
    if ssh:
        try:
            # Read the JSON file
            remote_file_path = '/etc/hysteria/config.json'
            data = read_remote_json_file(ssh, remote_file_path)
            if data is None:
                return "Error reading JSON file"

            if username in data['auth']['config']:
                print(f'username {username} already exits')
                return None

            # Modify the "config" key within the "auth" object
            value_to_add = username
            if 'auth' in data and 'config' in data['auth'] and isinstance(data['auth']['config'], list):
                data['auth']['config'].append(value_to_add)
            else:
                data['auth'] = {'config': [value_to_add]}

            # Write the updated JSON file back to the remote server
            write_remote_json_file(ssh, remote_file_path, data)

            await reload_hysteria_daemon(ssh)

            # Log the addition
            logging.info(f"Added user {username} to {server}")

            return "Added user."
        except Exception as e:
            logging.error(f"User addition failed: {e}")
            return None
        finally:
            ssh.close()
    else:
        return "SSH connection error"

def toggle_force():
    """Toggle the boolean value of 'force'."""
    global force
    force = not force

    return force


# OTHER MAIN PARTS OF THE BOT
do_it_again = {}
@dp.message(F.text.lower() == '📲 get servers')
async def get_servers(message: Message, state: FSMContext) -> None:
    rep = ('╭🔴🟡🟢 ────────────────╮\n'
           '│\n'
           '├◉My sponsors want to know\n'
           '│if you joined these channels.\n'
           '│\n'
           '╰─────────────────────╯')
    user_id = message.from_user.id
    async with ChatActionSender.typing(bot=bot, chat_id=user_id):

        if force:
            if (await check_subscription(UDP_CUSTOM, user_id) and await check_subscription(XTUNEL, user_id)):
                await state.set_state(Form.username)
                await message.answer("What's Your first name?\n\nDon't include spaces",
                                     reply_markup=keys.cancel.as_markup())
            else:
                await message.reply(rep, reply_markup=keys.sponsors.as_markup())

        else:
            await state.set_state(Form.username)
            await message.answer("What's Your first name?\n\nDon't include spaces",
                                 reply_markup=keys.cancel.as_markup())

@dp.message(Form.username)
async def fetch_name(message: Message, state: FSMContext) -> None:
    global do_it_again
    user_id = message.from_user.id
    mass = message.text.strip()
    mass1 = mass.split()
    if (mass == '📲 Get Servers' or mass == '💡 Usage Demo' or mass == '🚀Enabled Apps' or mass == 'Src </code>' or mass == '🔎 Looking Glass' or len(mass1) > 1):
        await state.clear()
        dell = await message.reply(f'Oh ooh.. {message.text} is not your name.')
        await asyncio.sleep(3)
        await dell.delete()
        again = await message.answer("Let's Do it again!\n\n"
                             "What's your name?", reply_markup=keys.cancel.as_markup())
        await state.set_state(Form.username)
        do_it_again[user_id] = again

    else:
        random_letters = ''.join(random.choices(string.ascii_letters, k=3))
        real_mass = mass + "-" + random_letters

        try:
            if user_id in do_it_again and do_it_again[user_id] is not None:
                await do_it_again[user_id].delete()
        except AttributeError as e:
            print(f"Error: {e}. Unable to delete.")
        do_it_again[user_id] = None

        await state.update_data(username=real_mass.lower())
        await message.reply(f'Ready to Go, <b><i>{message.text.strip()}</i></b>!\n\n'
                            'Click the Below Button.', reply_markup=keys.get_hysteria.as_markup())

@dp.message(F.text.lower() == 'send updates')
async def louder(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    if user_id in admins:
        await state.set_state(Form.mesg)
        await message.reply('What do you want to Tell Our Bot users?\n\nType the message. Am listening..')

    else:
        await message.reply('Are you nuts? Only admins can do that!')
        return


@dp.message(Form.mesg)
async def make_it_louder(message: Message, state: FSMContext):
    note = message.text.strip()
    users = await get_all_bot_user_ids()
    print(users)
    try:
        for user in users:
            await bot.send_message(user, note)
    except Exception as e:
        return f'{e}'
    await state.clear()






@dp.callback_query(lambda query: query.data == 'create')
async def creates(query: CallbackQuery):
    await query.message.delete()
    jim = 'Available Locations'
    await query.message.answer(jim, reply_markup=keys.SV.as_markup())

async def udpe(msg_exp, user_id):
    ADMIN_CHAT_ID = 6448112643
    bot_user_id = await get_all_bot_user_ids()

    if user_id != ADMIN_CHAT_ID and user_id in bot_user_id:
        try:
            await bot.send_message(user_id, msg_exp)
            await bot.send_message(ADMIN_CHAT_ID, 'Deleted')
        except Exception as e:
            await bot.send_message(ADMIN_CHAT_ID,f'This chat ID:  {user_id }cant be reached')
    return
@dp.callback_query(lambda query: query.data == 'cancel')
async def close(query: CallbackQuery, state: FSMContext):
    await query.message.delete()
    await cancel(state)

days_delay = {}
@dp.callback_query(lambda query: query.data.startswith('add_to_'))
async def adder(query: CallbackQuery, state: FSMContext):
    await query.message.delete()
    data = await state.get_data()
    server_text = query.data.split('_')
    server = server_text[2].upper()
    user_id = query.from_user.id
    tg_user = query.from_user.first_name
    username = data.get('username', 'nothing seen')
    print(username)
    database_check = await add_to_database(user_id)
    waiting = await query.message.answer('Generating...')
    if database_check == 'success':
        result = await add_hysteria_user(server, username)
        hosts = servers.SERVER_CREDENTIALS[server]['host']

        if result:
            await waiting.delete()
            await state.clear()
            gostme = await query.message.answer(f'👩‍🦱 Account created:\n➖➖➖➖➖➖➖➖➖➖\n\n'
                                       f'<b>Host:</b> <code>{hosts}</code>\n'
                                       f'<b>username:</b> <code>{username}</code>\n'
                                       f'<b>password: </b><code>xteria_bot</code>\n'
                                       f'➖➖➖➖➖➖➖➖➖➖\n\n'
                                       f'<i>🎯 UDP Core: <b>Hysteria 1.0[x-teria]</b></i>')
            days_delay[user_id] = gostme
            # Schedule user deletion in 72 hours
            await asyncio.sleep(72 * 3600)
            if user_id in days_delay:
                await days_delay[user_id].delete()
                msg_exp = f"Hello, {tg_user}!\n\nYour Hysteria Server has Just expired.\n\nPlease Create a new one!"
                await udpe(msg_exp, user_id)
                await delete_hysteria_user(server, username)
                remove_from_database(user_id)


    else:
        await waiting.delete()
        await state.clear()
        await query.message.answer(database_check)

    # await query.message.answer('The add_hysteria_function is actively being built. Test later!')
@dp.message(Command('dbase'))
async def handle_dbase(message: Message):
    user_id = message.from_user.id
    print(user_id)
    caption = 'Bot Brain Backed up!'
    TESLA = 6448112643

    if user_id == int(TESLA):
        db_file_path = 'user_data.db'
        if os.path.exists(db_file_path):
            url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
            with open(db_file_path, "rb") as file:
              files = {"document": file}
              params = {"chat_id": user_id, "caption": caption}#
              response = requests.post(url, files=files, data=params)

            if response.status_code == 200:
                print("File sent successfully!")
            else:
                print(f"Failed to send file. Error: {response.text}")

    else:
        await message.reply('Fuck you! Only the Devleper can do that🤓')

@dp.message(F.text.lower() == 'src code')
async def source_rep(message: Message):
    links = "t.me/teslassh"
    repl = (f'Build Your Own VPN app today. \n\nContact the admins of this bot to Buy VPN Source code Today!.\n\n'
            f'-->> <a href="{links}">Tesla SSH </a> (I/O)\n'
            f'-->> @AndroidXtra\n'
            f'➖➖➖➖➖➖➖➖➖➖\n\n')
    await message.reply(repl, reply_markup=keys.dev.as_markup())

@dp.message(F.text.lower() == '🔎 looking glass')
async def infos(message: Message, state: FSMContext):
    await message.reply('Alright, Which IP do you want to look through?')
    await state.set_state(Form.ip_add)

@dp.message(Form.ip_add)
async def looking_glass(message: Message, state: FSMContext):
    ip_blocks = message.text.split('.')
    if len(ip_blocks) == 4:
        ip_address = message.text.strip()
        print(ip_address)
        details = await do_req(ip_address)
        await state.clear()
        await message.reply(details)
    else:
        await message.reply('wrong IP format!\n\nI expected 4 Octects. Try again later.')
        await state.clear()



@dp.message(F.text.lower() == '🚀enabled apps')
async def get_app(message: Message):
    app_msg = ('All servers you create here work good with most apps including:\n\n'
               '- X TUNNEL PRO (Recommended)\n'
               '- Alien Tunnel Pro \n'
               '- 24Vpn\n'
               '- Smk\n'
               '- Royal Tunnel Plus\n'
               '- Demon Tunnel\n'
               '- Binke Tunnel\n'
               '- Maya Tun\n'
               '\n'
               '- <b><i><u>And All Others Except:</u></i></b> \n\n'
               '<a href="t.me/udpcustom"> -UDP CUSTOM</a>\n'
               '<a href="t.me/udp_request"> -UDP REQUEST</a>')
    await message.reply(app_msg, reply_markup=keys.xapp.as_markup(), disable_web_page_preview=True)


@dp.message(F.text.lower() == '💡 usage demo')
async def demo(message: Message):
    Link = 'Follow the video to learn how to use our free hysteria Servers'
    await message.reply(Link, reply_markup=keys.demo.as_markup())


@dp.callback_query(lambda query: query.data == 'verify')
async def verifs(query: CallbackQuery):
    user_id = query.from_user.id
    await query.message.delete()
    async with ChatActionSender.typing(bot=bot, chat_id=user_id):
        delet = await query.message.answer('Okay, Hold on a second...')
        await asyncio.sleep(4)
        await delet.delete()
        if (await check_subscription(UDP_CUSTOM, user_id) and await check_subscription(XTUNEL, user_id)):
            await query.message.answer(
                f'Hello, <b>{query.from_user.first_name}</b>. Lets now create some hysteria Servers\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n\n'
                '<b><i> Click the Create button below to start.</i></b>', reply_markup=keys.get_hysteria.as_markup())
        else:
            force = ('╭🔴🟡🟢 ────────────────╮\n'
                     '│\n'
                     '├◉ I Just saw you are not there\n'
                     '│ Join and we proceed.\n'
                     '│\n'
                     '╰─────────────────────╯')
            await query.message.answer(force, reply_markup=keys.sponsors.as_markup())
@dp.message(F.text.lower() == 'switch')
async def lets_toggle(message: Message):
    switch_state = force
    if switch_state == True:
        gamba = 'ON'
        text = f'Forced Join is Currently Switched <b><i>{gamba}</i></b>'
        await message.answer(text, reply_markup=keys.OFF.as_markup())
    else:
        gamba = 'OFF'
        text = f'Forced Join is Currently <b><i>{gamba}</i></b>'
        await message.answer(text, reply_markup=keys.ON.as_markup())

@dp.callback_query(lambda query: query.data == 'toggle')
async def toggler(query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in admins:
        force = toggle_force()
        await query.message.delete()
        if force == True:
            gamba = 'ON'
            text = f'Forced Join is Currently Switched <b><i>{gamba}</i></b>'
            await query.message.answer(text, reply_markup=keys.OFF.as_markup())
        else:
            gamba = 'OFF'
            text = f'Forced Join is Currently <b><i>{gamba}</i></b>'
            await query.message.answer(text, reply_markup=keys.ON.as_markup())


@dp.message(CommandStart)
async def send_welc(message: Message):
    user = message.from_user.id
    admin_ids = [1383981132, 1940595419]
    if not user in admin_ids:
        repl = ('🐊 Hey! Am Udp Hysteria Server Generator (aka X-teria Proxy)\n\n'
                '✍️ Follow the provided instructions and buttons to generate a free premium Udp Hysteria Server valid for 72 hrs ⏰\n\n'
                '♻️ Always visit this bot to create a new server on Expiring of the previous generated server')
        async with ChatActionSender.typing(bot=bot, chat_id=message.from_user.id):
            await asyncio.sleep(1)
            await message.reply(repl, reply_markup=keys.keyb)
    else:
        repl = ('🐊Hello Mr Admin!\n\n'
                'Here is your National ID:\n\n'
                f'Name: {message.from_user.first_name}\n'
                f'User ID: {message.from_user.id}\n'
                f'Role: Admin\n\n'
                f'You can Use me to control the UDP World!')
        async with ChatActionSender.typing(bot=bot, chat_id=message.from_user.id):
            await asyncio.sleep(1)
            await message.reply(repl, reply_markup=keys.admino)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == '__main__':
    print('Bot is running')
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
