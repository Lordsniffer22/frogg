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
import sys
import json
import sqlite3
import string
import random

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
print(TOKEN)
UDP_CUSTOM = '-1001653400671'
XTUNEL = '-1001837669085'

force = False

# User states
user_states = {}
STATE_NONE = 'none'
XTERIA_CREATE = 'awaiting_userename'

dp = Dispatcher()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


class Form(StatesGroup):
    username = State()


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
    conn.commit()
    conn.close()


init_db()


def remove_from_database(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE bot_user_id = ?', (user_id))
    conn.commit()
    conn.close()


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


import paramiko


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


async def reload_hysteria_daemon(server):
    ssh = await establish_ssh_connection(server)
    if ssh:
        try:
            stdin, stdout, stderr = ssh.exec_command('sudo systemctl restart hysteria-server')
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
        finally:
            ssh.close()
    else:
        return "SSH connection error"


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
                logging.info(f"Deleted user {username} from {server}")
                await reload_hysteria_daemon(server)

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


# OTHER MAIN PARTS OF THE BOT

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


def toggle_force():
    """Toggle the boolean value of 'force'."""
    global force
    force = not force

    return force


@dp.message(F.text.lower() == 'force')
async def force_switch(message: Message):
    user_id = message.from_user.id
    if user_id == 1383981132 or user_id == 1940595419:
        force = toggle_force()
        if force == True:
            await message.reply(f'Force Join Has been Turned ON')
        else:
            await message.reply(f'Force Join Has been Turned OFF')

    else:
        await message.reply('Nice try')


@dp.message(Form.username)
async def fetch_name(message: Message, state: FSMContext) -> None:
    mass = message.text.strip()
    random_letters = ''.join(random.choices(string.ascii_letters, k=3))
    real_mass = mass + "-" + random_letters

    await state.update_data(username=real_mass.lower())
    await message.reply(f'Ready to Go, <b><i>{message.text.strip()}</i></b>!\n\n'
                        'Click the Below Button.', reply_markup=keys.get_hysteria.as_markup())


@dp.callback_query(lambda query: query.data == 'create')
async def creates(query: CallbackQuery):
    await query.message.delete()
    jim = 'Available Locations'
    await query.message.answer(jim, reply_markup=keys.SV.as_markup())


@dp.callback_query(lambda query: query.data == 'cancel')
async def close(query: CallbackQuery, state: FSMContext):
    await query.message.delete()
    await cancel(state)


@dp.callback_query(lambda query: query.data.startswith('add_to_'))
async def adder(query: CallbackQuery, state: FSMContext):
    await query.message.delete()
    data = await state.get_data()
    server_text = query.data.split('_')
    server = server_text[2].upper()
    user_id = query.from_user.id
    username = data.get('username', 'nothing seen')
    print(username)
    database_check = await add_to_database(user_id)
    waiting = await query.message.answer('Generating...')
    if database_check == 'success':
        result = await add_hysteria_user(server, username)
        hosts = servers.SERVER_CREDENTIALS[server]['host']

        if result:
            await waiting.delete()
            allowed = f'➖➖➖➖➖➖➖➖➖➖\n\n'\
                      f'- X Tunnel Pro\n'\
                      f'- Alien Tunnel\n'\
                      f'- Idroid \n'
            await query.message.answer(f'👩‍🦱 Account created:\n➖➖➖➖➖➖➖➖➖➖\n\n'
                                       f'<b>Host:</b> <code>{hosts}</code>\n'
                                       f'<b>username:</b> <code>{username}</code>\n'
                                       f'<b>password: </b><code>xteria_bot</code>\n\n'
                                       f'<i><u><b>📲 Compatible with:</b> </u>\n'
                                       f'{html.quote(allowed)}'
                                       f'➖➖➖➖➖➖➖➖➖➖\n\n'
                                       f'🎯 UDP Core: <b>Hysteria 1.0[x-teria]</b></i>')

            await reload_hysteria_daemon(server)

            # Schedule user deletion in 24 hours
            await asyncio.sleep(72 * 3600)
            await delete_hysteria_user(server, username)
            remove_from_database(user_id)


    else:
        await waiting.delete()
        await query.message.answer(database_check)

    # await query.message.answer('The add_hysteria_function is actively being built. Test later!')


@dp.message(F.text.lower() == 'src </code>')
async def source_rep(message: Message):
    links = "t.me/teslassh"
    repl = (f'Build Your Own VPN app today. \n\nContact the admins of this bot to Buy VPN Source code Today!.\n\n'
            f'-->> <a href="{links}">Tesla SSH </a> (I/O)\n'
            f'-->> @AndroidXtra\n'
            f'➖➖➖➖➖➖➖➖➖➖\n\n')
    await message.reply(repl, reply_markup=keys.dev.as_markup())


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


@dp.message(Command('start'))
async def send_welc(message: Message):


    repl = ('🐊 Hey! Am Udp Hysteria Server Generator (aka X-teria Proxy)\n\n'
             '✍️ Follow the provided instructions and buttons to generate a free premium Udp Hysteria Server valid for 24hrs ⏰\n\n'
             '♻️ Always visit this bot to create a new server on Expiring of the previous generated server')
    async with ChatActionSender.typing(bot=bot, chat_id=message.from_user.id):
        await asyncio.sleep(1)
        await message.reply(repl, reply_markup=keys.keyb)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == '__main__':
    print('Bot is running')
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
