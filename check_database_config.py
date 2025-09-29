#!/usr/bin/env python3
"""
Script para verificar e diagnosticar a configuração do banco de dados
"""

import os
import sys
from dotenv import load_dotenv
import socket

def check_database_config():
    """Verifica a configuração do banco de dados"""

    # Carregar variáveis de ambiente
    load_dotenv()

    print("=== Verificação da Configuração do Banco de Dados ===\n")

    # Verificar variável de ambiente
    database_url = os.getenv('DATABASE_URL')
    print(f"DATABASE_URL: {database_url}")

    if not database_url:
        print("❌ DATABASE_URL não encontrada nas variáveis de ambiente!")
        print("Certifique-se de que o arquivo .env contém:")
        print("DATABASE_URL=postgresql://nasa_bot_user:1029384756Gh!@localhost:5432/nasa_bot")
        return False

    # Extrair componentes da URL
    if '://' in database_url:
        protocol, rest = database_url.split('://', 1)
        if '@' in rest:
            credentials, host_db = rest.split('@', 1)
            if '/' in host_db:
                host_port, db_name = host_db.split('/', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                else:
                    host, port = host_port, '5432'
            else:
                host, port, db_name = host_db, '5432', ''
        else:
            print("❌ URL do banco malformada - credenciais não encontradas")
            return False
    else:
        print("❌ URL do banco malformada - protocolo não encontrado")
        return False

    print(f"Host: {host}")
    print(f"Porta: {port}")
    print(f"Banco: {db_name}")

    # Testar resolução DNS
    print(f"\n=== Testando resolução DNS para {host} ===")
    try:
        ip = socket.gethostbyname(host)
        print(f"✅ {host} resolve para {ip}")
    except socket.gaierror as e:
        print(f"❌ Erro de resolução DNS para {host}: {e}")
        print("\nSugestões:")
        print("1. Se usando localhost, certifique-se de que o PostgreSQL está rodando localmente")
        print("2. Se usando um servidor remoto, verifique se o hostname está correto")
        print("3. Tente usar o IP diretamente: DATABASE_URL=postgresql://nasa_bot_user:1029384756Gh!@127.0.0.1:5432/nasa_bot")
        return False

    # Testar conectividade de rede
    print(f"\n=== Testando conectividade para {host}:{port} ===")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, int(port)))
        sock.close()

        if result == 0:
            print(f"✅ Porta {port} acessível em {host}")
        else:
            print(f"❌ Não foi possível conectar na porta {port} de {host}")
            print("Verifique se o PostgreSQL está rodando e aceita conexões na porta especificada")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar conectividade: {e}")
        return False

    print("\n=== Teste de Conexão com o Banco ===")
    try:
        from database.setup import db_setup

        if db_setup.test_connection():
            print("✅ Conexão com o banco de dados bem-sucedida!")
            return True
        else:
            print("❌ Falha na conexão com o banco de dados")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar conexão com o banco: {e}")
        return False

if __name__ == "__main__":
    success = check_database_config()
    sys.exit(0 if success else 1)