import discord
from discord.ext import commands
from sqlalchemy import select
from database.db import DatabaseManager
from database.models import Participante, EscolaridadeEnum, ModalidadeEnum
from utils.helpers import validate_email, validate_cpf, validate_phone, validate_date
from utils.logger import get_logger
import asyncio

class RegistrationHandler:
    def __init__(self, bot):
        self.bot = bot
        self.user_sessions = {}  # Armazena sessões de inscrição ativas
        self.logger = get_logger()

    async def check_existing_registration(self, user_id):
        """Verifica se o usuário já está inscrito"""
        try:
            async with await DatabaseManager.get_session() as session:
                result = await session.execute(
                    select(Participante).where(Participante.discord_user_id == user_id)
                )
                is_registered = result.scalars().first() is not None
                self.logger.debug(f"Verificação de inscrição para usuário {user_id}: {'Já inscrito' if is_registered else 'Não inscrito'}")
                return is_registered
        except Exception as e:
            self.logger.error(f"Erro ao verificar inscrição existente para usuário {user_id}", exc_info=e)
            return True  # Assumir inscrito em caso de erro para evitar duplicatas

    async def start_registration_process(self, channel, user):
        """Inicia o processo de inscrição no canal privado"""
        try:
            self.logger.log_user_action(user.id, "início_inscrição", f"Canal: {channel.name}")
            
            embed = discord.Embed(
                title="🚀 NASA Space Apps Challenge - Uberlândia",
                description="""Bem-vindo ao processo de inscrição!

Vou fazer algumas perguntas para completar sua inscrição. Responda uma pergunta por vez com as informações solicitadas.

**Você pode cancelar a qualquer momento digitando `cancelar`**""",
                color=discord.Color.blue()
            )
            embed.set_footer(text="NASA Space Apps Challenge 2025")
            
            await channel.send(f"Olá {user.mention}!", embed=embed)
            
            # Inicializar sessão do usuário
            self.user_sessions[user.id] = {
                'channel': channel,
                'step': 0,
                'data': {},
                'active': True
            }
            self.logger.debug(f"Sessão criada para usuário {user.id}. Total de sessões: {len(self.user_sessions)}")
            
            # Começar com a primeira pergunta
            await self.ask_next_question(user.id)
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar processo de inscrição para usuário {user.id}", exc_info=e)
            try:
                error_embed = discord.Embed(
                    title="❌ Erro",
                    description="Ocorreu um erro ao iniciar o processo de inscrição. Tente novamente ou contate um administrador.",
                    color=discord.Color.red()
                )
                await channel.send(embed=error_embed)
            except:
                pass

    async def ask_next_question(self, user_id):
        """Faz a próxima pergunta do formulário"""
        session = self.user_sessions.get(user_id)
        if not session or not session['active']:
            return
        
        questions = [
            ("nome", "**Nome:**", "Digite seu primeiro nome:"),
            ("sobrenome", "**Sobrenome:**", "Digite seu sobrenome:"),
            ("email", "**Email:**", "Digite seu melhor email:"),
            ("telefone", "**Telefone:**", "Digite seu telefone de contato (com DDD):"),
            ("cpf", "**CPF:**", "Digite seu CPF (apenas números):"),
            ("cidade", "**Cidade:**", "Digite a cidade onde você reside:"),
            ("data_nascimento", "**Data de Nascimento:**", "Digite sua data de nascimento (DD/MM/AAAA):"),
            ("escolaridade", "**Escolaridade:**", self.get_escolaridade_options()),
            ("modalidade", "**Modalidade:**", self.get_modalidade_options()),
            ("nome_equipe", "**Nome da Equipe:**", "Digite o nome único da sua equipe (máximo 100 caracteres):"),
            ("membros_convidados", "**Membros da Equipe:**", "Mencione os usuários que você quer convidar para sua equipe (ex: @usuario1 @usuario2) ou digite 'nenhum' se não quiser convidar ninguém agora:")
        ]
        
        if session['step'] < len(questions):
            field_name, title, question = questions[session['step']]
            
            embed = discord.Embed(
                title=title,
                description=question,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Pergunta {session['step'] + 1} de {len(questions)} | Digite 'cancelar' para cancelar")
            
            await session['channel'].send(embed=embed)
        else:
            await self.complete_registration(user_id)

    def get_escolaridade_options(self):
        """Retorna as opções de escolaridade formatadas"""
        options = []
        for i, enum_value in enumerate(EscolaridadeEnum, 1):
            options.append(f"`{i}` - {enum_value.value}")
        
        return "Escolha sua escolaridade digitando o número correspondente:\n\n" + "\n".join(options)

    def get_modalidade_options(self):
        """Retorna as opções de modalidade formatadas"""
        return """Escolha como gostaria de participar digitando o número correspondente:

`1` - Presencialmente em Uberlândia
`2` - Remotamente de qualquer lugar do mundo"""

    async def process_answer(self, message):
        """Processa a resposta do usuário"""
        user_id = message.author.id
        session = self.user_sessions.get(user_id)
        
        print(f"[DEBUG] Processando resposta de usuário {user_id}")
        print(f"[DEBUG] Sessões ativas: {list(self.user_sessions.keys())}")
        
        if not session or not session['active']:
            print(f"[DEBUG] Sessão não encontrada ou inativa para usuário {user_id}")
            return
        
        if message.channel.id != session['channel'].id:
            print(f"[DEBUG] Canal diferente: mensagem em {message.channel.id}, sessão em {session['channel'].id}")
            return
        
        answer = message.content.strip()
        
        # Verificar se o usuário quer cancelar
        if answer.lower() == 'cancelar':
            await self.cancel_registration(user_id)
            return
        
        questions = [
            ("nome", self.validate_nome),
            ("sobrenome", self.validate_sobrenome),
            ("email", self.validate_email),
            ("telefone", self.validate_telefone),
            ("cpf", self.validate_cpf),
            ("cidade", self.validate_cidade),
            ("data_nascimento", self.validate_data_nascimento),
            ("escolaridade", self.validate_escolaridade),
            ("modalidade", self.validate_modalidade),
            ("nome_equipe", self.validate_nome_equipe),
            ("membros_convidados", self.validate_membros_convidados)
        ]
        
        field_name, validator = questions[session['step']]
        
        # Validar resposta
        is_valid, processed_value, error_message = await validator(answer)
        
        if not is_valid:
            embed = discord.Embed(
                title="Resposta Inválida",
                description=error_message,
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed)
            return
        
        # Salvar resposta válida
        session['data'][field_name] = processed_value
        session['step'] += 1
        
        # Confirmar recebimento
        display_value = processed_value.value if hasattr(processed_value, 'value') else processed_value
        embed = discord.Embed(
            title="Resposta Registrada",
            description=f"**{field_name.replace('_', ' ').title()}:** {display_value}",
            color=discord.Color.green()
        )
        await message.channel.send(embed=embed)
        
        # Aguardar um pouco antes da próxima pergunta
        await asyncio.sleep(1)
        
        # Próxima pergunta
        await self.ask_next_question(user_id)

    # Métodos de validação
    async def validate_nome(self, answer):
        if len(answer) < 2 or len(answer) > 50:
            return False, None, "O nome deve ter entre 2 e 50 caracteres."
        if not answer.replace(' ', '').isalpha():
            return False, None, "O nome deve conter apenas letras."
        return True, answer.title(), None

    async def validate_sobrenome(self, answer):
        if len(answer) < 2 or len(answer) > 50:
            return False, None, "O sobrenome deve ter entre 2 e 50 caracteres."
        if not answer.replace(' ', '').isalpha():
            return False, None, "O sobrenome deve conter apenas letras."
        return True, answer.title(), None

    async def validate_email(self, answer):
        if not validate_email(answer):
            return False, None, "Por favor, digite um email válido."
        return True, answer.lower(), None

    async def validate_telefone(self, answer):
        if not validate_phone(answer):
            return False, None, "Por favor, digite um telefone válido com DDD (ex: 34999887766)."
        return True, answer, None

    async def validate_cpf(self, answer):
        if not validate_cpf(answer):
            return False, None, "Por favor, digite um CPF válido (apenas números)."
        return True, answer, None

    async def validate_cidade(self, answer):
        if len(answer) < 2 or len(answer) > 100:
            return False, None, "O nome da cidade deve ter entre 2 e 100 caracteres."
        return True, answer.title(), None

    async def validate_data_nascimento(self, answer):
        if not validate_date(answer):
            return False, None, "Por favor, digite uma data válida no formato DD/MM/AAAA."
        return True, answer, None

    async def validate_escolaridade(self, answer):
        try:
            choice = int(answer)
            escolaridade_list = list(EscolaridadeEnum)
            if 1 <= choice <= len(escolaridade_list):
                return True, escolaridade_list[choice - 1], None
            else:
                return False, None, f"Por favor, digite um número de 1 a {len(escolaridade_list)}."
        except ValueError:
            return False, None, "Por favor, digite apenas o número correspondente à sua escolaridade."

    async def validate_modalidade(self, answer):
        try:
            choice = int(answer)
            modalidade_list = list(ModalidadeEnum)
            if 1 <= choice <= len(modalidade_list):
                return True, modalidade_list[choice - 1], None
            else:
                return False, None, "Por favor, digite 1 para Presencial ou 2 para Remoto."
        except ValueError:
            return False, None, "Por favor, digite apenas o número correspondente à modalidade desejada."

    async def validate_nome_equipe(self, answer):
        if len(answer) < 3 or len(answer) > 100:
            return False, None, "O nome da equipe deve ter entre 3 e 100 caracteres."
        
        # Verificar se o nome da equipe já existe
        from sqlalchemy import select
        async with await DatabaseManager.get_session() as session:
            result = await session.execute(
                select(Participante).where(Participante.nome_equipe == answer.strip())
            )
            if result.scalars().first():
                return False, None, "Este nome de equipe já está em uso. Escolha outro nome."
        
        return True, answer.strip(), None

    async def validate_membros_convidados(self, answer):
        if answer.lower().strip() in ['nenhum', 'ninguem', 'não', 'nao']:
            return True, "", None
        
        # Extrair menções de usuários
        import re
        mentions = re.findall(r'<@!?(\d+)>', answer)
        
        if not mentions:
            # Tentar extrair IDs manualmente se não houver menções formatadas
            user_ids = []
            words = answer.split()
            for word in words:
                if word.startswith('@'):
                    # Tentar encontrar o usuário pelo nome
                    username = word[1:].strip()
                    try:
                        # Buscar membro no servidor
                        guild = self.bot.guilds[0] if self.bot.guilds else None
                        if guild:
                            member = discord.utils.get(guild.members, name=username)
                            if member:
                                user_ids.append(str(member.id))
                    except:
                        pass
            
            if user_ids:
                return True, ",".join(user_ids), None
            else:
                return False, None, "Por favor, mencione os usuários usando @usuario ou digite 'nenhum' se não quiser convidar ninguém."
        
        # Validar que não está convidando mais de 5 pessoas (equipe máxima de 6 incluindo o líder)
        if len(mentions) > 5:
            return False, None, "Você pode convidar no máximo 5 pessoas (equipe máxima de 6 membros)."
        
        return True, ",".join(mentions), None

    async def complete_registration(self, user_id):
        """Completa o processo de inscrição salvando no banco"""
        session = self.user_sessions.get(user_id)
        if not session:
            self.logger.warning(f"Tentativa de completar inscrição sem sessão ativa para usuário {user_id}")
            return
        
        try:
            self.logger.info(f"Completando inscrição para usuário {user_id}")
            
            # Salvar no banco de dados
            async with await DatabaseManager.get_session() as db_session:
                user = await self.bot.fetch_user(user_id)
                
                # Log dos valores dos enums para debug
                self.logger.debug(f"Dados de inscrição - Escolaridade: {session['data']['escolaridade']}, Modalidade: {session['data']['modalidade']}")
                
                participante = Participante(
                    discord_user_id=user_id,
                    discord_username=f"{user.name}#{user.discriminator}",
                    nome=session['data']['nome'],
                    sobrenome=session['data']['sobrenome'],
                    email=session['data']['email'],
                    telefone=session['data']['telefone'],
                    cpf=session['data']['cpf'],
                    cidade=session['data']['cidade'],
                    data_nascimento=session['data']['data_nascimento'],
                    escolaridade=session['data']['escolaridade'],
                    modalidade=session['data']['modalidade'],
                    nome_equipe=session['data']['nome_equipe'],
                    membros_convidados=session['data']['membros_convidados'],
                    canal_privado_id=session['channel'].id
                )
                
                db_session.add(participante)
                await db_session.commit()
                
                self.logger.log_database_operation("INSERT", "participantes", True, 
                    f"Usuário: {user.name}, Email: {session['data']['email']}, Equipe: {session['data']['nome_equipe']}")
                
                self.logger.log_user_action(user_id, "inscrição_completa", 
                    f"Nome: {session['data']['nome']} {session['data']['sobrenome']}, Equipe: {session['data']['nome_equipe']}")
            
            # Embed de confirmação
            team_info = ""
            if session['data']['membros_convidados']:
                member_ids = session['data']['membros_convidados'].split(',')
                mentions = []
                for member_id in member_ids:
                    mentions.append(f"<@{member_id}>")
                team_info = f"\n• **Equipe:** {session['data']['nome_equipe']}\n• **Convites Enviados Para:** {' '.join(mentions)}"
            else:
                team_info = f"\n• **Equipe:** {session['data']['nome_equipe']}\n• **Membros Convidados:** Nenhum"
            
            embed = discord.Embed(
                title="Inscrição Concluída!",
                description=f"""**Parabéns {session['data']['nome']}!**

Sua inscrição no NASA Space Apps Challenge foi realizada com sucesso!

**Resumo da sua inscrição:**
• **Nome:** {session['data']['nome']} {session['data']['sobrenome']}
• **Email:** {session['data']['email']}
• **Modalidade:** {session['data']['modalidade'].value}
• **Escolaridade:** {session['data']['escolaridade'].value}{team_info}

**🎯 Sua equipe está sendo configurada:**
• Role da equipe criada
• Categoria e canais exclusivos preparados
• Convites enviados por DM aos membros convidados

**Este canal será deletado em 10 segundos.**""",
                color=discord.Color.gold()
            )
            embed.set_footer(text="NASA Space Apps Challenge 2025 - Uberlândia")
            
            await session['channel'].send(embed=embed)
            
            # Criar role da equipe e canais
            guild = session['channel'].guild
            await self.create_team_infrastructure(guild, user_id, session['data'])
            
            # Aguardar 10 segundos e deletar o canal
            await asyncio.sleep(10)
            try:
                await session['channel'].delete(reason="Inscrição concluída - canal removido automaticamente")
                print(f"Canal {session['channel'].name} deletado após inscrição concluída")
            except Exception as e:
                print(f"Erro ao deletar canal: {e}")
            
            # Limpar sessão
            session['active'] = False
            
        except Exception as e:
            self.logger.error(f"Erro ao completar inscrição para usuário {user_id}", exc_info=e)
            self.logger.log_database_operation("INSERT", "participantes", False, f"Usuário: {user_id}, Erro: {str(e)}")
            
            try:
                embed = discord.Embed(
                    title="Erro na Inscrição",
                    description="Ocorreu um erro ao salvar sua inscrição. Por favor, tente novamente ou entre em contato com a organização.",
                    color=discord.Color.red()
                )
                await session['channel'].send(embed=embed)
            except Exception as send_error:
                self.logger.error(f"Erro ao enviar mensagem de erro para usuário {user_id}", exc_info=send_error)

    async def create_team_infrastructure(self, guild, leader_id, team_data):
        """Cria role da equipe, categoria e canais"""
        try:
            # 1. Criar role da equipe
            team_role = await guild.create_role(
                name=f"Equipe {team_data['nome_equipe']}",
                color=discord.Color.random(),
                mentionable=True,
                reason="Role criada para equipe NASA Space Apps"
            )
            print(f"Role '{team_role.name}' criada")
            
            # 2. Adicionar role ao líder da equipe
            leader = guild.get_member(leader_id)
            if leader:
                await leader.add_roles(team_role, reason="Líder da equipe")
                print(f"Role adicionada ao líder {leader.display_name}")
            
            # 3. Enviar convites aos membros convidados
            if team_data['membros_convidados']:
                member_ids = team_data['membros_convidados'].split(',')
                await self.send_team_invitations(guild, team_role, team_data, leader_id, member_ids)
            
            # 4. Criar categoria da equipe
            category_name = f"🚀 {team_data['nome_equipe']}"
            
            # Permissões da categoria
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                team_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    connect=True,
                    speak=True,
                    read_message_history=True,
                    add_reactions=True,
                    attach_files=True,
                    embed_links=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    connect=True,
                    manage_channels=True
                )
            }
            
            category = await guild.create_category(
                category_name,
                overwrites=overwrites,
                reason="Categoria criada para equipe NASA Space Apps"
            )
            print(f"Categoria '{category.name}' criada")
            
            # 5. Criar canal de texto geral
            text_channel = await category.create_text_channel(
                "chat-geral",
                topic=f"Canal de chat da equipe {team_data['nome_equipe']}",
                reason="Canal de texto da equipe"
            )
            
            # 6. Criar canal de texto para desenvolvimento
            dev_channel = await category.create_text_channel(
                "desenvolvimento",
                topic="Discussões técnicas e desenvolvimento do projeto",
                reason="Canal de desenvolvimento da equipe"
            )
            
            # 7. Criar canal de voz
            voice_channel = await category.create_voice_channel(
                "Reunião da Equipe",
                reason="Canal de voz da equipe"
            )
            
            # 8. Enviar mensagem de boas-vindas no canal de texto
            welcome_embed = discord.Embed(
                title=f"Bem-vindos à Equipe {team_data['nome_equipe']}! 🚀",
                description=f"""**Parabéns por se registrarem no NASA Space Apps Challenge!**
                
**Informações da Equipe:**
• **Líder:** <@{leader_id}>
• **Nome da Equipe:** {team_data['nome_equipe']}
• **Modalidade:** {team_data['modalidade'].value}

**Canais da Equipe:**
• {text_channel.mention} - Chat geral da equipe
• {dev_channel.mention} - Discussões técnicas e desenvolvimento
• {voice_channel.mention} - Reuniões por voz

**Próximos Passos:**
1. Discutam e escolham um desafio da NASA
2. Planejem sua solução
3. Desenvolvam o projeto durante o evento
4. Preparem a apresentação final

Boa sorte! 🌟""",
                color=discord.Color.gold()
            )
            welcome_embed.set_footer(text="NASA Space Apps Challenge 2025 - Uberlândia")
            
            await text_channel.send(embed=welcome_embed)
            
            print(f"Infraestrutura da equipe {team_data['nome_equipe']} criada com sucesso!")
            
        except Exception as e:
            print(f"Erro ao criar infraestrutura da equipe: {e}")

    async def send_team_invitations(self, guild, team_role, team_data, leader_id, member_ids):
        """Envia convites individuais para os membros convidados"""
        from views.team_invitation_view import TeamInvitationView
        
        for member_id in member_ids:
            try:
                member = guild.get_member(int(member_id))
                if member:
                    # Criar embed do convite
                    leader = guild.get_member(leader_id)
                    leader_name = leader.display_name if leader else "Líder da equipe"
                    
                    embed = discord.Embed(
                        title="🚀 Convite para Equipe NASA Space Apps!",
                        description=f"""Você foi convidado para participar de uma equipe no NASA Space Apps Challenge!

**Informações da Equipe:**
• **Nome da Equipe:** {team_data['nome_equipe']}
• **Líder:** {leader_name} (<@{leader_id}>)
• **Modalidade:** {team_data['modalidade'].value}

**Sobre o NASA Space Apps Challenge:**
O maior hackathon espacial do mundo! Você terá 48 horas para resolver desafios reais da NASA usando dados abertos.

**O que acontece se você aceitar:**
• Receberá acesso aos canais exclusivos da equipe
• Poderá colaborar no desenvolvimento da solução
• Participará da competição oficial

Você tem **1 hora** para responder a este convite.""",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="NASA Space Apps Challenge 2025 - Uberlândia")
                    embed.set_thumbnail(url="https://www.spaceappschallenge.org/assets/images/branding/space-apps-logo.png")
                    
                    # Criar view com botões
                    view = TeamInvitationView(team_role, team_data, leader_id, member.id)
                    
                    # Enviar DM com o convite
                    try:
                        await member.send(embed=embed, view=view)
                        print(f"Convite enviado para {member.display_name}")
                    except discord.Forbidden:
                        print(f"Não foi possível enviar DM para {member.display_name} - DMs desabilitadas")
                        # TODO: Criar um sistema alternativo para membros com DMs desabilitadas
                        # Por exemplo, mencionar em um canal específico
                    except Exception as dm_error:
                        print(f"Erro ao enviar DM para {member.display_name}: {dm_error}")
                        
                else:
                    print(f"Membro com ID {member_id} não encontrado no servidor")
                    
            except Exception as e:
                print(f"Erro ao processar convite para membro {member_id}: {e}")

    async def cancel_registration(self, user_id):
        """Cancela o processo de inscrição"""
        session = self.user_sessions.get(user_id)
        if session:
            session['active'] = False
            
            embed = discord.Embed(
                title="Inscrição Cancelada",
                description="Sua inscrição foi cancelada. Você pode iniciar uma nova inscrição a qualquer momento.",
                color=discord.Color.red()
            )
            await session['channel'].send(embed=embed)