"""
Configuração e inicialização simplificada do banco de dados
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.models import Base
import config
import sys

class DatabaseSetup:
    def __init__(self):
        self.sync_engine = None
        self.async_engine = None
        self.AsyncSessionLocal = None
        self._setup_engines()

    def _get_database_urls(self):
        """Converte URLs entre formatos sync/async"""
        base_url = config.DATABASE_URL

        # Log da URL para debug
        print(f"DEBUG: Using database URL: {base_url}")
        
        # URL sync (para criação de tabelas)
        if base_url.startswith('postgresql+asyncpg://'):
            sync_url = base_url.replace('postgresql+asyncpg://', 'postgresql+psycopg2://')
        elif base_url.startswith('postgresql://'):
            sync_url = base_url.replace('postgresql://', 'postgresql+psycopg2://')
        else:
            sync_url = base_url

        # URL async (para operações do bot)
        if base_url.startswith('postgresql+psycopg2://'):
            async_url = base_url.replace('postgresql+psycopg2://', 'postgresql+asyncpg://')
        elif base_url.startswith('postgresql://'):
            async_url = base_url.replace('postgresql://', 'postgresql+asyncpg://')
        else:
            async_url = base_url

        return sync_url, async_url

    def _setup_engines(self):
        """Configura engines sync e async"""
        sync_url, async_url = self._get_database_urls()
        
        self.sync_engine = create_engine(sync_url, echo=False)
        self.async_engine = create_async_engine(async_url, echo=False)
        self.AsyncSessionLocal = sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

    def test_connection(self):
        """Testa conexão com o banco de dados"""
        try:
            print(f"Testing connection with engine: {self.sync_engine.url}")
            with self.sync_engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                return result.fetchone() is not None
        except Exception as e:
            print(f"Erro na conexao: {e}")
            return False

    def create_enums(self):
        """Cria todos os ENUMs necessários"""
        enums_sql = [
            {
                'name': 'escolaridadeenum',
                'values': [
                    'Fundamental I', 'Fundamental II', 'Ensino Médio',
                    'Graduando', 'Ensino Superior', 'Ensino Superior Completo',
                    'Mestrando', 'Mestrado Completo', 'Doutorando',
                    'Doutorado Completo', 'PHD ou +'
                ]
            },
            {
                'name': 'modalidadeenum',
                'values': [
                    'Presencialmente em Uberlândia',
                    'Remotamente de qualquer lugar do mundo'
                ]
            },
            {
                'name': 'statusaplicacaoenum',
                'values': ['Pendente', 'Aprovada', 'Rejeitada', 'Cancelada']
            }
        ]

        for enum_def in enums_sql:
            try:
                with self.sync_engine.connect() as connection:
                    values_str = "', '".join(enum_def['values'])
                    sql = f"CREATE TYPE {enum_def['name']} AS ENUM ('{values_str}')"
                    connection.execute(text(sql))
                    connection.commit()
                    print(f"Enum {enum_def['name']} criado")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"Enum {enum_def['name']} ja existe")
                else:
                    print(f"Erro ao criar {enum_def['name']}: {e}")

    def create_tables(self):
        """Cria todas as tabelas"""
        try:
            Base.metadata.create_all(bind=self.sync_engine)
            print("Tabelas criadas/atualizadas com sucesso")
            return True
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
            return False

    def initialize_database(self):
        """Inicialização completa do banco"""
        print("Inicializando banco de dados de mentoria...")
        
        # Testar conexão
        if not self.test_connection():
            print("Falha na conexao com o banco de dados")
            return False

        # Criar ENUMs
        print("Criando tipos ENUM...")
        self.create_enums()

        # Criar tabelas
        print("Criando tabelas...")
        if not self.create_tables():
            return False

        print("Banco de dados inicializado com sucesso!")
        return True

    async def get_session(self):
        """Retorna nova sessão assíncrona"""
        return self.AsyncSessionLocal()

    async def close(self):
        """Fecha conexões"""
        if self.async_engine:
            await self.async_engine.dispose()

# Instância global
db_setup = DatabaseSetup()

# Funções compatíveis com código existente
def create_tables():
    """Função compatível - cria tabelas"""
    return db_setup.initialize_database()

class DatabaseManager:
    @staticmethod
    async def get_session():
        """Compatibilidade com código existente"""
        return db_setup.AsyncSessionLocal()
    
    @staticmethod
    async def close_engine():
        """Compatibilidade com código existente"""
        await db_setup.close()