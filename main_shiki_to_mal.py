import logging
import asyncio
from lib_utilities import ShikimoriClient
from lib_utilities import (
    SHIKI_CLIENT_ID,
    SHIKI_CLIENT_SECRET,
    SHIKI_REDIRECT_URL,
    SHIKI_AUTH_CODE
)
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) # Make this optional for windows!
# Logging config
logger = logging.getLogger("mainLogger")
logger.setLevel(logging.DEBUG)

# Configs - move to yaml
SHIKI_SCOPES = "user_rates+comments+topics"
SHIKI_OAUTH_CACHE = "Cache/shiki_token.json"
SHIKI_APP = "MAL_migrator"
# https://pypi.org/project/asyncio-atexit/ to register session closure

shikimori = ShikimoriClient(client_id = SHIKI_CLIENT_ID,
                            client_secret = SHIKI_CLIENT_SECRET,
                            redirect_url = SHIKI_REDIRECT_URL,
                            auth_code = SHIKI_AUTH_CODE,
                            app_name = SHIKI_APP,
                            token_path = SHIKI_OAUTH_CACHE,
                            buffer = 99999)

GET_URLS = ["https://shikimori.one/api/users/whoami"]

URL = "https://shikimori.one/api/users/whoami"

loop = asyncio.new_event_loop()

shikimori.authorize(loop = loop)





print("Completed async process")




# Huynia ebbanie, ne rabotaet
# Rewrite shikiClient with a simpler approach, but make it async whatever it takes!!!
# Probably queues need to be removed for now
# TODOs review constructor, re-think how requests are to be made, get rid of queues for now