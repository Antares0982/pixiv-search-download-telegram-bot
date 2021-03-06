# pixiv-search-download-telegram-bot
> download the original illustration from Pixiv using SauceNAO and pixivpy

```
pip3 install -r requirements.txt
```

## Instructions

* Rename `sample-config.ini ` to `config.ini`

* Fill in your api keys or tokens (the refresh key of section "pixiv" in sample is the key from [pixivpy demo](https://github.com/upbit/pixivpy/blob/master/demo.py).)

  * Telegram: get your own bot [here](https://t.me/botfather). socks5 is suggested if you need proxies.
  * Pixiv: You may need to [get your own refresh key](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362).
  * SauceNAO: get your api-key [here](https://saucenao.com/), click "account" to sign in/up.
  * Set up your default proxy if you need. 
  * Choose the paths to store illustrations and temp file from telegram. Also a json file to store search history.
  * If you need to search many times and frequently exceed the daily search limit, then fill in "alternative" section to use different proxies and SauceNAO api keys. But first you need to set up your proxies to different ports.
  * You can enable or disable command `/random`, which makes the bot send an illustration in search history.

* ```
  python3 main_pixivbot.py
  ```

And it's done!

## Usage

Send an image (could be low definition, with watermarks, or processed) to your bot. The bot will send back the original illustration if found in Pixiv, or send other sources if found any.