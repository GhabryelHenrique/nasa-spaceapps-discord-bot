import discord
from discord.ext import commands
import asyncio
import config
from database.db import create_tables, DatabaseManager
from views.register_view import RegistrationView
from handlers.registration_form import RegistrationHandler
from utils.logger import get_logger, set_bot_instance

# Configurações do bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class NASASpaceAppsBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            description="Bot para inscrições no NASA Space Apps Challenge - Uberlândia"
        )
        self.registration_handler = None
        self.logger = get_logger()

    async def setup_hook(self):
        """Configurações iniciais do bot"""
        try:
            # Configurar sistema de logging
            set_bot_instance(self)
            self.logger.info("Iniciando configuração do bot...")
            
            # Criar tabelas do banco de dados
            create_tables()
            self.logger.info("Tabelas do banco de dados verificadas/criadas")
            
            # Inicializar handlers
            self.registration_handler = RegistrationHandler(self)
            from handlers.email_verification_handler import EmailVerificationHandler
            from handlers.application_handler import ApplicationHandler
            self.email_verification_handler = EmailVerificationHandler(self)
            self.application_handler = ApplicationHandler(self)
            self.logger.info("Handlers inicializados")
            
            # Adicionar views persistentes
            self.add_view(RegistrationView())
            from views.team_search_view import TeamSearchView
            self.add_view(TeamSearchView())
            self.logger.info("Views persistentes adicionadas")
            
            # Adicionar views de convites (serão recriadas dinamicamente quando necessário)
            # As views de convite são temporárias e não precisam ser persistentes
            
            self.logger.info(f'Bot configurado e pronto!')
            
        except Exception as e:
            self.logger.error("Erro crítico durante inicialização do bot", exc_info=e)

    async def on_ready(self):
        """Evento executado quando o bot fica online"""
        self.logger.info(f'Bot conectado como {self.user.name} (ID: {self.user.id})')
        
        # Configurar logger para Discord (agora que o bot está online)
        set_bot_instance(self)
        
        # Sincronizar comandos slash
        try:
            synced = await self.tree.sync()
            self.logger.info(f'Sincronizados {len(synced)} comando(s) slash')
        except Exception as e:
            self.logger.error('Erro ao sincronizar comandos slash', exc_info=e)

    async def on_message(self, message):
        """Processa mensagens"""
        # Ignorar mensagens do próprio bot
        if message.author == self.user:
            return
        
        # Debug: Log da mensagem recebida
        print(f"Mensagem recebida de {message.author}: {message.content} no canal {message.channel.name}")
        
        # Processar respostas do formulário de inscrição
        if self.registration_handler:
            print(f"Processando resposta do formulário para usuário {message.author.id}")
            await self.registration_handler.process_answer(message)
        
        # Processar mensagens de verificação por email
        if self.email_verification_handler:
            await self.email_verification_handler.process_verification_message(message)
        
        # Processar comandos
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        """Trata erros de comandos de prefixo"""
        self.logger.error(f'Erro em comando de prefixo: {ctx.command} por {ctx.author.id}', exc_info=error)
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Você não tem permissão para usar este comando.")
        else:
            await ctx.send("Ocorreu um erro ao executar o comando.")

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Trata erros de comandos slash"""
        command_name = interaction.command.name if interaction.command else "unknown"
        self.logger.error(f'Erro em comando slash: /{command_name} por {interaction.user.id}', exc_info=error)
        
        try:
            if isinstance(error, discord.app_commands.MissingPermissions):
                message = "Você não tem permissão para usar este comando."
            else:
                message = "Ocorreu um erro ao executar o comando."
            
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except:
            pass

    async def close(self):
        """Limpeza ao fechar o bot"""
        self.logger.info("Desconectando bot...")
        await DatabaseManager.close_engine()
        await super().close()

# Instância do bot
bot = NASASpaceAppsBot()

@bot.command(name='setup')
@commands.has_permissions(administrator=True)
async def setup_registration(ctx):
    """Comando para configurar o painel de inscrições"""
    embed = discord.Embed(
        title="🚀 NASA Space Apps Challenge 2025 - Uberlândia",
        description="""**O maior hackathon espacial do mundo chegou em Uberlândia!**

