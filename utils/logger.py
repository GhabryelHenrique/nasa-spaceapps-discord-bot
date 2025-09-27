"""
Sistema de logging centralizado para o NASA Space Apps Bot
Envia logs importantes para um canal Discord específico
"""

import logging
import asyncio
import traceback
from datetime import datetime
from typing import Optional
import discord

class DiscordLogHandler(logging.Handler):
    """Handler customizado para enviar logs para canal Discord"""
    
    def __init__(self, bot=None, channel_id: int = None):
        super().__init__()
        self.bot = bot
        # Usar configuração do config.py se disponível
        if channel_id is None:
            try:
                import config
                self.channel_id = config.LOG_CHANNEL_ID
            except:
                self.channel_id = 1404498057239859371  # Fallback
        else:
            self.channel_id = channel_id
        self.channel = None
        self.message_queue = []
        self.is_sending = False
        
    def set_bot(self, bot):
        """Define o bot após inicialização"""
        self.bot = bot
        if bot and bot.is_ready():
            asyncio.create_task(self._get_channel())
    
    async def _get_channel(self):
        """Obtém o canal de logs"""
        if self.bot and self.bot.is_ready():
            try:
                self.channel = self.bot.get_channel(self.channel_id)
                if not self.channel:
                    # Tentar fetch se get não funcionar
                    self.channel = await self.bot.fetch_channel(self.channel_id)
                
                # Processar mensagens em fila
                if self.channel and self.message_queue:
                    await self._process_queue()
                    
            except Exception as e:
                print(f"Erro ao obter canal de logs: {e}")
    
    async def _process_queue(self):
        """Processa mensagens em fila"""
        if self.is_sending:
            return
            
        self.is_sending = True
        while self.message_queue:
            embed = self.message_queue.pop(0)
            try:
                if self.channel:
                    await self.channel.send(embed=embed)
                    await asyncio.sleep(1)  # Rate limit
            except Exception as e:
                print(f"Erro ao enviar log para Discord: {e}")
                break
        self.is_sending = False
    
    def emit(self, record):
        """Emite log para Discord"""
        try:
            embed = self._create_embed(record)
            
            if self.channel:
                # Enviar imediatamente se canal disponível
                asyncio.create_task(self._send_embed(embed))
            else:
                # Adicionar à fila se canal não disponível
                self.message_queue.append(embed)
                if len(self.message_queue) > 50:  # Limitar fila
                    self.message_queue.pop(0)
                
                # Tentar obter canal
                if self.bot:
                    asyncio.create_task(self._get_channel())
                    
        except Exception as e:
            print(f"Erro no DiscordLogHandler: {e}")
    
    async def _send_embed(self, embed):
        """Envia embed para o canal"""
        try:
            if self.channel:
                await self.channel.send(embed=embed)
        except Exception as e:
            print(f"Erro ao enviar embed de log: {e}")
    
    def _create_embed(self, record) -> discord.Embed:
        """Cria embed para o log"""
        level_colors = {
            'ERROR': discord.Color.red(),
            'WARNING': discord.Color.orange(),
            'INFO': discord.Color.blue(),
            'DEBUG': discord.Color.light_grey()
        }
        
        level_emojis = {
            'ERROR': '🔴',
            'WARNING': '🟠', 
            'INFO': '🔵',
            'DEBUG': '⚪'
        }
        
        color = level_colors.get(record.levelname, discord.Color.light_grey())
        emoji = level_emojis.get(record.levelname, '📝')
        
        embed = discord.Embed(
            title=f"{emoji} {record.levelname}",
            color=color,
            timestamp=datetime.fromtimestamp(record.created)
        )
        
        # Adicionar informações do log
        embed.add_field(name="Módulo", value=record.name, inline=True)
        embed.add_field(name="Função", value=record.funcName or "N/A", inline=True)
        embed.add_field(name="Linha", value=record.lineno, inline=True)
        
        # Mensagem principal (limitar tamanho)
        message = record.getMessage()
        if len(message) > 1000:
            message = message[:1000] + "..."
        embed.add_field(name="Mensagem", value=f"```{message}```", inline=False)
        
        # Adicionar stack trace se for erro
        if record.levelname == 'ERROR' and record.exc_info:
            tb = ''.join(traceback.format_exception(*record.exc_info))
            if len(tb) > 1000:
                tb = tb[-1000:]  # Pegar últimas 1000 chars
            embed.add_field(name="Stack Trace", value=f"```python\n{tb}```", inline=False)
        
        embed.set_footer(text="NASA Space Apps Bot - Sistema de Logs")
        return embed


