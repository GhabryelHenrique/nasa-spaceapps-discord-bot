import discord
from discord.ext import commands
import random
import string
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import select
from database.db import DatabaseManager
from database.models import Participante
from utils.helpers import validate_email
import config

class EmailVerificationHandler:
    def __init__(self, bot):
        self.bot = bot
        self.verification_sessions = {}  # Armazena sessões de verificação ativas

    async def start_email_verification_process(self, channel, user):
        """Inicia o processo de verificação por email"""
        embed = discord.Embed(
            title="🔍 Verificação de Inscrição",
            description="""Para acessar suas informações de inscrição, preciso verificar seu email.

Por favor, **digite o email** que você usou para se inscrever no NASA Space Apps Challenge.

**Você pode cancelar a qualquer momento digitando `cancelar`**""",
            color=discord.Color.blue()
        )
        embed.set_footer(text="NASA Space Apps Challenge 2024")
        
        await channel.send(f"Olá {user.mention}!", embed=embed)
        
        # Inicializar sessão do usuário
        self.verification_sessions[user.id] = {
            'channel': channel,
            'step': 'waiting_email',
            'email': None,
            'verification_code': None,
            'active': True,
            'attempts': 0
        }

    async def process_verification_message(self, message):
        """Processa mensagens do usuário durante a verificação"""
        user_id = message.author.id
        session = self.verification_sessions.get(user_id)
        
        if not session or not session['active']:
            return
        
        if message.channel.id != session['channel'].id:
            return
        
        content = message.content.strip()
        
        # Verificar se o usuário quer cancelar
        if content.lower() == 'cancelar':
            await self.cancel_verification(user_id)
            return
        
        if session['step'] == 'waiting_email':
            await self.handle_email_input(user_id, content)
        elif session['step'] == 'waiting_code':
            await self.handle_code_input(user_id, content)

    async def handle_email_input(self, user_id, email):
        """Processa a entrada do email"""
        session = self.verification_sessions.get(user_id)
        if not session:
            return
        
        # Validar formato do email
        if not validate_email(email):
            embed = discord.Embed(
                title="Email Inválido",
                description="Por favor, digite um endereço de email válido.",
                color=discord.Color.red()
            )
            await session['channel'].send(embed=embed)
            return
        
        # Verificar se o email existe no banco de dados
        try:
            async with await DatabaseManager.get_session() as db_session:
                result = await db_session.execute(
                    select(Participante).where(Participante.email == email.lower())
                )
                participante = result.scalars().first()
                
                if not participante:
                    session['attempts'] += 1
                    if session['attempts'] >= 3:
                        embed = discord.Embed(
                            title="Muitas Tentativas",
                            description="Você excedeu o número máximo de tentativas. Este canal será fechado em 30 segundos.",
                            color=discord.Color.red()
                        )
                        await session['channel'].send(embed=embed)
                        await asyncio.sleep(30)
                        await session['channel'].delete(reason="Verificação cancelada - muitas tentativas")
                        session['active'] = False
                        return
                    
                    embed = discord.Embed(
                        title="Email Não Encontrado",
                        description=f"Não encontrei uma inscrição com este email. Tentativas restantes: {3 - session['attempts']}\n\nTente novamente ou digite `cancelar` para sair.",
                        color=discord.Color.red()
                    )
                    await session['channel'].send(embed=embed)
                    return
                
                # Email encontrado, gerar e enviar código
                session['email'] = email.lower()
                session['participante'] = participante
                session['verification_code'] = self.generate_verification_code()
                session['step'] = 'waiting_code'
                
                # Enviar código por email
                if await self.send_verification_email(email, session['verification_code'], participante.nome):
                    embed = discord.Embed(
                        title="Código Enviado!",
                        description=f"Enviei um código de verificação para **{email}**.\n\nDigite o código de 6 dígitos que você recebeu por email.",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="O código expira em 10 minutos")
                    await session['channel'].send(embed=embed)
                    
                    # Configurar timeout para o código
                    await asyncio.sleep(600)  # 10 minutos
                    if session.get('step') == 'waiting_code' and session['active']:
                        embed = discord.Embed(
                            title="Código Expirado",
                            description="O código de verificação expirou. Este canal será fechado em 30 segundos.",
                            color=discord.Color.red()
                        )
                        await session['channel'].send(embed=embed)
                        await asyncio.sleep(30)
                        await session['channel'].delete(reason="Código de verificação expirado")
                        session['active'] = False
                else:
                    embed = discord.Embed(
                        title="Erro ao Enviar Email",
                        description="Não foi possível enviar o código de verificação. Tente novamente mais tarde.",
                        color=discord.Color.red()
                    )
                    await session['channel'].send(embed=embed)
                    
        except Exception as e:
            print(f"Erro ao verificar email: {e}")
            embed = discord.Embed(
                title="Erro Interno",
                description="Ocorreu um erro ao verificar o email. Tente novamente mais tarde.",
                color=discord.Color.red()
            )
            await session['channel'].send(embed=embed)

    async def handle_code_input(self, user_id, code):
        """Processa a entrada do código de verificação"""
        session = self.verification_sessions.get(user_id)
        if not session:
            return
        
        # Verificar se o código está correto
        if code.strip() == session['verification_code']:
            # Código correto, mostrar informações da inscrição
            await self.show_registration_info(user_id)
        else:
            session['attempts'] += 1
            if session['attempts'] >= 3:
                embed = discord.Embed(
                    title="Muitas Tentativas",
                    description="Você excedeu o número máximo de tentativas. Este canal será fechado em 30 segundos.",
                    color=discord.Color.red()
                )
                await session['channel'].send(embed=embed)
                await asyncio.sleep(30)
                await session['channel'].delete(reason="Verificação cancelada - muitas tentativas")
                session['active'] = False
                return
            
            embed = discord.Embed(
                title="Código Incorreto",
                description=f"Código incorreto. Tentativas restantes: {3 - session['attempts']}\n\nTente novamente.",
                color=discord.Color.red()
            )
            await session['channel'].send(embed=embed)

    async def show_registration_info(self, user_id):
        """Mostra as informações da inscrição verificada"""
        session = self.verification_sessions.get(user_id)
        if not session:
            return
        
        participante = session['participante']
        
        # Buscar informações dos membros convidados
        team_members_info = ""
        if participante.membros_convidados:
            member_ids = participante.membros_convidados.split(',')
            mentions = []
            for member_id in member_ids:
                try:
                    member = session['channel'].guild.get_member(int(member_id))
                    if member:
                        mentions.append(f"• {member.display_name} (<@{member_id}>)")
                    else:
                        mentions.append(f"• Usuário ID: {member_id}")
                except:
                    mentions.append(f"• Usuário ID: {member_id}")
            team_members_info = "\n".join(mentions) if mentions else "Nenhum"
        else:
            team_members_info = "Nenhum"
        
        embed = discord.Embed(
            title="✅ Verificação Concluída!",
            description=f"**Suas informações de inscrição:**",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="👤 Dados Pessoais",
            value=f"**Nome:** {participante.nome} {participante.sobrenome}\n"
                  f"**Email:** {participante.email}\n"
                  f"**Telefone:** {participante.telefone}\n"
                  f"**Cidade:** {participante.cidade}\n"
                  f"**CPF:** {participante.cpf}\n"
                  f"**Data de Nascimento:** {participante.data_nascimento}",
            inline=False
        )
        
        embed.add_field(
            name="🎓 Dados Acadêmicos",
            value=f"**Escolaridade:** {participante.escolaridade.value}\n"
                  f"**Modalidade:** {participante.modalidade.value}",
            inline=False
        )
        
        embed.add_field(
            name="👥 Equipe",
            value=f"**Nome da Equipe:** {participante.nome_equipe}\n"
                  f"**Membros Convidados:**\n{team_members_info}",
            inline=False
        )
        
        embed.add_field(
            name="📅 Inscrição",
            value=f"**Data:** {participante.data_inscricao.strftime('%d/%m/%Y às %H:%M')}",
            inline=False
        )
        
        embed.set_footer(text="NASA Space Apps Challenge 2024 - Uberlândia")
        
        await session['channel'].send(embed=embed)
        
        # Aguardar 60 segundos e deletar o canal
        await asyncio.sleep(60)
        try:
            await session['channel'].delete(reason="Verificação concluída - canal removido automaticamente")
            print(f"Canal de verificação {session['channel'].name} deletado")
        except Exception as e:
            print(f"Erro ao deletar canal de verificação: {e}")
        
        # Limpar sessão
        session['active'] = False

    def generate_verification_code(self):
        """Gera um código de verificação de 6 dígitos"""
        return ''.join(random.choices(string.digits, k=6))

    async def send_verification_email(self, email, code, nome):
        """Envia o código de verificação por email"""
        try:
            # Configurações do servidor SMTP (você precisa configurar isso)
            smtp_server = config.SMTP_SERVER if hasattr(config, 'SMTP_SERVER') else None
            smtp_port = config.SMTP_PORT if hasattr(config, 'SMTP_PORT') else 587
            smtp_username = config.SMTP_USERNAME if hasattr(config, 'SMTP_USERNAME') else None
            smtp_password = config.SMTP_PASSWORD if hasattr(config, 'SMTP_PASSWORD') else None
            
            if not all([smtp_server, smtp_username, smtp_password]):
                print("Configurações SMTP não encontradas. Simulando envio de email...")
                print(f"[SIMULAÇÃO] Código {code} seria enviado para {email}")
                return True  # Simular sucesso para desenvolvimento
            
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = smtp_username
            msg['To'] = email
            msg['Subject'] = "Código de Verificação - NASA Space Apps Challenge"
            
            body = f"""
Olá {nome},

Seu código de verificação para acessar suas informações de inscrição no NASA Space Apps Challenge é:

{code}

Este código expira em 10 minutos.

Se você não solicitou este código, ignore este email.

Atenciosamente,
Equipe NASA Space Apps Challenge - Uberlândia
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Conectar e enviar
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            
            print(f"Código de verificação enviado para {email}")
            return True
            
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
            return False

    async def cancel_verification(self, user_id):
        """Cancela o processo de verificação"""
        session = self.verification_sessions.get(user_id)
        if session:
            session['active'] = False
            
            embed = discord.Embed(
                title="Verificação Cancelada",
                description="A verificação foi cancelada. Este canal será fechado em 30 segundos.",
                color=discord.Color.red()
            )
            await session['channel'].send(embed=embed)
            
            await asyncio.sleep(30)
            try:
                await session['channel'].delete(reason="Verificação cancelada pelo usuário")
            except Exception as e:
                print(f"Erro ao deletar canal: {e}")