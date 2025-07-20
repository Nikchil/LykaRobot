# BeatGuard - All rights reserved
# --------------------------------
# This code is owned by BeatGuard and is protected.
# Unauthorized copying or distribution is prohibited.
# © Graybots™. All rights reserved.

import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    NoActiveGroupCall,
)
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio, MediumQualityVideo
from pytgcalls.types.stream import StreamAudioEnded

import config
from Lyka import LOGGER, YouTube, app
from Lyka.misc import db
from Lyka.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from Lyka.utils.exceptions import AssistantErr
from Lyka.utils.formatters import check_duration, seconds_to_min, speed_converter
from Lyka.utils.inline.play import stream_markup, telegram_markup
from Lyka.utils.stream.autoclear import auto_clean
from Lyka.utils.thumbnails import get_thumb
from strings import get_string

autoend = {}
counter = {}


async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


class Call(PyTgCalls):
    def __init__(self):
        self.userbot1 = Client("LykaAss1", config.API_ID, config.API_HASH, session_string=str(config.STRING1))
        self.one = PyTgCalls(self.userbot1, cache_duration=100)

        self.userbot2 = Client("LykaAss2", config.API_ID, config.API_HASH, session_string=str(config.STRING2))
        self.two = PyTgCalls(self.userbot2, cache_duration=100)

        self.userbot3 = Client("LykaXAss3", config.API_ID, config.API_HASH, session_string=str(config.STRING3))
        self.three = PyTgCalls(self.userbot3, cache_duration=100)

        self.userbot4 = Client("LykaXAss4", config.API_ID, config.API_HASH, session_string=str(config.STRING4))
        self.four = PyTgCalls(self.userbot4, cache_duration=100)

        self.userbot5 = Client("LykaAss5", config.API_ID, config.API_HASH, session_string=str(config.STRING5))
        self.five = PyTgCalls(self.userbot5, cache_duration=100)

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause_stream(chat_id)

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume_stream(chat_id)

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_group_call(chat_id)
        except:
            pass

    async def stop_stream_force(self, chat_id: int):
        for assistant, string in zip([self.one, self.two, self.three, self.four, self.five],
                                     [config.STRING1, config.STRING2, config.STRING3, config.STRING4, config.STRING5]):
            try:
                if string:
                    await assistant.leave_group_call(chat_id)
            except:
                pass
        try:
            await _clear_(chat_id)
        except:
            pass

    async def speedup_stream(self, chat_id: int, file_path, speed, playing):
        assistant = await group_assistant(self, chat_id)
        if str(speed) != str("1.0"):
            base = os.path.basename(file_path)
            chatdir = os.path.join(os.getcwd(), "playback", str(speed))
            os.makedirs(chatdir, exist_ok=True)
            out = os.path.join(chatdir, base)

            if not os.path.isfile(out):
                vs = {"0.5": 2.0, "0.75": 1.35, "1.5": 0.68, "2.0": 0.5}.get(str(speed), 1.0)
                proc = await asyncio.create_subprocess_shell(
                    f"ffmpeg -i {file_path} -filter:v setpts={vs}*PTS -filter:a atempo={speed} {out}",
                    stdin=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
        else:
            out = file_path

        dur = int(await asyncio.get_event_loop().run_in_executor(None, check_duration, out))
        played, con_seconds = speed_converter(playing[0]["played"], speed)
        duration = seconds_to_min(dur)

        stream = AudioVideoPiped(
            out,
            audio_parameters=HighQualityAudio(),
            video_parameters=MediumQualityVideo(),
            additional_ffmpeg_parameters=f"-ss {played} -to {duration}",
        ) if playing[0]["streamtype"] == "video" else AudioPiped(
            out,
            audio_parameters=HighQualityAudio(),
            additional_ffmpeg_parameters=f"-ss {played} -to {duration}",
        )

        if str(db[chat_id][0]["file"]) == str(file_path):
            await assistant.change_stream(chat_id, stream)
        else:
            raise AssistantErr("Umm")

        if str(db[chat_id][0]["file"]) == str(file_path):
            db[chat_id][0].update({
                "played": con_seconds,
                "dur": duration,
                "seconds": dur,
                "speed_path": out,
                "speed": speed,
                "old_dur": db[chat_id][0].get("dur"),
                "old_second": db[chat_id][0].get("seconds")
            })

    async def force_stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            db.get(chat_id).pop(0)
        except:
            pass
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)
        try:
            await assistant.leave_group_call(chat_id)
        except:
            pass

    async def join_call(self, chat_id: int, original_chat_id: int, link, video=None, image=None):
        assistant = await group_assistant(self, chat_id)
        language = await get_lang(chat_id)
        _ = get_string(language)

        stream = AudioVideoPiped(
            link,
            audio_parameters=HighQualityAudio(),
            video_parameters=MediumQualityVideo(),
        ) if video else AudioPiped(link, audio_parameters=HighQualityAudio())

        try:
            await assistant.join_group_call(
                chat_id,
                stream,
                stream_type=StreamType().pulse_stream,
            )
        except NoActiveGroupCall:
            raise AssistantErr(_["call_8"])
        except AlreadyJoinedError:
            raise AssistantErr(_["call_9"])
        except Exception:
            raise AssistantErr(_["call_10"])

        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)
        if await is_autoend():
            counter[chat_id] = {}
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    # All other functions remain unchanged (skip_stream, seek_stream, change_stream, etc.)
    # If needed, I can refactor and update the rest too.
