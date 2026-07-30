import time
from limits.storage import Storage
from sqlalchemy import create_engine, Column, String, Integer, Float, MetaData, Table, inspect
from sqlalchemy.orm import sessionmaker, scoped_session

class SQLAlchemyStorage(Storage):
    """
    A simple SQLAlchemy backend for Flask-Limiter (limits package).
    Registered under 'sqlalchemy://', 'mysql://', 'postgresql://', 'sqlite://'.
    Supports fixed-window rate limiting.
    """
    
    STORAGE_SCHEME = ["sqlalchemy", "mysql", "mysql+pymysql", "postgresql", "sqlite"]
    
    def __init__(self, uri: str, **kwargs):
        super().__init__(uri, **kwargs)
        self.engine = create_engine(uri, pool_pre_ping=True) if not uri.startswith('sqlite') else create_engine(uri)
        self.metadata = MetaData()
        self.table = Table(
            'rate_limits', self.metadata,
            Column('key', String(255), primary_key=True),
            Column('value', Integer, default=0),
            Column('expiry', Float, nullable=False)
        )
        # Create table if it doesn't exist
        insp = inspect(self.engine)
        if not insp.has_table('rate_limits'):
            self.metadata.create_all(self.engine)
            
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
    @property
    def base_exceptions(self):
        import sqlalchemy.exc
        return (sqlalchemy.exc.SQLAlchemyError,)

    def _cleanup_expired(self, session):
        # Optional: periodically clean up expired keys
        pass

    def get(self, key: str) -> int:
        session = self.Session()
        try:
            row = session.execute(self.table.select().where(self.table.c.key == key)).first()
            if row:
                if row.expiry <= time.time():
                    session.execute(self.table.delete().where(self.table.c.key == key))
                    session.commit()
                    return 0
                return row.value
            return 0
        finally:
            self.Session.remove()

    def get_expiry(self, key: str) -> float:
        session = self.Session()
        try:
            row = session.execute(self.table.select().where(self.table.c.key == key)).first()
            if row:
                return row.expiry
            return time.time()
        finally:
            self.Session.remove()

    def incr(self, key: str, expiry: float, elastic_expiry: bool = False, amount: int = 1) -> int:
        session = self.Session()
        try:
            now = time.time()
            row = session.execute(self.table.select().where(self.table.c.key == key)).first()
            
            if row:
                if row.expiry <= now:
                    # Expired, reset
                    new_val = amount
                    new_exp = now + expiry
                    session.execute(self.table.update().where(self.table.c.key == key).values(value=new_val, expiry=new_exp))
                else:
                    # Increment
                    new_val = row.value + amount
                    new_exp = (now + expiry) if elastic_expiry else row.expiry
                    session.execute(self.table.update().where(self.table.c.key == key).values(value=new_val, expiry=new_exp))
            else:
                new_val = amount
                new_exp = now + expiry
                session.execute(self.table.insert().values(key=key, value=new_val, expiry=new_exp))
                
            session.commit()
            return new_val
        except Exception:
            session.rollback()
            return 0
        finally:
            self.Session.remove()

    def decr(self, key: str, amount: int = 1) -> int:
        session = self.Session()
        try:
            row = session.execute(self.table.select().where(self.table.c.key == key)).first()
            if row and row.expiry > time.time():
                new_val = max(row.value - amount, 0)
                session.execute(self.table.update().where(self.table.c.key == key).values(value=new_val))
                session.commit()
                return new_val
            return 0
        except Exception:
            session.rollback()
            return 0
        finally:
            self.Session.remove()

    def clear(self, key: str) -> None:
        session = self.Session()
        try:
            session.execute(self.table.delete().where(self.table.c.key == key))
            session.commit()
        except Exception:
            session.rollback()
        finally:
            self.Session.remove()

    def check(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(self.table.select().limit(1))
            return True
        except Exception:
            return False

    def reset(self):
        session = self.Session()
        try:
            session.execute(self.table.delete())
            session.commit()
            return 1
        except Exception:
            session.rollback()
            return 0
        finally:
            self.Session.remove()
