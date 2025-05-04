from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app import db

class Database:
    """Database utility class for managing database connections"""
    
    @staticmethod
    def get_engine(app=None, database_url=None):
        """Get SQLAlchemy engine"""
        if app:
            return db.get_engine(app)
        else:
            return create_engine(database_url)
    
    @staticmethod
    @contextmanager
    def get_session(app=None, database_url=None):
        """Context manager for database sessions"""
        if app:
            # Use Flask-SQLAlchemy session
            try:
                yield db.session
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
        else:
            # Create standalone session
            engine = Database.get_engine(database_url=database_url)
            session_factory = sessionmaker(bind=engine)
            session = scoped_session(session_factory)
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    @staticmethod
    def create_schema(engine, schema_name):
        """Create PostgreSQL schema if it doesn't exist"""
        engine.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
    
    @staticmethod
    def drop_schema(engine, schema_name):
        """Drop PostgreSQL schema"""
        engine.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
    
    @staticmethod
    def list_schemas(engine):
        """List all schemas in the database"""
        result = engine.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema'"
        )
        return [row[0] for row in result]

# Base model class
class BaseModel(db.Model):
    """Abstract base model with common fields"""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime, 
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )