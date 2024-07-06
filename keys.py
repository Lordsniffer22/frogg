from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


udpcustom = 'udpcustom'
udprex = 'xtunnelpro'
keyb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text='📲 Get Servers'),
            KeyboardButton(text='💡 Usage Demo')
        ],
[
            KeyboardButton(text='🚀Enabled Apps'),
            KeyboardButton(text='Src </code>')
        ]

    ],
    resize_keyboard=True
)

sponsors = InlineKeyboardBuilder()
markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🟢 UDP Custom', url=f"https://t.me/{udpcustom}"),
     InlineKeyboardButton(text='🔴 X TUNNEL PRO', url=f"https://t.me/{udprex}")],
    [InlineKeyboardButton(text='Verify Membership', callback_data=f'verify')
 ]
])  # Some markup
sponsors.attach(InlineKeyboardBuilder.from_markup(markup))


get_hysteria = InlineKeyboardBuilder()
markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='CREATE', callback_data='create')
 ]
])  # Some markup
get_hysteria.attach(InlineKeyboardBuilder.from_markup(markup))

xapp = InlineKeyboardBuilder()
markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Get X Tunnel Pro', url='https://t.me/xtunnelpro/1635')
 ]
])  # Some markup
xapp.attach(InlineKeyboardBuilder.from_markup(markup))

dev = InlineKeyboardBuilder()
markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='About The Devs', url='https://t.me/zero_contract_devs')
 ]
])  # Some markup
dev.attach(InlineKeyboardBuilder.from_markup(markup))

demo = InlineKeyboardBuilder()
markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Watch Video', url='https://t.me/xtunnelpro/942')
 ]
])  # Some markup
demo.attach(InlineKeyboardBuilder.from_markup(markup))


SV = InlineKeyboardBuilder()
markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🇺🇸 USA', callback_data='add_to_usa')
 ]
])  # Some markup
SV.attach(InlineKeyboardBuilder.from_markup(markup))

cancel = InlineKeyboardBuilder()
markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='cancel', callback_data='cancel')
 ]
])  # Some markup
cancel.attach(InlineKeyboardBuilder.from_markup(markup))