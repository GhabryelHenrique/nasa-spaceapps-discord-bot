"""
Configuração de banco de dados simplificada
Importa funcionalidades do setup.py
"""

# Importar tudo do novo sistema simplificado
from database.setup import (
    db_setup,
    create_tables,
    DatabaseManager
)

# Manter compatibilidade com imports existentes
async_engine = db_setup.async_engine
sync_engine = db_setup.sync_engine
AsyncSessionLocal = db_setup.AsyncSessionLocal

# Função de sessão assíncrona (compatibilidade)
async def get_async_session():
    """Retorna uma sessão assíncrona do banco"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()