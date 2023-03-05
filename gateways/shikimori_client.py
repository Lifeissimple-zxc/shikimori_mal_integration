import json
from time import time
from pathlib import Path
import logging
from asyncio.events import AbstractEventLoop
from aiohttp import ClientSession



logger = logging.getLogger("mainLogger")

EXPIRATION_WARNING = {
    "code": 401,
    "error": "The access token is invalid"
} # Move to YAML?

TOKEN_URL = "https://shikimori.one/oauth/token"

class ShikimoriClient:
    """
    Class used to interact with Shikimori API
    """
    def __init__(self,
                 client_id: str,
                 client_secret: str,
                 redirect_url: str,
                 auth_code: str,
                 app_name: str,
                 token_path: str,
                 buffer = 15,
                 result_limit = 5000):
        """
        Constructor of the class, TODO
        """
        # Store params for requests within self
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_url = redirect_url
        self.auth_code = auth_code
        # Request headers that we persist when making requests
        self.headers = {"User-Agent": app_name}
        # Check if we have local token, if it is still valid --> use it
        self.token_path_obj = Path(token_path)
        self.buffer = buffer


    # functions needed for the constructor to work
    def _read_token_cache(self) -> int:
        """
        Method reads and validates cached json with a Shikimori API token
        :return int: Flag that outcome of cache reading token. 0 - ok, 1 - file found but expired, 2 - no file found
        """
        # Check if we have local token
        if self.token_path_obj.is_file():
            with open(self.token_path_obj, "r") as _f:
                # Store within self if yes
                token = json.load(_f)
            # Check that our token is still valid
            token_expiry = token["created_at"] + token["expires_in"]
            self.token = token # Assinging to self here for _get_token_request_params to access it
            if (token_expiry - int(time())) / 60 > self.buffer:
                self.headers["Authorization"] = f"Bearer {self.token['access_token']}"
                print("Found valid token in local cache, assigned to self")
                return 0
            else:
                print("Found token in local cache, but it is expired.")
                return 1
        else:
            print("No token located in cache.")
            return 2
    

    def _get_token_request_params(self, mode: str = None) -> tuple:
        """
        Prepares parameters dict for token (auth) request
        """
        # Set mode to default parameter
        if mode is None:
            mode = "new"
        elif mode not in ("new", "refresh"):
            return None, AttributeError("Wrong mode of getting token")
        # Prepare params dict
        params = {"client_id": self.client_id, "client_secret": self.client_secret}
        if mode == "new":
            # Update params to get new token
            params["grant_type"] = "authorization_code"
            params["code"] = self.auth_code
            params["redirect_uri"] = self.redirect_url
        elif mode == "refresh":
            # Extra params for refreshing token
            params["grant_type"] = "refresh_token"
            params["refresh_token"] = self.token["refresh_token"]
        return params, None
    

    def _cache_token(self, token: dict):
        """
        Caches token to a local .json file
        """
        with open(self.token_path_obj, "w") as _tPath:
            json.dump(token, _tPath, indent = 4)


    def authorize(self, loop: AbstractEventLoop):
        """
        Higher level method for getting oauth token to interact with the API
        """
        # First, we try to read token from local cache
        res = self._read_token_cache()
        if res == 0:
            return
        else: # refactor this???
            if res == 1: # Token refresh path 
                fut = loop.create_task(self._get_token_coro(mode = "refresh"))        
            else: # New token path
                fut = loop.create_task(self._get_token_coro(mode = "new"))
            # This runs our _get_token_coro and caches token locally
            fut_result = loop.run_until_complete(fut)
            print(f"Future result is: {fut_result}")
            result = self._read_token_cache()
            if result != 0:
                print("Something went wrong when requesting token, check logs")


    # Functions for performing async requests
    async def _get_token_coro(self, mode = None):
        """
        Coroutine for making an async auth request
        :param TODO:
        """
        if mode is None:
            mode = "new"
        params, e = self._get_token_request_params(mode = mode)
        if e is not None:
            print(f"Error getting Shiki token: {e}")
        # Actually prepare task for token request
        print(f"Requesting token ({mode})...")
        # TODO add retries here? Make post coro / get coro with retry decorator???
        async with ClientSession(headers = self.headers) as session:
            async with session.post(TOKEN_URL, data = params) as response:
                if response.status != 200:
                    return Exception("Requesting token failed")
                try:
                    token = await response.json()
                    self._cache_token(token)
                    return None
                except Exception as e:
                    print(f"Uncaught exception when requesting token: {e}")
                    return e
    
 
# Base url for session?
# ClientSession requires to be created in the same coro from which we are to be making requests!!!