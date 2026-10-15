from datetime import date, datetime
from decimal import Decimal
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event, text

import config

_engine = None   
_cache = {}      


def get_engine():
    global _engine 
    if _engine is None:
        password = quote_plus(config.DB_PASSWORD)
        url = (f"mysql+pymysql://{config.DB_USER}:{password}"
                f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
        _engine = create_engine(
            url,
            pool_pre_ping=True,   
        )
        @event.listens_for(_engine, "connect")
        def set_query_timeout(connection, _):
            if "MariaDB" in connection.get_server_info():
                setting = f"max_statement_time={config.QUERY_TIMEOUT_MS / 1000}"
            else:
                setting = f"max_execution_time={config.QUERY_TIMEOUT_MS}"
            with connection.cursor() as cursor:
                cursor.execute(f"SET SESSION {setting}")
    return _engine

def _clean(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return value

def query_all(sql, params=None, use_cache=False):

    params = params or {}
    key = (sql, tuple(sorted(params.items())))
    if use_cache and key in _cache:
        return _cache[key]

    with get_engine().connect() as connection:
        result = connection.execute(text(sql), params)
        rows = [{name: _clean(value) for name, value in row._mapping.items()} for row in result]

    if use_cache:
        if len(_cache) > 500:   
            _cache.clear()
        _cache[key] = rows    
    return rows