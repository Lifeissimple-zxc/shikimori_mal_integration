import requests
import json
import logging
import asyncio
from aiohttp import ClientSession
from dotenv import load_dotenv
from os import getenv
from datetime import datetime, timedelta
from pathlib import Path
from atexit import register
from migrationToolbox import ShikimoriClient
from migrationToolbox import (
    SHIKI_CLIENT_ID,
    SHIKI_CLIENT_SECRET,
    SHIKI_REDIRECT_URL,
    SHIKI_AUTH_CODE
)

# Logging config
logger = logging.getLogger("mainLogger")
logger.setLevel(logging.DEBUG)



# Configs - move to yaml
SHIKI_SCOPES = "user_rates+comments+topics"
SHIKI_OAUTH_CACHE = "Cache/shiki_token.json"
SHIKI_APP = "MAL_migrator"
# https://pypi.org/project/asyncio-atexit/ to register session closure

shikimori = ShikimoriClient(clientId = SHIKI_CLIENT_ID,
                            clientSecret = SHIKI_CLIENT_SECRET,
                            redirectUrl = SHIKI_REDIRECT_URL,
                            authCode = SHIKI_AUTH_CODE,
                            appName = SHIKI_APP,
                            tokenPath = SHIKI_OAUTH_CACHE)

loop = asyncio.new_event_loop()

GET_URLS = ["https://shikimori.one/api/users/whoami"]

URL = "https://shikimori.one/api/users/whoami"

async def test1():
    print("Preparing tasks")
    print(shikimori.token)
    async with ClientSession() as sesh:
        for url in GET_URLS:
            await shikimori.mainQueue.put(shikimori._getRequestCoro(url = url,sesh = sesh,
                                                            headers = shikimori.headers))
        
        print("Starting async execution")
        await shikimori.processTasks(loop = loop)

async def test2():
    print("Trying a simple 1-off request")
    headers = {
        "User-Agent": "MAL_migrator",
        "Authorization": f"Bearer {shikimori.token['access_token']}"
    }
    async with ClientSession() as sesh:
        dat = await shikimori._getRequestCoro(url = URL, sesh = sesh, headers = headers)
        print(dat)


loop.run_until_complete(test1())
# loop.run_until_complete(test2())

loop.close()


print("Completed async process")




# Huynia ebbanie, ne rabotaet
# Rewrite shikiClient with a simpler approach, but make it async whatever it takes!!!
# Probably queues need to be removed for now
# TODOs review constructor, re-think how requests are to be made, get rid of queues for now