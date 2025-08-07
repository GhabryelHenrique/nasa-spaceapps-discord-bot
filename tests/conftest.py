"""
Configurações compartilhadas para testes
"""

import pytest
import asyncio
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.models import Base
from database.setup import DatabaseSetup

# Configurar banco de teste
TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'sqlite+aiosqlite:///test_nasa_spaceapps.db')

@pytest.fixture(scope="session")
def event_loop():
    """Cria um loop de eventos para toda a sessão de testes"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db_setup():
    """Configura banco de dados de teste"""
    # Para SQLite em memória, não precisamos criar ENUMs
    if 'sqlite' in TEST_DATABASE_URL:
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield engine, AsyncSessionLocal
        
        await engine.dispose()
    else:
        # Para PostgreSQL de teste
        db_setup = DatabaseSetup()
        db_setup._setup_engines()
        
        # Criar tabelas de teste
        if db_setup.test_connection():
            db_setup.create_enums()
            db_setup.create_tables()
        
        yield db_setup.async_engine, db_setup.AsyncSessionLocal
        
        await db_setup.close()

@pytest.fixture
async def db_session(test_db_setup):
    """Cria uma sessão de banco de dados para cada teste"""
    engine, AsyncSessionLocal = test_db_setup
    
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
def sample_participant_data():
    """Dados de exemplo para um participante"""
    return {
        'discord_user_id': 123456789,
        'discord_username': 'testuser#1234',
        'nome': 'João',
        'sobrenome': 'Silva',
        'email': 'joao@example.com',
        'telefone': '34999887766',
        'cpf': '12345678901',
        'cidade': 'Uberlândia',
        'data_nascimento': '15/08/1995',
        'nome_equipe': 'Equipe Teste',
        'membros_convidados': '',
        'disponivel_para_equipe': False,
        'descricao_habilidades': None
    }

@pytest.fixture
def sample_team_application_data():
    """Dados de exemplo para uma aplicação de equipe"""
    return {
        'equipe_nome': 'Equipe Destino',
        'mensagem_aplicacao': 'Gostaria de me juntar à equipe porque tenho experiência em Python.',
    }