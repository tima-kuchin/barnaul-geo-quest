import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import entities
from controllers import run_controllers

if __name__ == "__main__":
    import uvicorn

    load_dotenv('/etc/secrets/.env')

    database_url = os.getenv("DATABASE_URL")
    secret_key = os.getenv("SECRET_KEY")
    access_token_expire_minutes = 30

    engine = create_engine(database_url)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    entities.create_all(engine)

    app = run_controllers(access_token_expire_minutes, secret_key, session_local)

    uvicorn.run(app, host="127.0.0.1", port=8000)
