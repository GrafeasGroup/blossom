import os

import dotenv
from blossom_wrapper import BlossomAPI
from praw import Reddit

dotenv.load_dotenv()

blossom = BlossomAPI(
    email=os.environ.get("BLOSSOM_EMAIL"),
    password=os.environ.get("BLOSSOM_PASSWORD"),
    api_key=os.environ.get("BLOSSOM_API_KEY"),
    api_base_url="https://grafeas.org/api/",
)
REDDIT = Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_SECRET"),
    password=os.getenv("REDDIT_PASSWORD"),
    username=os.getenv("REDDIT_USERNAME"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)
