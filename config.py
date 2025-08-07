import os
from dotenv import load_dotenv

load_dotenv()

# Configurações do Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID')) if os.getenv('GUILD_ID') else None

# Configurações do Banco de Dados
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://nasa_bot_user:senha123@localhost:5432/nasa_bot')

# Outras configurações
REGISTRATION_CATEGORY_NAME = "NASA Space Apps - Inscrições"

# Configurações de Email (para verificação)
SMTP_SERVER = os.getenv('SMTP_SERVER')  # ex: smtp.gmail.com
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')  # seu email
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')  # senha do app ou senha do email