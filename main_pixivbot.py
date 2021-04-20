# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

import json
import logging
import os
from configparser import ConfigParser
from typing import Dict, List, Tuple

from pixivpy3 import *
from saucenao_api import SauceNao
from saucenao_api.containers import BasicSauce, SauceResponse
from telegram import Update
from telegram.ext import (CallbackContext, CommandHandler, Filters,
                          MessageHandler, Updater)

cfgparser = ConfigParser()
cfgparser.read("config.ini")

TOKEN = cfgparser["tgbot"]["TOKEN"]

_REFRESH_TOKEN = cfgparser["pixiv"]["REFRESH_TOKEN"]

sauceapikey = cfgparser["SauceNAO"]["api_key"]

path_store = cfgparser["path"]["store"]
if not os.path.exists(path_store):
    os.makedirs(path_store)

path_temp = cfgparser["path"]["tempillust"]
if not os.path.exists(path_temp):
    os.makedirs(path_temp)

path_history = cfgparser["path"]["history_json"]
try:
    with open(path_history, 'r', encoding='utf-8') as f:
        searchHistoryMap = json.load(f)
except FileNotFoundError:
    with open(path_history, 'w', encoding='utf-8') as f:
        json.dump({}, f)
    searchHistoryMap = {}

USE_PROXY = cfgparser.getboolean("proxy", "use")

PROXY_URL = cfgparser["proxy"]["url"]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

pixivapi: AppPixivAPI = None

searchHistoryMap: Dict[str, List[str]]


def checkPixivapi() -> bool:
    response = pixivapi.illust_detail('85281729')
    return False if response.illust is None else True


def renewPixivapi() -> None:
    global pixivapi
    pixivapi = AppPixivAPI()
    pixivapi.set_accept_language('en-us')
    pixivapi.auth(refresh_token=_REFRESH_TOKEN)


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "GitHub repo:\nhttps://github.com/Antares0982/pixiv-search-download-telegram-bot\nTry to send an illustration to me!\nWill not receive any group/channel message.")


def tgphoto(update: Update) -> str:
    """return filepath"""
    ph = update.message.photo[-1]
    photo = ph.get_file()
    extname = photo.file_path[photo.file_path.rfind('.'):]

    tpfilepath = os.path.join(path_store, photo.file_unique_id+extname)
    if not os.path.exists(photo.file_unique_id+extname):
        photo.download(tpfilepath)

    return tpfilepath


def dataprocess(response: SauceResponse) -> Tuple[List[str], List[BasicSauce]]:
    results = [x for x in response.results if x.similarity > 70]

    pixivids: List[str] = []
    for result in results:

        if 'pixiv_id' in result.raw['data']:
            newpid = str(result.raw['data']['pixiv_id'])
            pixivids.append(newpid) if newpid not in pixivids else ...
        elif "source" in result.raw["data"] and result.raw["data"]["source"].startswith("https://i.pximg.net"):
            scurl = result.raw["data"]["source"]
            newpid = scurl[scurl.rfind('/')+1:]
            pixivids.append(newpid) if newpid not in pixivids else ...

    return pixivids, results


def sendResult(update: Update, response, pid: str, results: List[BasicSauce]) -> List[str]:
    ans: List[str]
    if response is not None and response.illust is not None:
        update.message.reply_text(
            "Found from pixiv, sending original illust...")

        if response.illust.meta_single_page:
            url: str = response.illust.meta_single_page.original_image_url

            pixivapi.download(url, path=path_store)

            fname = os.path.join(path_store, url[url.rfind('/')+1:])
            ans = [fname]
            with open(fname, 'rb') as f:
                try:
                    update.message.reply_document(
                        f, caption=f"source: https://www.pixiv.net/artworks/{pid}")
                except:
                    try:
                        update.message.reply_text(
                            "Network error, cannot send this illust. Please retry")
                    except:
                        ...
        else:
            ans = []
            for page in response.illust.meta_pages:
                url = page.image_urls.original
                pixivapi.download(url, path=path_store)

                fname = os.path.join(path_store, url[url.rfind('/')+1:])
                ans.append(fname)
                with open(fname, 'rb') as f:
                    try:
                        update.message.reply_document(
                            f, caption=f"source: https://www.pixiv.net/artworks/{pid}")
                    except:
                        try:
                            update.message.reply_text(
                                "Network error, cannot send one illust. Please retry")
                        except:
                            ...
        return ans
    if len(results) > 0:
        rturls = "\n".join(
            [result.urls[0]+f" similarity:{result.similarity}" for result in results if len(result.urls) > 0])
        if rturls != "":
            update.message.reply_text(
                "Can't find from pixiv. Other sources:\n"+rturls)
            return ["Can't find from pixiv. Other sources:\n"+rturls]

    update.message.reply_text("no results")
    return []


def sendbyhistory(update: Update, key: str) -> None:
    ans = searchHistoryMap[key]
    if len(ans) == 0:
        update.message.reply_text("no results")
        return

    if len(ans) == 1 and ans[0].find("Can't find from pixiv.") == 0:
        update.message.reply_text(ans[0])
        return

    pid = ans[0][ans[0].rfind('/')+1:ans[0].rfind('_')]
    for fname in ans:
        with open(fname, 'rb') as f:
            try:
                update.message.reply_document(
                    f, caption=f"source: https://www.pixiv.net/artworks/{pid}")
            except:
                try:
                    if len(ans) == 1:
                        update.message.reply_text(
                            "Network error, cannot send this illust. Please retry")
                    else:
                        update.message.reply_text(
                            "Network error, cannot send one illust. Please retry")
                except:
                    ...


def photohandler(update: Update, context: CallbackContext) -> None:

    if update.effective_chat.type != "private":
        return

    if not checkPixivapi():
        renewPixivapi()

    update.message.reply_text("Searching...")

    sauce = SauceNao(api_key=sauceapikey)

    tpfilepath = tgphoto(update)
    if tpfilepath in searchHistoryMap:
        sendbyhistory(tpfilepath)
        return

    # Getting result from SauceNAO
    with open(tpfilepath, 'rb') as f:
        try:
            response = sauce.from_file(f)
        except:
            update.message.reply_text(
                "Network error when connecting to SauceNAO, please retry. If this happens frequently, maybe the daily search limit exceeded.")
            return

    if not(len(response.results) > 0 and response.results[0].similarity > 70):
        update.message.reply_text("No results")
        return

    pixivids, results = dataprocess(response)

    response = None

    # Getting result from pixiv
    pid = None
    if len(pixivids) > 0:

        for pid in pixivids:
            try:
                response = pixivapi.illust_detail(pid)
            except:
                update.message.reply_text(
                    "Network error when connecting to Pixiv, please retry")
            if response.illust is not None:
                break

    if len(pixivids) > 0 and response.illust is None:
        update.message.reply_text(
            "The illustration may be removed from pixiv")

    mapvalue = sendResult(update, response, pid, results)
    searchHistoryMap[tpfilepath] = mapvalue
    with open(path_history, 'w', encoding='utf-8') as f:
        json.dump(searchHistoryMap, f)


def main():
    try:
        renewPixivapi()
    except PixivError:
        exit(1)
    if USE_PROXY:
        updater = Updater(token=TOKEN,
                          request_kwargs={'proxy_url': PROXY_URL},
                          use_context=True)
    else:
        updater = Updater(token=TOKEN, use_context=True)

    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("help", start))
    updater.dispatcher.add_handler(MessageHandler(
        Filters.photo, photohandler))

    updater.start_polling(drop_pending_updates=True)

    updater.idle()


if __name__ == '__main__':
    main()