class BotLogger:
    """Logger principal do bot"""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.logger = logging.getLogger('nasa_spaceapps_bot')
        self.discord_handler = None
        self._setup_logger()
    
    def _setup_logger(self):
        """Configura o sistema de logging"""
        # Configurar nível do logger
        self.logger.setLevel(logging.DEBUG)
        
        # Limpar handlers existentes
        self.logger.handlers.clear()
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Handler para arquivo
        file_handler = logging.FileHandler('nasa_spaceapps_bot.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Handler para Discord (apenas WARN e ERROR)
        self.discord_handler = DiscordLogHandler(self.bot)
        self.discord_handler.setLevel(logging.WARNING)
        self.logger.addHandler(self.discord_handler)
    
    def set_bot(self, bot):
        """Define o bot após inicialização"""
        self.bot = bot
        if self.discord_handler:
            self.discord_handler.set_bot(bot)
    
    def info(self, message: str, **kwargs):
        """Log de informação"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log de warning"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, exc_info=None, **kwargs):
        """Log de erro"""
        self.logger.error(message, exc_info=exc_info, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log de debug"""
        self.logger.debug(message, **kwargs)
    
    def log_user_action(self, user_id: int, action: str, details: str = ""):
        """Log de ação de usuário"""
        self.info(f"Usuário {user_id} executou: {action} | {details}")
    
    def log_database_operation(self, operation: str, table: str, success: bool, details: str = ""):
        """Log de operação de banco de dados"""
        level = self.info if success else self.warning
        status = "✅" if success else "❌"
        level(f"DB {status} {operation} em {table} | {details}")
    
    def log_command_execution(self, command: str, user_id: int, success: bool, error_msg: str = ""):
        """Log de execução de comando"""
        if success:
            self.info(f"Comando /{command} executado com sucesso por usuário {user_id}")
        else:
            self.warning(f"Comando /{command} falhou para usuário {user_id}: {error_msg}")
    
    def log_team_operation(self, operation: str, team_name: str, user_id: int, success: bool, details: str = ""):
        """Log de operações de equipe"""
        status = "✅" if success else "❌"
        level = self.info if success else self.warning
        level(f"Equipe {status} {operation}: '{team_name}' por usuário {user_id} | {details}")
    
    def log_application_action(self, action: str, applicant_id: int, team_name: str, leader_id: int, details: str = ""):
        """Log de ações de aplicação"""
        self.info(f"Aplicação {action}: Candidato {applicant_id} -> Equipe '{team_name}' (Líder: {leader_id}) | {details}")


# Instância global do logger
bot_logger = BotLogger()

# Funções de conveniência para importação
def get_logger():
    """Retorna o logger principal"""
    return bot_logger

def log_info(message: str, **kwargs):
    """Log de informação"""
    bot_logger.info(message, **kwargs)

def log_warning(message: str, **kwargs):
    """Log de warning"""
    bot_logger.warning(message, **kwargs)

def log_error(message: str, exc_info=None, **kwargs):
    """Log de erro"""
    bot_logger.error(message, exc_info=exc_info, **kwargs)

def log_debug(message: str, **kwargs):
    """Log de debug"""
    bot_logger.debug(message, **kwargs)

def set_bot_instance(bot):
    """Define a instância do bot para logging"""
    bot_logger.set_bot(bot)