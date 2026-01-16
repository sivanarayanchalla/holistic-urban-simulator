import sys
sys.path.append('src')
from database.db_config import db_config
from sqlalchemy import inspect

engine = db_config.engine
inspector = inspect(engine)

table_name = 'ev_infrastructure'
columns = inspector.get_columns(table_name)
print(f'Columns in {table_name}:')
for col in columns:
    print(f'  {col["name"]}: {col["type"]}')
