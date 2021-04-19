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
from telegram import Message, PhotoSize, Update, chat
from telegram.ext import CallbackContext, Filters, MessageHandler, Updater

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


def testphotohandler(update: Update, context: CallbackContext) -> None:
    sauce = SauceNao(api_key=sauceapikey)

    pixivapi = AppPixivAPI()
    pixivapi.set_accept_language('en-us')
    pixivapi.auth(refresh_token=_REFRESH_TOKEN)

    ph = update.message.photo[-1]
    photo = ph.get_file()
    extname = photo.file_path[photo.file_path.rfind('.'):]
    tpfilepath = os.path.join(path_store, "tempfile"+extname)

    photo.download(tpfilepath)

    with open(tpfilepath, 'rb') as f:
        response = sauce.from_file(f)
    os.remove(tpfilepath)

    if not(len(response.results) > 0 and response.results[0].similarity > 70):
        update.message.reply_text("No results")
        return

    results = [x for x in response.results if x.similarity > 70]

    pixivid: str = ""
    for result in results:

        if pixivid != "":
            continue

        if 'pixiv_id' in result.raw['data']:
            pixivid = str(result.raw['data']['pixiv_id'])
        elif "source" in result.raw["data"] and result.raw["data"]["source"].startswith("https://i.pximg.net"):
            scurl = result.raw["data"]["source"]
            pixivid = scurl[scurl.rfind('/')+1:]

    if pixivid != "":
        update.message.reply_text("Found from pixiv, sending original illust")
        response = pixivapi.illust_detail(pixivid)

        if response.illust.meta_single_page:
            url: str = response.illust.meta_single_page.original_image_url
            pixivapi.download(url, path=path_store)

            fname = os.path.join(path_store, url[url.rfind('/')+1:])
            with open(fname, 'rb') as f:
                update.message.reply_photo(
                    f, caption=f"source: https://www.pixiv.net/en/artworks/{pixivid}")
        else:
            for page in response.illust.meta_pages:
                url = page.image_urls.original
                pixivapi.download(url, path=path_store)

                fname = os.path.join(path_store, url[url.rfind('/')+1:])
                with open(fname, 'rb') as f:
                    update.message.reply_photo(
                        f, caption=f"source: https://www.pixiv.net/en/artworks/{pixivid}")
    else:
        rttext = "Can't find from pixiv. Other sources:\n"+"\n".join(
            [result.urls[0]+f" similarity:{result.similarity}" for result in results if len(result.urls) > 0])
        update.message.reply_text(rttext)


def main():
    if USE_PROXY:
        updater = Updater(token=TOKEN,
                          request_kwargs={'proxy_url': PROXY_URL},
                          use_context=True)
    else:
        updater = Updater(token=TOKEN, use_context=True)

    updater.dispatcher.add_handler(MessageHandler(
        (Filters.photo) & (~Filters.command), testphotohandler))

    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()
