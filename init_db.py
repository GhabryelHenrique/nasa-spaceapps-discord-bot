#!/usr/bin/env python3
"""
Script simples para inicializar apenas o banco de dados
Para configuração completa, use: python setup.py
"""

from database.setup import db_setup

def main():
    print("Inicializando banco de dados...")
    
    if db_setup.initialize_database():
        print("Banco de dados inicializado com sucesso!")
        print("Execute 'python bot.py' para iniciar o bot")
    else:
        print("Falha na inicializacao do banco de dados")
        print("Para configuracao completa, execute: python setup.py")

if __name__ == "__main__":
    main()