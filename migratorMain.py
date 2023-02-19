import requests
import json
import logging
import asyncio
from dotenv import load_dotenv
from os import getenv
from datetime import datetime, timedelta
from pathlib import Path
from migrationToolbox.shikiClient import ShikimoriClient

# Logging config
logger = logging.getLogger("mainLogger")
logger.setLevel(logging.DEBUG)

# Read ENV variables
load_dotenv()
SHIKI_CLIENT_ID = getenv("SHIKI_CLIENT_ID")
SHIKI_CLIENT_SECRET = getenv("SHIKI_CLIENT_SECRET")
SHIKI_REDIRECT_URL = getenv("SHIKI_REDIRECT_URL")
SHIKI_AUTH_CODE = getenv("SHIKI_AUTH_CODE")

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

shikimori.authorize() #TODO move this to constructor?

r = shikimori.syncSesh.get("https://shikimori.one/api/users/whoami") # Test line to make sure we have access
print(r.text)