O NASA Space Apps Challenge é uma competição internacional onde equipes do mundo todo se unem para resolver desafios reais da NASA usando dados abertos.

**📅 Data do Evento:** [Data a ser definida]
**📍 Local:** Uberlândia, MG (presencial) ou Online (remoto)

**O que você vai fazer:**
• Formar equipes de até 6 pessoas
• Escolher um desafio da NASA
• Desenvolver uma solução em 48 horas
• Concorrer a prêmios locais e globais

**Por que participar:**
• Networking com outros desenvolvedores e cientistas
• Aprender sobre tecnologias espaciais
• Certificado de participação
• Oportunidade de ganhar prêmios
• Experiência única de inovação

Clique no botão abaixo para fazer sua inscrição e garantir sua vaga!""",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎯 Público Alvo",
        value="Estudantes, profissionais de TI, engenheiros, designers, cientistas e entusiastas da tecnologia espacial.",
        inline=False
    )
    
    embed.add_field(
        name="💡 Habilidades Valorizadas",
        value="Programação, design, ciência de dados, engenharia, comunicação e trabalho em equipe.",
        inline=False
    )
    
    embed.set_footer(text="NASA Space Apps Challenge 2025 | Uberlândia, MG")
    embed.set_thumbnail(url="https://www.spaceappschallenge.org/assets/images/branding/space-apps-logo.png")
    
    view = RegistrationView()
    await ctx.send(embed=embed, view=view)

@bot.command(name='stats')
@commands.has_permissions(administrator=True)
async def registration_stats(ctx):
    """Mostra estatísticas das inscrições"""
    try:
        from sqlalchemy import func, select
        from database.models import Participante, ModalidadeEnum, EscolaridadeEnum
        
        async with await DatabaseManager.get_session() as session:
            # Total de inscrições
            total_result = await session.execute(select(func.count(Participante.id)))
            total = total_result.scalar()
            
            # Por modalidade
            modalidade_result = await session.execute(
                select(Participante.modalidade, func.count(Participante.id))
                .group_by(Participante.modalidade)
            )
            modalidades = modalidade_result.fetchall()
            
            # Por escolaridade
            escolaridade_result = await session.execute(
                select(Participante.escolaridade, func.count(Participante.id))
                .group_by(Participante.escolaridade)
            )
            escolaridades = escolaridade_result.fetchall()
        
        embed = discord.Embed(
            title="📊 Estatísticas de Inscrições",
            description=f"**Total de Inscritos:** {total}",
            color=discord.Color.green()
        )
        
        # Modalidades
        modalidade_text = ""
        for modalidade, count in modalidades:
            modalidade_text += f"• {modalidade.value}: {count}\n"
        
        if modalidade_text:
            embed.add_field(name="Por Modalidade", value=modalidade_text, inline=True)
        
        # Escolaridades (top 5)
        if escolaridades:
            escolaridade_text = ""
            sorted_escolaridades = sorted(escolaridades, key=lambda x: x[1], reverse=True)[:5]
            for escolaridade, count in sorted_escolaridades:
                escolaridade_text += f"• {escolaridade.value}: {count}\n"
            
            embed.add_field(name="Top 5 Escolaridades", value=escolaridade_text, inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"Erro ao buscar estatísticas: {str(e)}")

@bot.command(name='export')
@commands.has_permissions(administrator=True)
async def export_registrations(ctx):
    """Exporta lista de inscritos em formato texto"""
    try:
        from database.models import Participante
        from sqlalchemy import select
        
        async with await DatabaseManager.get_session() as session:
            result = await session.execute(select(Participante).order_by(Participante.data_inscricao))
            participantes = result.scalars().all()
        
        if not participantes:
            await ctx.send("Nenhuma inscrição encontrada.")
            return
        
        # Criar arquivo texto
        content = "LISTA DE INSCRITOS - NASA SPACE APPS CHALLENGE UBERLÂNDIA\n"
        content += "=" * 60 + "\n\n"
        
        for i, p in enumerate(participantes, 1):
            content += f"{i:03d}. {p.nome} {p.sobrenome}\n"
            content += f"     Email: {p.email}\n"
            content += f"     Telefone: {p.telefone}\n"
            content += f"     Cidade: {p.cidade}\n"
            content += f"     Escolaridade: {p.escolaridade.value}\n"
            content += f"     Modalidade: {p.modalidade.value}\n"
            content += f"     Data Inscrição: {p.data_inscricao.strftime('%d/%m/%Y %H:%M')}\n"
            content += "-" * 40 + "\n"
        
        content += f"\nTotal: {len(participantes)} inscritos"
        
        # Salvar em arquivo
        with open("inscricoes_nasa_spaceapps.txt", "w", encoding="utf-8") as f:
            f.write(content)
        
        # Enviar arquivo
        file = discord.File("inscricoes_nasa_spaceapps.txt")
        await ctx.send("Lista de inscritos:", file=file)
        
    except Exception as e:
        await ctx.send(f"Erro ao exportar dados: {str(e)}")

# Versões slash dos comandos
@bot.tree.command(name='setup', description='Configurar o painel de inscrições')
@discord.app_commands.default_permissions(administrator=True)
async def setup_registration_slash(interaction: discord.Interaction):
    """Comando slash para configurar o painel de inscrições"""
    embed = discord.Embed(
        title="🚀 NASA Space Apps Challenge 2025 - Uberlândia",
        description="""**O maior hackathon espacial do mundo chegou em Uberlândia!**

