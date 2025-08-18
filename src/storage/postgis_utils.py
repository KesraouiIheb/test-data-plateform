from dotenv import load_dotenv
import os

load_dotenv()  # loads variables from .env

user = os.getenv("PGSTAC_USER")
password = os.getenv("PGSTAC_PASSWORD")
host = os.getenv("PGSTAC_HOST")
port = os.getenv("PGSTAC_PORT")
db = os.getenv("PGSTAC_DB")

dsn = f"postgresql://{user}:{password}@{host}:{port}/{db}"

print(dsn)