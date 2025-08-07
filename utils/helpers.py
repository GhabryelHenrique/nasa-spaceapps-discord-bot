import re
from datetime import datetime

def validate_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_cpf(cpf):
    """Valida CPF brasileiro"""
    # Remove caracteres não numéricos
    cpf = re.sub(r'\D', '', cpf)
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Validação do primeiro dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[9]) != digito1:
        return False
    
    # Validação do segundo dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return int(cpf[10]) == digito2

def validate_phone(phone):
    """Valida telefone brasileiro"""
    # Remove caracteres não numéricos
    phone = re.sub(r'\D', '', phone)
    
    # Verifica se tem 10 ou 11 dígitos (com DDD)
    if len(phone) not in [10, 11]:
        return False
    
    # Verifica se o DDD é válido (11 a 99)
    ddd = int(phone[:2])
    if ddd < 11 or ddd > 99:
        return False
    
    return True

def validate_date(date_str):
    """Valida data no formato DD/MM/AAAA"""
    try:
        datetime.strptime(date_str, '%d/%m/%Y')
        
        # Verificações adicionais
        parts = date_str.split('/')
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        
        # Verifica se a pessoa tem pelo menos 10 anos e no máximo 100 anos
        current_year = datetime.now().year
        age = current_year - year
        
        if age < 10 or age > 100:
            return False
        
        return True
    except ValueError:
        return False

def format_cpf(cpf):
    """Formata CPF para exibição"""
    cpf = re.sub(r'\D', '', cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def format_phone(phone):
    """Formata telefone para exibição"""
    phone = re.sub(r'\D', '', phone)
    if len(phone) == 11:
        return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
    elif len(phone) == 10:
        return f"({phone[:2]}) {phone[2:6]}-{phone[6:]}"
    return phone