O NASA Space Apps Challenge é uma competição internacional onde equipes do mundo todo se unem para resolver desafios reais da NASA usando dados abertos.

**📅 Data do Evento:** [Data a ser definida]
**📍 Local:** Uberlândia, MG (presencial) ou Online (remoto)

**O que você vai fazer:**
• Formar equipes de até 6 pessoas
• Escolher um desafio da NASA
• Desenvolver uma solução em 48 horas
• Concorrer a prêmios locais e globais

**Por que participar:**
• Networking com outros desenvolvedores e cientistas
• Aprender sobre tecnologias espaciais
• Certificado de participação
• Oportunidade de ganhar prêmios
• Experiência única de inovação

Clique no botão abaixo para fazer sua inscrição e garantir sua vaga!""",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎯 Público Alvo",
        value="Estudantes, profissionais de TI, engenheiros, designers, cientistas e entusiastas da tecnologia espacial.",
        inline=False
    )
    
    embed.add_field(
        name="💡 Habilidades Valorizadas",
        value="Programação, design, ciência de dados, engenharia, comunicação e trabalho em equipe.",
        inline=False
    )
    
    embed.set_footer(text="NASA Space Apps Challenge 2025 | Uberlândia, MG")
    embed.set_thumbnail(url="https://www.spaceappschallenge.org/assets/images/branding/space-apps-logo.png")
    
    view = RegistrationView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='stats', description='Mostrar estatísticas das inscrições')
@discord.app_commands.default_permissions(administrator=True)
async def registration_stats_slash(interaction: discord.Interaction):
    """Comando slash para mostrar estatísticas das inscrições"""
    try:
        from sqlalchemy import func, select
        from database.models import Participante, ModalidadeEnum, EscolaridadeEnum
        
        async with await DatabaseManager.get_session() as session:
            # Total de inscrições
            total_result = await session.execute(select(func.count(Participante.id)))
            total = total_result.scalar()
            
            # Por modalidade
            modalidade_result = await session.execute(
                select(Participante.modalidade, func.count(Participante.id))
                .group_by(Participante.modalidade)
            )
            modalidades = modalidade_result.fetchall()
            
            # Por escolaridade
            escolaridade_result = await session.execute(
                select(Participante.escolaridade, func.count(Participante.id))
                .group_by(Participante.escolaridade)
            )
            escolaridades = escolaridade_result.fetchall()
        
        embed = discord.Embed(
            title="📊 Estatísticas de Inscrições",
            description=f"**Total de Inscritos:** {total}",
            color=discord.Color.green()
        )
        
        # Modalidades
        modalidade_text = ""
        for modalidade, count in modalidades:
            modalidade_text += f"• {modalidade.value}: {count}\n"
        
        if modalidade_text:
            embed.add_field(name="Por Modalidade", value=modalidade_text, inline=True)
        
        # Escolaridades (top 5)
        if escolaridades:
            escolaridade_text = ""
            sorted_escolaridades = sorted(escolaridades, key=lambda x: x[1], reverse=True)[:5]
            for escolaridade, count in sorted_escolaridades:
                escolaridade_text += f"• {escolaridade.value}: {count}\n"
            
            embed.add_field(name="Top 5 Escolaridades", value=escolaridade_text, inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"Erro ao buscar estatísticas: {str(e)}")

@bot.tree.command(name='export', description='Exportar lista de inscritos em formato texto')
@discord.app_commands.default_permissions(administrator=True)
async def export_registrations_slash(interaction: discord.Interaction):
    """Comando slash para exportar lista de inscritos"""
    try:
        from database.models import Participante
        from sqlalchemy import select
        
        async with await DatabaseManager.get_session() as session:
            result = await session.execute(select(Participante).order_by(Participante.data_inscricao))
            participantes = result.scalars().all()
        
        if not participantes:
            await interaction.response.send_message("Nenhuma inscrição encontrada.")
            return
        
        # Criar arquivo texto
        content = "LISTA DE INSCRITOS - NASA SPACE APPS CHALLENGE UBERLÂNDIA\n"
        content += "=" * 60 + "\n\n"
        
        for i, p in enumerate(participantes, 1):
            content += f"{i:03d}. {p.nome} {p.sobrenome}\n"
            content += f"     Email: {p.email}\n"
            content += f"     Telefone: {p.telefone}\n"
            content += f"     Cidade: {p.cidade}\n"
            content += f"     Escolaridade: {p.escolaridade.value}\n"
            content += f"     Modalidade: {p.modalidade.value}\n"
            content += f"     Data Inscrição: {p.data_inscricao.strftime('%d/%m/%Y %H:%M')}\n"
            content += "-" * 40 + "\n"
        
        content += f"\nTotal: {len(participantes)} inscritos"
        
        # Salvar em arquivo
        with open("inscricoes_nasa_spaceapps.txt", "w", encoding="utf-8") as f:
            f.write(content)
        
        # Enviar arquivo
        file = discord.File("inscricoes_nasa_spaceapps.txt")
        await interaction.response.send_message("Lista de inscritos:", file=file)
        
    except Exception as e:
        await interaction.response.send_message(f"Erro ao exportar dados: {str(e)}")

@bot.tree.command(name='equipes', description='Painel para buscar equipes e se marcar como disponível')
async def team_search_panel(interaction: discord.Interaction):
    """Comando slash para o painel de busca de equipes"""
    try:
        bot.logger.log_command_execution('equipes', interaction.user.id, True)
        bot.logger.log_user_action(interaction.user.id, 'comando_equipes', f'Canal: {interaction.channel.name}')
        
        embed = discord.Embed(
            title="🔍 Sistema de Busca de Equipes",
            description="""**Encontre a equipe perfeita para o NASA Space Apps Challenge!**

