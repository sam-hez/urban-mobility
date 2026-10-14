import os 
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME")

DEFAULT_PER_PAGE = 25     
MAX_PER_PAGE = 100        
MAX_PAGE = 10000          
MAX_TOP_LIMIT = 50        
QUERY_TIMEOUT_MS = 30000                                  