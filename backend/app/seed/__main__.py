import asyncio

from app.core.db import get_db
from app.seed import seed

if __name__ == "__main__":
    print(asyncio.run(seed(get_db())))
