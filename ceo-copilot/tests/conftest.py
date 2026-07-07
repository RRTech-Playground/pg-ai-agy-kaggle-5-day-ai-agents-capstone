import os
from dotenv import load_dotenv

# Load .env file at the very start of the test session
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)
