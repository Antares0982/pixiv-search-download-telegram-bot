# -*- coding: utf-8 -*-
# pylint: disable=W0613, C0116
# type: ignore[union-attr]
# This program is dedicated to the public domain under the CC0 license.


import logging
import os
from configparser import ConfigParser
from typing import List

from pixivpy3 import *
from saucenao_api import SauceNao
from saucenao_api.containers import SauceResponse
from telegram import Message, PhotoSize, Update, chat
from telegram.ext import CallbackContext, Filters, MessageHandler, Updater, CommandHandler

cfgparser = ConfigParser()
cfgparser.read("config.ini")

TOKEN = cfgparser["tgbot"]["TOKEN"]

_REFRESH_TOKEN = cfgparser["pixiv"]["REFRESH_TOKEN"]

sauceapikey = cfgparser["SauceNAO"]["api_key"]

path_store = cfgparser["path"]["store"]

USE_PROXY = cfgparser.getboolean("proxy", "use")

PROXY_URL = cfgparser["proxy"]["url"]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "GitHub repo:\nhttps://github.com/Antares0982/pixiv-search-download-telegram-bot\nTry to send an illustration to me!")


def tgphoto(update: Update):
    ph = update.message.photo[-1]
    photo = ph.get_file()
    extname = photo.file_path[photo.file_path.rfind('.'):]

    print(photo.file_unique_id)
    tpfilepath = os.path.join(path_store, photo.file_unique_id+extname)
    if not os.path.exists(photo.file_unique_id+extname):
        photo.download(tpfilepath)

    return tpfilepath


def dataprocess(response: SauceResponse) -> List[str]:
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

    return pixivids


def sendresult(update: Update, pixivapi: AppPixivAPI, response, pid: str):
    if response is not None and response.illust is not None:
        update.message.reply_text(
            "Found from pixiv, sending original illust...")

        if response.illust.meta_single_page:
            url: str = response.illust.meta_single_page.original_image_url

            pixivapi.download(url, path=path_store)

            fname = os.path.join(path_store, url[url.rfind('/')+1:])
            with open(fname, 'rb') as f:
                try:
                    update.message.reply_photo(
                        f, caption=f"source: https://www.pixiv.net/artworks/{pid}")
                except:
                    update.message.reply_text(
                        "Network error, cannot send this illust")
        else:
            for page in response.illust.meta_pages:
                url = page.image_urls.original
                pixivapi.download(url, path=path_store)

                fname = os.path.join(path_store, url[url.rfind('/')+1:])
                with open(fname, 'rb') as f:
                    try:
                        update.message.reply_photo(
                            f, caption=f"source: https://www.pixiv.net/artworks/{pid}")
                    except:
                        update.message.reply_text(
                            "Network error, cannot send this illust")
    else:
        rttext = "Can't find from pixiv. Other sources:\n"+"\n".join(
            [result.urls[0]+f" similarity:{result.similarity}" for result in results if len(result.urls) > 0])
        update.message.reply_text(rttext)


def photohandler(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Searching...")

    sauce = SauceNao(api_key=sauceapikey)

    pixivapi = AppPixivAPI()
    pixivapi.set_accept_language('en-us')
    pixivapi.auth(refresh_token=_REFRESH_TOKEN)

    tpfilepath = tgphoto(update)

    # Getting result from SauceNAO
    with open(tpfilepath, 'rb') as f:
        try:
            response = sauce.from_file(f)
        except:
            update.message.reply_text("Network error, please retry")
            return

    if not(len(response.results) > 0 and response.results[0].similarity > 70):
        update.message.reply_text("No results")
        return

    pixivids = dataprocess(response)

    response = None

    # Getting result from pixiv
    if len(pixivids) > 0:
        for pid in pixivids:
            try:
                response = pixivapi.illust_detail(pid)
            except:
                update.message.reply_text("Network error, please retry")
            if response.illust is not None:
                break

    if len(pixivids) > 0 and response.illust is None:
        update.message.reply_text(
            "The illustration may be deleted or removed from pixiv")

    sendresult(update, pixivapi, response, pid)


def main():
    if USE_PROXY:
        updater = Updater(token=TOKEN,
                          request_kwargs={'proxy_url': PROXY_URL},
                          use_context=True)
    else:
        updater = Updater(token=TOKEN, use_context=True)

    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(MessageHandler(
        Filters.photo, photohandler))

    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()
