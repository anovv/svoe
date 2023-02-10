from sqlalchemy import create_engine, Column, String, JSON, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

import os

Base = declarative_base()
Session = sessionmaker()


class MysqlClient:
    def __init__(self, config):
        self.config = config
        self.engine = self._init_engine()

    def _init_engine(self):
        # TODO figure out users/priviliges
        user = os.getenv('MYSQL_USER')
        password = os.getenv('MYSQL_PASSWORD')
        host = os.getenv('MYSQL_HOST')
        port = os.getenv('MYSQL_PORT')
        db = os.getenv('MYSQL_DATABASE')
        url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'
        engine = create_engine(url, echo=True)
        Session.configure(bind=engine)
        return engine

    def create_tables(self):
        # creates if not exists
        Base.metadata.create_all(self.engine)
