#!/usr/bin/env python3
"""
Script para executar todos os testes
"""

import sys
import subprocess
import os
from pathlib import Path

def install_test_dependencies():
    """Instala dependências de teste"""
    test_packages = [
        'pytest',
        'pytest-asyncio',
        'aiosqlite'  # Para testes com SQLite
    ]
    
    print("📦 Instalando dependências de teste...")
    for package in test_packages:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                          check=True, capture_output=True)
            print(f"✅ {package} instalado")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao instalar {package}: {e}")
            return False
    
    return True

def run_tests():
    """Executa os testes com pytest"""
    print("\n🧪 Executando testes...")
    
    # Adicionar diretório atual ao PYTHONPATH
    current_dir = Path.cwd()
    env = os.environ.copy()
    env['PYTHONPATH'] = str(current_dir)
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/', 
            '-v',  # Verbose
            '--tb=short',  # Traceback curto
            '--disable-warnings'  # Desabilitar warnings
        ], env=env, capture_output=True, text=True)
        
        print("📊 Resultado dos testes:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Todos os testes passaram!")
            return True
        else:
            print("❌ Alguns testes falharam")
            return False
            
    except FileNotFoundError:
        print("❌ pytest não encontrado. Instale com: pip install pytest")
        return False
    except Exception as e:
        print(f"❌ Erro ao executar testes: {e}")
        return False

def main():
    """Função principal"""
    print("=" * 50)
    print("🧪 EXECUTOR DE TESTES - NASA SPACE APPS BOT")
    print("=" * 50)
    
    # Verificar se estamos no diretório correto
    if not Path('tests').exists():
        print("❌ Diretório 'tests' não encontrado!")
        print("   Execute este script no diretório raiz do projeto")
        sys.exit(1)
    
    # Instalar dependências de teste
    if not install_test_dependencies():
        print("❌ Falha ao instalar dependências de teste")
        sys.exit(1)
    
    # Executar testes
    success = run_tests()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ TESTES CONCLUÍDOS COM SUCESSO!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        sys.exit(1)
    
    print("=" * 50)

if __name__ == "__main__":
    main()