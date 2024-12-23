import asyncio
import logging
import os

import numpy as np
from convopyro import Conversation
from dotenv import load_dotenv
from fancylogging import setup_fancy_logging
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from rich.console import Console
from rich.traceback import install

from database import (
    UserStatus,
    create_game,
    delete_game,
    get_assigned_roles,
    get_players,
    get_roles,
    get_status,
    has_unfinished_game,
    init_db,
    set_assigned_roles,
    set_game_roles,
    set_players,
    set_status,
)
from utils import (
    chunk_list,
    create_data_match_filter,
    create_status_filter,
    filter_unfinished_game,
)

console = Console(tab_size=2)
print = console.print

install(console=console)

log = logging.getLogger("robomaf")
setup_fancy_logging(
    "robomaf",
    console_log_level=logging.INFO,
    file_log_level=logging.DEBUG,
    file_mode="w",
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

app = Client(
    "MafiaNarrator",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
)
Conversation(app)

init_db()
log.info("Database initialized")


@app.on_message(filters=filters.command(["newgame", "sg", "ng"], prefixes=[".", "/"]))
async def handle_new_game(client, message: Message):
    user_id = message.from_user.id
    log.info(f"Starting new game | {user_id}")
    log.info(f"{has_unfinished_game(user_id)}")
    if has_unfinished_game(user_id):
        log.info(f"User has an unfinished game | {user_id}")
        new_msg = await message.reply(
            "You have a game in progress."
            " Do you want to end the game and start a new one?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Yes", callback_data="already_game_yes"),
                        InlineKeyboardButton("No", callback_data="already_game_no"),
                    ],
                ]
            ),
        )
        try:
            log.info(f"Waiting for user to click yes/no | {user_id}")
            answer: CallbackQuery = await client.listen.CallbackQuery(
                filters.user(user_id)
                & filters.create(
                    create_data_match_filter(r"^already_game_(?:(?:yes)|(?:no))$")
                ),
            )

            if "yes" in answer.data:
                log.info(f"User answered yes | {user_id}")
                delete_game(user_id)
                await message.delete(revoke=True)
                await new_msg.delete(revoke=True)
            else:
                log.info(f"User answered no | {user_id}")
                await message.delete(revoke=True)
                await new_msg.delete(revoke=True)
                return
        except TimeoutError:
            log.info(f"TIMEOUT - No yes/no received | {user_id}")
            pass

    log.info(f"Creating game | {user_id}")
    create_game(owner_id=message.from_user.id, players=[])

    log.info(f"Setting status | {user_id}")
    set_status(user_id, UserStatus.CREATING_GAME)

    log.info(f"Getting player names | {user_id}")
    set_status(user_id, UserStatus.GETTING_PLAYERS)
    await message.reply("Please enter player names, one name per line:", quote=True)

    try:
        answer = await client.listen.Message(
            filters.create(create_status_filter(UserStatus.GETTING_PLAYERS))
            & filters.create(filter_unfinished_game)
            & filters.user(user_id)
            & filters.regex(r"^(?![./]).*")
        )
        players = [name.strip() for name in answer.text.split("\n")]
        log.info(
            f"{len(players)} Players received - " + ", ".join(players) + f" | {user_id}"
        )
    except TimeoutError:
        log.info(f"Getting players time out | {user_id}")
        return

    log.info(f"Setting players | {user_id}")
    set_players(user_id, players)

    players_string = "\n".join(
        f"{p+1:>02d} - {player}" for p, player in enumerate(players)
    )
    await answer.reply(
        players_string,
        quote=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Shuffle", callback_data="shuffle_list"),
                    InlineKeyboardButton("Confirm", callback_data="confirm_list"),
                ],
            ]
        ),
    )


@app.on_callback_query(filters=filters.create(create_data_match_filter("shuffle_list")))
async def handle_shuffle(client, callback: CallbackQuery):
    log.info(f"Shuffle request | {callback.from_user.id}")
    message: Message
    message = callback.message
    players = get_players(callback.from_user.id)

    org_order = players.copy()
    n_attempts = 0
    while n_attempts < 10:
        np.random.shuffle(players)
        if (org_order != players) or (len(players) == 1):
            break
        n_attempts += 1
    else:
        return

    log.info(f"Shuffled players: {players} | {callback.from_user.id}")
    log.info(f"Setting players | {callback.from_user.id}")
    set_players(callback.from_user.id, players)

    players_string = "\n".join(
        f"{p+1:02d} - {player}" for p, player in enumerate(players)
    )

    await message.edit(
        players_string,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Shuffle", callback_data="shuffle_list"),
                    InlineKeyboardButton("Confirm", callback_data="confirm_list"),
                ],
            ]
        ),
    )


@app.on_message(filters.regex(r"^(?![./]).*"))
async def handle_plain_text(client, message: Message):
    user_id = message.from_user.id
    user_status = get_status(user_id)

    if user_status == UserStatus.GETTING_GAME_ROLES:
        log.info(f"Getting game roles | {user_id}")
        players = get_players(message.from_user.id)

        log.info(f"Players: {players}")

        roles = [role.strip() for role in message.text.split("\n")]

        log.info(f"Received roles {roles} | {user_id}")
        if len(roles) != len(players):
            log.info(
                f"Incorrect number of roles. expected {len(players)}. Received {len(roles)}"
            )
            await message.reply(
                f"{len(players)} roles expected; you entered {len(roles)}."
                " Please try again."
            )
        else:
            log.info(f"Shuffling roles | {user_id}")
            np.random.shuffle(roles)

            log.info(f"Setting roles | {user_id}")
            set_game_roles(message.from_user.id, roles)
            set_status(message.from_user.id, UserStatus.DISTRIBUTION_ROLES)
            await message.reply(
                "Ready!",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Start",
                                callback_data="start_distribution",
                            )
                        ]
                    ]
                ),
            )


@app.on_callback_query(filters=filters.create(create_data_match_filter("confirm_list")))
async def handle_confirm(client, callback: CallbackQuery):
    message: Message
    message = callback.message
    user_id = callback.from_user.id

    log.info(f"Confirm request received | {user_id}")
    await message.edit(text=message.text, reply_markup=None)

    set_status(user_id, UserStatus.GETTING_GAME_ROLES)
    await message.reply("Please enter roles, one role per line", quote=True)


@app.on_callback_query(filters=filters.create(create_data_match_filter("show_role")))
async def handle_show_role(client: Client, callback: CallbackQuery):
    log.info(f"Showing roles | {callback.from_user.id}")

    players = get_players(callback.from_user.id)
    roles = get_assigned_roles(callback.from_user.id)

    response = "\n".join(
        f"{i:02d} - {player}: {role}"
        for i, (player, role) in enumerate(zip(players, roles), start=1)
    )
    await callback.message.reply(response)
    await callback.message.delete(revoke=True)

    delete_game(callback.from_user.id)


@app.on_callback_query(
    filters=filters.create(create_data_match_filter(r"^role_\d+$"))
    | filters.create(create_data_match_filter("start_distribution")),
)
async def handle_select_box(client: Client, callback: CallbackQuery):
    players = get_players(callback.from_user.id)
    all_roles = get_roles(callback.from_user.id)
    assigned_roles = get_assigned_roles(callback.from_user.id)

    remaining_roles = all_roles.copy()
    for role in assigned_roles:
        remaining_roles.remove(role)

    player_idx = len(assigned_roles)

    if callback.data.startswith("role_"):
        role_idx = int(callback.data.split("_")[-1])
        selected_role = remaining_roles[role_idx]
        log.info(
            f"Player {player_idx}: {players[player_idx]}"
            f" selected role {role_idx}: {selected_role!r} "
        )

        await callback.message.edit(
            f"{players[player_idx]}\nYour role:\n{selected_role}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Next ⏭️", callback_data="next")]]
            ),
        )
        await client.listen.CallbackQuery(
            filters.user(callback.from_user.id)
            & filters.create(filter_unfinished_game)
            & filters.create(create_status_filter(UserStatus.DISTRIBUTION_ROLES))
        )

        remaining_roles.remove(selected_role)
        assigned_roles.append(selected_role)
        set_assigned_roles(callback.from_user.id, assigned_roles)

        player_idx += 1
    elif callback.data.startswith("start_distribution"):
        log.info(f"Setting status to distribution | {callback.from_user.id}")
        set_status(callback.from_user.id, UserStatus.DISTRIBUTION_ROLES)

    if remaining_roles:
        boxes = chunk_list(
            [
                InlineKeyboardButton("📦", callback_data=f"role_{r}")
                for r, role in enumerate(remaining_roles)
            ],
            4,
        )
        await callback.message.edit(
            f"{players[player_idx]}\nPlease select a box:",
            reply_markup=InlineKeyboardMarkup(boxes),
        )
    else:
        await callback.message.edit(
            "Finish",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Roles", callback_data="show_roles")]]
            ),
        )


async def main():
    await app.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    log.info("Starting bot")
    loop.create_task(main())
    loop.run_forever()
