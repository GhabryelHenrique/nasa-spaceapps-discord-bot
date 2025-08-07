"""
Testes para funções utilitárias
"""

import pytest
from utils.helpers import validate_email, validate_cpf, validate_phone, validate_date, format_cpf, format_phone

class TestValidationFunctions:
    
    def test_validate_email_valid(self):
        """Testa validação de emails válidos"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "123@numbers.org",
            "user+tag@gmail.com"
        ]
        
        for email in valid_emails:
            assert validate_email(email), f"Email {email} deveria ser válido"
    
    def test_validate_email_invalid(self):
        """Testa validação de emails inválidos"""
        invalid_emails = [
            "plainaddress",
            "@missinglocalpart.com",
            "missing@.com",
            "spaces in@email.com",
            "email@",
            ".email@domain.com",
            "email.@domain.com"
        ]
        
        for email in invalid_emails:
            assert not validate_email(email), f"Email {email} deveria ser inválido"
    
    def test_validate_cpf_valid(self):
        """Testa validação de CPFs válidos"""
        valid_cpfs = [
            "11144477735",  # CPF válido
            "12345678909",  # CPF válido
            "00011122233"   # CPF válido
        ]
        
        for cpf in valid_cpfs:
            assert validate_cpf(cpf), f"CPF {cpf} deveria ser válido"
    
    def test_validate_cpf_invalid(self):
        """Testa validação de CPFs inválidos"""
        invalid_cpfs = [
            "11111111111",  # Todos iguais
            "12345678901",  # Dígitos verificadores incorretos
            "123456789",    # Muito curto
            "123456789012", # Muito longo
            "abcdefghijk",  # Não numérico
            ""              # Vazio
        ]
        
        for cpf in invalid_cpfs:
            assert not validate_cpf(cpf), f"CPF {cpf} deveria ser inválido"
    
    def test_validate_phone_valid(self):
        """Testa validação de telefones válidos"""
        valid_phones = [
            "11999887766",   # Celular SP
            "34988776655",   # Celular MG
            "1133334444",    # Fixo SP
            "3433334444"     # Fixo MG
        ]
        
        for phone in valid_phones:
            assert validate_phone(phone), f"Telefone {phone} deveria ser válido"
    
    def test_validate_phone_invalid(self):
        """Testa validação de telefones inválidos"""
        invalid_phones = [
            "999887766",     # Sem DDD
            "01999887766",   # DDD inválido (01)
            "119998877661",  # Muito longo
            "abc1234567",    # Não numérico
            ""               # Vazio
        ]
        
        for phone in invalid_phones:
            assert not validate_phone(phone), f"Telefone {phone} deveria ser inválido"
    
    def test_validate_date_valid(self):
        """Testa validação de datas válidas"""
        valid_dates = [
            "15/08/1995",    # Data válida
            "29/02/2020",    # Ano bissexto
            "01/01/2000",    # Válida
            "31/12/1990"     # Válida
        ]
        
        for date in valid_dates:
            assert validate_date(date), f"Data {date} deveria ser válida"
    
    def test_validate_date_invalid(self):
        """Testa validação de datas inválidas"""
        invalid_dates = [
            "29/02/2021",    # Não é bissexto
            "32/01/2000",    # Dia inválido
            "15/13/2000",    # Mês inválido
            "15/08/2030",    # Muito no futuro
            "15/08/1920",    # Muito no passado
            "15-08-2000",    # Formato errado
            "abc",           # Não é data
            ""               # Vazio
        ]
        
        for date in invalid_dates:
            assert not validate_date(date), f"Data {date} deveria ser inválida"
    
    def test_format_cpf(self):
        """Testa formatação de CPF"""
        assert format_cpf("12345678901") == "123.456.789-01"
        assert format_cpf("111.444.777-35") == "111.444.777-35"  # Já formatado
    
    def test_format_phone(self):
        """Testa formatação de telefone"""
        assert format_phone("11999887766") == "(11) 99988-7766"  # Celular
        assert format_phone("1133334444") == "(11) 3333-4444"    # Fixo
        assert format_phone("123") == "123"                      # Muito curto, não formata