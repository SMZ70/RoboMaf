import logging
import re

import pyrogram.types as pt
from pyrogram.client import Client

from database import has_unfinished_game

log = logging.getLogger("robomaf.utils")


def data_matches_pattern(re_pattern: str):
    def check_pattern(filter, client: Client, update: pt.CallbackQuery):
        log.debug(f"Checking {re_pattern!r} against {update.data}")
        if re.search(re_pattern, update.data):
            return True
        return False

    return check_pattern


def filter_unfinished_game(filter, client: Client, update: pt.CallbackQuery):
    return has_unfinished_game(update.from_user.id)


def chunk_list(lst, r):
    return [lst[i : i + r] for i in range(0, len(lst), r)]