🔍 **Ver Equipes Disponíveis** - Veja todas as equipes que estão procurando membros
💼 **Marcar Como Disponível** - Se marque como disponível para outras equipes te convidarem
👥 **Ver Pessoas Disponíveis** - (Apenas líderes) Veja pessoas procurando equipes

**Como funciona:**
1. Marque-se como disponível e descreva suas habilidades
2. Procure equipes que combinem com você
3. Envie uma aplicação explicando por que quer se juntar
4. Aguarde a resposta do líder da equipe
5. Se aprovado, você será transferido para a nova equipe!

**Importante:** Você pode estar em apenas uma equipe por vez.""",
            color=discord.Color.blue()
        )
        embed.set_footer(text="NASA Space Apps Challenge 2025 - Sistema de Equipes")
        
        from views.team_search_view import TeamSearchView
        view = TeamSearchView()
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        bot.logger.log_command_execution('equipes', interaction.user.id, False, str(e))
        bot.logger.error(f'Erro no comando /equipes para usuário {interaction.user.id}', exc_info=e)
        
        try:
            error_embed = discord.Embed(
                title="❌ Erro",
                description="Ocorreu um erro ao executar o comando. Tente novamente.",
                color=discord.Color.red()
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except:
            pass

@bot.tree.command(name='aplicacoes', description='Gerenciar aplicações para sua equipe')
async def manage_applications(interaction: discord.Interaction):
    """Comando slash para gerenciar aplicações"""
    try:
        aplicacoes, erro = await bot.application_handler.get_pending_applications(interaction.user.id)
        
        if erro:
            embed = discord.Embed(
                title="❌ Erro",
                description=erro,
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not aplicacoes:
            embed = discord.Embed(
                title="📭 Nenhuma Aplicação Pendente",
                description="Você não tem aplicações pendentes para sua equipe no momento.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Mostrar aplicações pendentes
        embed = discord.Embed(
            title="📥 Aplicações Pendentes Para Sua Equipe",
            description=f"Você tem **{len(aplicacoes)}** aplicação(ões) pendente(s)",
            color=discord.Color.blue()
        )

        for i, aplicacao in enumerate(aplicacoes[:5], 1):  # Máximo 5 por vez
            aplicante = aplicacao.aplicante
            
            field_value = f"**Candidato:** {aplicante.nome} {aplicante.sobrenome}\n"
            field_value += f"**Escolaridade:** {aplicante.escolaridade.value}\n"
            field_value += f"**Cidade:** {aplicante.cidade}\n"
            
            if aplicacao.mensagem_aplicacao:
                msg = aplicacao.mensagem_aplicacao[:100]
                if len(aplicacao.mensagem_aplicacao) > 100:
                    msg += "..."
                field_value += f"**Mensagem:** {msg}\n"
            
            if aplicante.descricao_habilidades:
                hab = aplicante.descricao_habilidades[:100]
                if len(aplicante.descricao_habilidades) > 100:
                    hab += "..."
                field_value += f"**Habilidades:** {hab}"
            
            embed.add_field(
                name=f"📝 Aplicação #{aplicacao.id}",
                value=field_value,
                inline=False
            )

        embed.set_footer(text="Use os botões abaixo para responder às aplicações")

        # Criar view com botões para cada aplicação
        view = ApplicationManagementView(aplicacoes[:5], bot.application_handler)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Erro",
            description="Ocorreu um erro ao buscar aplicações. Tente novamente.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"Erro ao buscar aplicações: {e}")

@bot.tree.command(name='minhas_aplicacoes', description='Ver suas aplicações enviadas')
async def my_applications(interaction: discord.Interaction):
    """Comando slash para ver aplicações do usuário"""
    try:
        aplicacoes, erro = await bot.application_handler.get_user_applications(interaction.user.id)
        
        if erro:
            embed = discord.Embed(
                title="❌ Erro",
                description=erro,
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not aplicacoes:
            embed = discord.Embed(
                title="📭 Nenhuma Aplicação",
                description="Você ainda não enviou nenhuma aplicação para equipes.\n\nUse `/equipes` para procurar equipes disponíveis!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="📝 Suas Aplicações",
            description=f"Você tem **{len(aplicacoes)}** aplicação(ões) enviada(s)",
            color=discord.Color.blue()
        )

        for aplicacao in aplicacoes[:10]:  # Máximo 10
            status_emoji = {
                'Pendente': '⏳',
                'Aprovada': '✅',
                'Rejeitada': '❌',
                'Cancelada': '🚫'
            }
            
            status_color = {
                'Pendente': '🟡',
                'Aprovada': '🟢',
                'Rejeitada': '🔴',
                'Cancelada': '⚫'
            }

            field_value = f"{status_color.get(aplicacao.status.value, '⚪')} **Status:** {aplicacao.status.value}\n"
            field_value += f"📅 **Enviada em:** {aplicacao.data_aplicacao.strftime('%d/%m/%Y %H:%M')}\n"
            
            if aplicacao.data_resposta:
                field_value += f"📅 **Respondida em:** {aplicacao.data_resposta.strftime('%d/%m/%Y %H:%M')}\n"
            
            if aplicacao.resposta_lider:
                resp = aplicacao.resposta_lider[:100]
                if len(aplicacao.resposta_lider) > 100:
                    resp += "..."
                field_value += f"💬 **Resposta:** {resp}"

            embed.add_field(
                name=f"{status_emoji.get(aplicacao.status.value, '📝')} {aplicacao.equipe_nome}",
                value=field_value,
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Erro",
            description="Ocorreu um erro ao buscar suas aplicações.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"Erro ao buscar aplicações do usuário: {e}")


class ApplicationManagementView(discord.ui.View):
    def __init__(self, aplicacoes, handler):
        super().__init__(timeout=300)
        self.aplicacoes = aplicacoes
        self.handler = handler
        
        # Adicionar botões para cada aplicação
        for i, aplicacao in enumerate(aplicacoes[:5], 1):
            # Botão para ver detalhes
            self.add_item(ApplicationDetailButton(aplicacao, i, handler))

class ApplicationDetailButton(discord.ui.Button):
    def __init__(self, aplicacao, number, handler):
        super().__init__(
            label=f"Ver Aplicação #{aplicacao.id}",
            style=discord.ButtonStyle.secondary,
            emoji="👤"
        )
        self.aplicacao = aplicacao
        self.handler = handler

    async def callback(self, interaction: discord.Interaction):
        # Mostrar detalhes da aplicação com botões de aprovação/rejeição
        aplicante = self.aplicacao.aplicante
        
        embed = discord.Embed(
            title=f"📝 Aplicação #{self.aplicacao.id} - {aplicante.nome} {aplicante.sobrenome}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="👤 Dados do Candidato",
            value=f"**Nome:** {aplicante.nome} {aplicante.sobrenome}\n**Email:** {aplicante.email}\n**Cidade:** {aplicante.cidade}\n**Escolaridade:** {aplicante.escolaridade.value}\n**Modalidade:** {aplicante.modalidade.value}",
            inline=False
        )
        
        if self.aplicacao.mensagem_aplicacao:
            embed.add_field(
                name="💬 Mensagem do Candidato",
                value=self.aplicacao.mensagem_aplicacao,
                inline=False
            )
        
        if aplicante.descricao_habilidades:
            embed.add_field(
                name="🛠️ Habilidades",
                value=aplicante.descricao_habilidades,
                inline=False
            )
        
        embed.add_field(
            name="📅 Data da Aplicação",
            value=self.aplicacao.data_aplicacao.strftime('%d/%m/%Y às %H:%M'),
            inline=True
        )
        
        embed.set_footer(text="Escolha uma ação abaixo")
        
        # View com botões de aprovação/rejeição
        from handlers.application_handler import ApplicationResponseView
        view = ApplicationResponseView(self.aplicacao.id, self.handler)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Error handlers para comandos de prefixo
@setup_registration.error
@registration_stats.error
@export_registrations.error
async def command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Você não tem permissão para usar este comando.")

# Error handlers para comandos slash
@setup_registration_slash.error
@registration_stats_slash.error
@export_registrations_slash.error
async def slash_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.MissingPermissions):
        if not interaction.response.is_done():
            await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
        else:
            await interaction.followup.send("Você não tem permissão para usar este comando.", ephemeral=True)

# Executar o bot
if __name__ == "__main__":
    try:
        bot.run(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("Bot desconectado.")
    except Exception as e:
        print(f"Erro ao executar o bot: {e}")