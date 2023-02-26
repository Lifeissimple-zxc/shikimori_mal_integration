
import requests
import json
import logging
from asyncio.events import AbstractEventLoop
from asyncio import Queue
from aiohttp import ClientSession, ClientRequest
from requests.sessions import Session
from dotenv import load_dotenv
from os import getenv
from datetime import datetime, timedelta
from pathlib import Path
from time import time
from atexit import register
from types import CoroutineType

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
        self.syncSesh.headers.update({"User-Agent": appName}) # move to a dict because we don't persist session in Async approach
        # Request headers that we persist when making requests
        self.headers = {"User-Agent": appName}
        # Store queues for handling requests within self
        self.mainQueue = Queue() # TODO Tbd if size needs to be specified
        self.retryQueue = Queue()
        self.authQueue = Queue() # TODO Set to 1?
        # Check if we have local token, if it is still valid --> use it
        self.tokenPath = Path(tokenPath)
        self.buffer = buffer
        register(self.syncSesh.close)
        self._readTokenCache()
            
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
    
    def _getTokenRequestParams(self, mode: str = None) -> tuple:
        """
        Prepares parameters dict for token (auth) request
        """
        # Set mode to default parameter
        if mode is None:
            mode = "new"
        elif mode not in ("new", "refresh"):
            return None, AttributeError(f"Wrong mode of getting token")
        # Prepare params dict
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
        return params, None
    
    def _requestTokenSync(self, mode = "new") -> tuple:
        """
        Method that gets new token from Shikimori API
        """
        # Base request params - move this to a function
        params, e = self._getTokenRequestParams(mode = mode)
        if e is not None:
            print(f"Error getting auth request params: {e}")
        # Actually request our token
        logger.debug("Requesting a new token")
        resp = self.syncSesh.post(url = TOKEN_URL, data = params)
        # Handle failed request
        if resp.status_code != 200:
            return None, Exception("Requesting token failed")
        # Convert response to json and return
        try:
            return resp.json(), None 
        except Exception as e:
            return None, e

    def _cacheToken(self, token: dict):
        """
        Caches token to a local .json file
        """
        with open(self.tokenPath, "w") as _tPath:
            json.dump(token, _tPath, indent = 4)
    
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
                token, e = self._requestTokenSync("refresh")
                if e is not None:
                    raise e
                self.token = token
            case 2:
                token, e = self._requestTokenSync()
                if e is not None:
                    raise e
                self.token = token    
        # Cache token if requested it above
        self._cacheToken()
        # Add Bearer to self for convenience
        self.syncSesh.headers.update({"Authorization": f"Bearer {self.token['access_token']}"})
    
    # Functions for performing async requests
    @staticmethod
    async def _enqueueRequest(requestCoro: CoroutineType, queue: Queue):
        """
        Puts request coroutine to a queue
        """
        await queue.put(requestCoro)
        # TODO Exceptions

    async def _getRequestCoro(self,
                              url: str,
                              sesh: ClientSession,
                              headers: dict = None,
                              params: dict = None):
        """
        Coroutine for GET requests to shikimori APIs
        """
        async with sesh.get(url = url, headers = headers, params = params) as resp:
            # We put this very request to retry queue if we get a bad response (not 200)
            if (status := resp.status) != 200:
                self._enqueueRequest(queue = self.retryQueue,
                                     requestCoro = self._getRequestCoro(url = url,
                                                                        sesh = sesh,
                                                                        headers = headers,
                                                                        params = params))
            # Check for 401 error because it means we need to put auth request to queue
                if status == EXPIRATION_WARNING["code"]:
                    self._enqueueRequest(queue = self.authQueue,
                                         requestCoro = self._postRequestCoro(url = url,
                                                                             sesh = sesh,
                                                                             isAuth = True,
                                                                             headers = headers,
                                                                             data = params))
            # In a normal scenario, just await on the response
            print(resp.status)
            data = await resp.text()
            print(data)
            return data
    
    async def _postRequestCoro(self,
                               url: str,
                               sesh: ClientSession,
                               isAuth: bool,
                               headers: dict = None,
                               data: dict = None):
        """
        Coroutine for POST requests to shikimori API
        """
        # Path for auth request
        if isAuth:
            print("Requesting token")
            # Prepare request params
            params, e = self._getTokenRequestParams(mode = "refresh")
            if e is not None:
                print(f"Error getting auth request params: {e}")
            # Prepare header
            refreshHeader = {"User-Agent": self.headers["User-Agent"]}
            async with sesh.post(url = TOKEN_URL, data = params, headers = refreshHeader) as resp:
                data = await resp.text()
                print(resp.status)
                print(data)
                # Cache token
                self._cacheToken(token = data)
                # Update headers for making requests
                self.headers["Authorization"] = f"Bearer {self.token['access_token']}"
                print("Updated access token")
        
        # Other POST requests
        else:    
            async with sesh.post(url = url, data = data, headers = headers) as resp:
                # We put this very request to retry queue if we get a bad response (not 200)
                if (status := resp.status) != 200:
                    self._enqueueRequest(queue = self.retryQueue,
                                        requestCoro = self._postRequestCoro(url = url,
                                                                            sesh = sesh,
                                                                            isAuth = isAuth,
                                                                            headers = headers,
                                                                            data = data))
                # Check for 401 error because it means we need to put auth request to queue
                    if status == EXPIRATION_WARNING["code"]:
                        self._enqueueRequest(
                            queue = self.authQueue,
                            requestCoro = self._postRequestCoro(url = url,
                                                                sesh = sesh,
                                                                isAuth = True,
                                                                headers = headers,
                                                                data = data)
                        ) 
                # In a normal scenario, just await on the response
                data = await resp.text()
                print(resp.status)
                print(data)
                
                return data

    async def processTasks(self, loop: AbstractEventLoop):
        """
        Consumer function to process coroutines attached to the Client's queue
        """
        while True:
            # If we have no tasks in main and retry - return from the function
            if self.mainQueue.empty():
                print("Main queue is empty")
                # Check retry queue as well
                if self.retryQueue.empty():
                    print("Retry queue is empty")
                    return

            # Check if we have any unprocessed auth requests
            if not self.authQueue.empty(): # While is not needed because tasks on the Queue should not > 1
                task = await self.authQueue.get()
                loop.create_task(task)
                # Run loop to complete auth tasks with higher priority than the rest
                loop.run_until_complete()
    
            # Process tasks from the main queue #TODO abstract this???
            task = await self.mainQueue.get()
            loop.create_task(task)
            # Process retry tasks too
            task = await self.retryQueue.get()
            loop.create_task(task)

            loop.run_until_complete() # TBD IF Run forever should be used instead?

    
    
    
        

        
        

    
# Refactor the class a bit, constructor is too much right now
# Check 
# Move session to async
# ClienRequest object in aiohttp????
# Base url for session?
# sync for auth, async for rest of the script?
# https://docs.aiohttp.org/en/stable/http_request_lifecycle.html