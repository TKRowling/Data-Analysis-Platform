from urllib.parse import quote_plus
from sqlalchemy import Engine, create_engine
from app.schemas.datasource import DatabaseConnection

def build_engine(config: DatabaseConnection) -> Engine:
    driver="postgresql+psycopg" if config.database_type=="postgresql" else "mysql+pymysql"
    url=f"{driver}://{quote_plus(config.username)}:{quote_plus(config.password)}@{config.host}:{config.port}/{config.database}"
    return create_engine(url,pool_pre_ping=True)

