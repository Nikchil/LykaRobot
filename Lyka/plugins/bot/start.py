# ---------------------------------------------------------
# BeatGuard Bot - All rights reserved
# ---------------------------------------------------------
# This code is part of the BeatGuard Bot project.
# Unauthorized copying, distribution, or use is prohibited.
# © Graybots™. All rights reserved.
# ---------------------------------------------------------

import time
from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtubesearchpython.__future__ import VideosSearch

from config import BANNED_USERS, SUPPORT_CHAT, LOGGER_ID, START_IMG_URL
from BeatGuard import app
from BeatGuard.misc import _boot_
from BeatGuard.plugins.sudo.sudoers import sudoers_list
from BeatGuard.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_served_chats,
    get_served_users,
    get_lang,
    is_banned_user,
    is_on_off,
)
from BeatGuard.utils import bot_sys_stats
from BeatGuard.utils.decorators.language import LanguageStart
from BeatGuard.utils.formatters import get_readable_time
from BeatGuard.utils.inline import help_pannel, private_panel, start_panel
from strings import get_string


@app.on_message(filters.command("start") & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)
    if len(message.text.split()) > 1:
        payload = message.text.split(None, 1)[1]
        if payload.startswith("help"):
            return await message.reply_photo(
                photo=START_IMG_URL,
                caption=_["help_1"].format(SUPPORT_CHAT),
                reply_markup=help_pannel(_),
            )
        elif payload.startswith("sud"):
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                return await app.send_message(
                    LOGGER_ID,
                    f"✦ {message.from_user.mention} started bot to check <b>sudolist</b>.\n\n"
                    f"<b>UID ➠</b> <code>{message.from_user.id}</code>\n"
                    f"<b>Username ➠</b> @{message.from_user.username}",
                )
            return
        elif payload.startswith("inf"):
            m = await message.reply_text("🔎")
            query = f"https://www.youtube.com/watch?v={payload.replace('info_', '', 1)}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]

            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, app.mention
            )
            key = InlineKeyboardMarkup([
                [InlineKeyboardButton(_["S_B_8"], url=link),
                 InlineKeyboardButton(_["S_B_9"], url=SUPPORT_CHAT)]
            ])
            await m.delete()
            await app.send_photo(message.chat.id, photo=thumbnail, caption=searched_text, reply_markup=key)

            if await is_on_off(2):
                return await app.send_message(
                    LOGGER_ID,
                    f"✦ {message.from_user.mention} started bot to check <b>track info</b>.\n\n"
                    f"✦ <b>UID ➠</b> <code>{message.from_user.id}</code>\n"
                    f"✦ <b>Username ➠</b> @{message.from_user.username}",
                )
    else:
        out = private_panel(_)
        served_chats = len(await get_served_chats())
        served_users = len(await get_served_users())
        UP, CPU, RAM, DISK = await bot_sys_stats()
        caption = _["start_2"].format(
            message.from_user.mention,
            app.mention,
            UP,
            DISK,
            CPU,
            RAM,
        )
        await message.reply_photo(
            photo=START_IMG_URL,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(out),
        )
        if await is_on_off(2):
            return await app.send_message(
                LOGGER_ID,
                f"✦ {message.from_user.mention} started the bot.\n\n"
                f"✦ <b>UID ➠</b> <code>{message.from_user.id}</code>\n"
                f"✦ <b>Username ➠</b> @{message.from_user.username}",
            )


@app.on_message(filters.command("start") & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    caption = _["start_1"].format(app.mention, get_readable_time(uptime))
    await message.reply_photo(
        photo=START_IMG_URL,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(out),
    )
    return await add_served_chat(message.chat.id)


@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except:
                    pass
            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)

                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)
                caption = _["start_3"].format(
                    message.from_user.mention,
                    app.mention,
                    message.chat.title,
                    app.mention,
                )
                await message.reply_photo(
                    photo=START_IMG_URL,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(out),
                )
                await add_served_chat(message.chat.id)
                await message.stop_propagation()
        except Exception as ex:
            print(ex)
