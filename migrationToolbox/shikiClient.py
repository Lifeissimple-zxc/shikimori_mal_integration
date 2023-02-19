
import requests
import json
import logging
from asyncio.events import AbstractEventLoop
from aiohttp import ClientSession, ClientRequest
from requests.sessions import Session
from dotenv import load_dotenv
from os import getenv
from datetime import datetime, timedelta
from pathlib import Path
from time import time
from atexit import register

logger = logging.getLogger("mainLogger")

class ShikimoriClient:
    """
    Class used to interact with Shikimori API
    """
    def __init__(self,
                 clientId: str,
                 clientSecret: str,
                 redirectUrl: str,
                 authCode: str,
                 appName: str,
                 tokenPath: str,
                 buffer = 15,
                 resultLimit = 5000):
        """
        Constructor of the class, TODO
        """
        # Store params for requests within self
        self.clientId = clientId
        self.clientSecret = clientSecret
        self.redirectUrl = redirectUrl
        self.authCode = authCode
        # Create session for persisting headers #TODO make it async
        self.syncSesh = Session()
        self.syncSesh.headers.update({"User-Agent": appName})
        # Check if we have local token, if it is still valid --> use it
        self.tokenPath = Path(tokenPath)
        self.buffer = buffer
        register(self.syncSesh.close)
            
    # functions needed for the constructor to work
    def _readTokenCache(self) -> int:
        """
        Method reads and validates cached json with a Shikimori API token
        :return int: Flag that outcome of cache reading token. 0 - ok, 1 - file found but expired, 2 - no file found
        """
        # Check if we have local token
        if self.tokenPath.is_file():
            with open(self.tokenPath, "r") as _tokenJson:
                # Store within self if yes
                token = json.load(_tokenJson)
            # Check that our token is still valid
            tokenExpiry = token["created_at"] + token["expires_in"]
            self.token = token
            if (tokenExpiry - int(time())) / 60 > self.buffer:
                logger.debug("Found valid token in local cache")
                return 0
            else:
                print("Found token in local cache, but it is expired.")
                return 1
        else:
            print("No token located in cache.")
            return 2
    
    def _requestToken(self, mode = "new") -> tuple: # This should be _requestToken, make getToken a higher-level method to get access to the API
        """
        Method that gets new token from Shikimori API
        """
        # Base request params - move this to a function
        params = {"client_id": self.clientId, "client_secret": self.clientSecret}
        if mode == "new":
            # Update params to get new token
            params["grant_type"] = "authorization_code"
            params["code"] = self.authCode
            params["redirect_uri"] = self.redirectUrl
        elif mode == "refresh":
            # Extra params for refreshing token
            params["grant_type"] = "refresh_token"
            params["refresh_token"] = self.token["refresh_token"]
        else:
            return None, AttributeError(f"Wrong mode of getting token")
        # Actually request our token
        logger.debug("Requesting a new token")
        resp = self.syncSesh.post(url = "https://shikimori.one/oauth/token", data = params)
        # Handle failed request
        if resp.status_code != 200:
            return None, Exception("Requesting token failed")
        # Convert response to json and return
        try:
            return resp.json(), None 
        except Exception as e:
            return None, e

    def _cacheToken(self):
        """
        Caches token to a local .json file
        """
        with open(self.tokenPath, "w") as _tPath:
            json.dump(self.token, _tPath, indent = 4)
    
    def authorize(self):
        """
        Higher level method for getting oauth token to interact with the API
        """
        # First, we try to read token from local cache
        match self._readTokenCache():
            case 0:
                self.syncSesh.headers.update({"Authorization": f"Bearer {self.token['access_token']}"})
                return # Don't need to do anything if 0
            case 1:
                token, e = self._requestToken("refresh")
                if e is not None:
                    raise e
                self.token = token
            case 2:
                token, e = self._requestToken()
                if e is not None:
                    raise e
                self.token = token    
        # Cache token if requested it above
        self._cacheToken()
        # Add Bearer to self for convenience
        self.syncSesh.headers.update({"Authorization": f"Bearer {self.token['access_token']}"})
        

        
        

    
# Refactor the class a bit, constructor is too much right now
# Check 
# Move session to async
# ClienRequest object in aiohttp????
# Base url for session?
# sync for auth, async for rest of the script?
# https://docs.aiohttp.org/en/stable/http_request_lifecycle.html