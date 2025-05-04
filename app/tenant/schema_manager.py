from sqlalchemy import create_engine, text
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class SchemaManager:
    """Manage PostgreSQL schemas for tenant isolation"""
    
    @staticmethod
    def get_engine():
        """Get SQLAlchemy engine with admin privileges"""
        return create_engine(current_app.config['SQLALCHEMY_DATABASE_URI'])
    
    @staticmethod
    def create_schema(schema_name):
        """Create a new PostgreSQL schema"""
        engine = SchemaManager.get_engine()
        
        try:
            with engine.connect() as connection:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
                logger.info(f"Schema created: {schema_name}")
        except Exception as e:
            logger.error(f"Error creating schema {schema_name}: {str(e)}")
            raise
        finally:
            engine.dispose()
    
    @staticmethod
    def drop_schema(schema_name):
        """Drop a PostgreSQL schema and all its objects"""
        engine = SchemaManager.get_engine()
        
        try:
            with engine.connect() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
                logger.info(f"Schema dropped: {schema_name}")
        except Exception as e:
            logger.error(f"Error dropping schema {schema_name}: {str(e)}")
            raise
        finally:
            engine.dispose()
    
    @staticmethod
    def schema_exists(schema_name):
        """Check if a schema exists"""
        engine = SchemaManager.get_engine()
        
        try:
            with engine.connect() as connection:
                result = connection.execute(text(
                    "SELECT schema_name FROM information_schema.schemata "
                    f"WHERE schema_name = '{schema_name}'"
                ))
                return result.scalar() is not None
        except Exception as e:
            logger.error(f"Error checking schema {schema_name}: {str(e)}")
            raise
        finally:
            engine.dispose()
    
    @staticmethod
    def list_schemas():
        """List all tenant schemas"""
        engine = SchemaManager.get_engine()
        
        try:
            with engine.connect() as connection:
                result = connection.execute(text(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name LIKE 'tenant_%'"
                ))
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error listing schemas: {str(e)}")
            raise
        finally:
            engine.dispose()
    
    @staticmethod
    def create_tenant_tables(schema_name):
        """Create tables in the tenant schema"""
        engine = SchemaManager.get_engine()
        
        try:
            # Set search path to the tenant schema
            with engine.connect() as connection:
                connection.execute(text(f'SET search_path TO "{schema_name}"'))
                
                # Create tenant-specific tables
                # This is where you would create tables specific to each tenant
                # For example: connection.execute(text('CREATE TABLE "users" (...)'))
                
                logger.info(f"Created tables in schema: {schema_name}")
        except Exception as e:
            logger.error(f"Error creating tables in schema {schema_name}: {str(e)}")
            raise
        finally:
            engine.dispose()