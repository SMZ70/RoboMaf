import logging
import re

import pyrogram.types as pt
from pyrogram.client import Client

from database import UserStatus, get_status, has_unfinished_game

log = logging.getLogger("robomaf.utils")


def create_data_match_filter(re_pattern: str):
    def check_pattern(filter, client: Client, update: pt.CallbackQuery):
        log.debug(f"Checking {re_pattern!r} against {update.data}")
        if re.search(re_pattern, update.data):
            return True
        return False

    return check_pattern


def filter_unfinished_game(filter, client: Client, update: pt.CallbackQuery):
    return has_unfinished_game(update.from_user.id)


def create_status_filter(status: UserStatus):
    def filter_game_status(filter, client: Client, update: pt.CallbackQuery):
        try:
            real_status = get_status(update.from_user.id)
        except ValueError:
            return False
        return real_status == status

    return filter_game_status


def chunk_list(lst, r):
    return [lst[i : i + r] for i in range(0, len(lst), r)]
