#!/usr/bin/env python3
"""
Script de configuração inicial para o NASA Space Apps Bot
Configura banco de dados, verifica dependências e executa testes básicos
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 ou superior é necessário!")
        print(f"   Versão atual: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} detectado")
    return True

def check_env_file():
    """Verifica se o arquivo .env existe"""
    if not Path('.env').exists():
        if Path('.env.example').exists():
            print("⚠️  Arquivo .env não encontrado!")
            print("   Copie .env.example para .env e configure suas variáveis:")
            print("   cp .env.example .env")
            return False
        else:
            print("❌ Arquivos .env e .env.example não encontrados!")
            return False
    print("✅ Arquivo .env encontrado")
    return True

def install_dependencies():
    """Instala dependências do requirements.txt"""
    if not Path('requirements.txt').exists():
        print("❌ Arquivo requirements.txt não encontrado!")
        return False
    
    print("📦 Instalando dependências...")
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], capture_output=True, text=True, check=True)
        print("✅ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        print("   Saída do erro:", e.stderr)
        return False

def setup_database():
    """Configura o banco de dados"""
    print("\n🗄️ Configurando banco de dados...")
    
    try:
        # Importar após instalar dependências
        from database.setup import db_setup
        
        # Inicializar banco
        if db_setup.initialize_database():
            print("✅ Banco de dados configurado com sucesso!")
            return True
        else:
            print("❌ Falha na configuração do banco de dados")
            return False
            
    except ImportError as e:
        print(f"❌ Erro ao importar módulos do banco: {e}")
        print("   Verifique se as dependências foram instaladas corretamente")
        return False
    except Exception as e:
        print(f"❌ Erro na configuração do banco: {e}")
        return False

def run_tests():
    """Executa testes básicos do sistema"""
    print("\n🧪 Executando testes básicos...")
    
    try:
        # Importar módulos principais
        import config
        from database.setup import db_setup
        from database.models import Participante, AplicacaoEquipe
        
        # Testar configuração
        if not config.DISCORD_TOKEN:
            print("⚠️  DISCORD_TOKEN não configurado no .env")
            return False
            
        # Testar conexão com banco
        if not db_setup.test_connection():
            print("❌ Falha no teste de conexão com banco de dados")
            return False
            
        print("✅ Todos os testes básicos passaram!")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos testes: {e}")
        return False

def main():
    """Função principal de configuração"""
    print("=" * 60)
    print("🚀 CONFIGURAÇÃO INICIAL - NASA SPACE APPS BOT")
    print("=" * 60)
    
    # Verificações básicas
    if not check_python_version():
        sys.exit(1)
    
    if not check_env_file():
        sys.exit(1)
    
    # Instalar dependências
    if not install_dependencies():
        print("\n❌ Falha na instalação de dependências")
        sys.exit(1)
    
    # Configurar banco
    if not setup_database():
        print("\n❌ Falha na configuração do banco de dados")
        print("\nVerifique se:")
        print("• PostgreSQL está instalado e rodando")
        print("• Credenciais no .env estão corretas")
        print("• Banco de dados existe e usuário tem permissões")
        sys.exit(1)
    
    # Executar testes
    if not run_tests():
        print("\n⚠️  Alguns testes falharam, mas o setup básico foi concluído")
    
    print("\n" + "=" * 60)
    print("✅ CONFIGURAÇÃO CONCLUÍDA!")
    print("")
    print("🚀 Para executar o bot:")
    print("   python bot.py")
    print("")
    print("📚 Comandos úteis:")
    print("   /setup     - Configura painel de inscrições")
    print("   /equipes   - Sistema de busca de equipes")
    print("   /stats     - Estatísticas de inscrições")
    print("")
    print("📖 Veja CLAUDE.md para mais informações")
    print("=" * 60)

if __name__ == "__main__":
    main()