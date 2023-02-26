from dotenv import load_dotenv, dotenv_values
from os import getenv
# Read ENV variablesk TODO Move to a dict for simpler import statements in main: dotenv_values in dotenv lib?
load_dotenv()
SECRETS = dotenv_values() # This unites all the stuff below where we read from env variables
SHIKI_CLIENT_ID = getenv("SHIKI_CLIENT_ID")
SHIKI_CLIENT_SECRET = getenv("SHIKI_CLIENT_SECRET")
SHIKI_REDIRECT_URL = getenv("SHIKI_REDIRECT_URL")
SHIKI_AUTH_CODE = getenv("SHIKI_AUTH_CODE")

from migrationToolbox.shikiClient import ShikimoriClient