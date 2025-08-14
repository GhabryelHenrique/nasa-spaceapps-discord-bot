import discord
from discord.ext import commands
import asyncio
import config
from database.db import create_tables, DatabaseManager
from views.mentoria_view import MentoriaRequestView
from handlers.mentoria_handler import MentoriaHandler
from utils.logger import get_logger, set_bot_instance

# Configurações do bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class MentoriaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            description="Bot para solicitações de mentoria"
        )
        self.mentoria_handler = None
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
            self.mentoria_handler = MentoriaHandler(self)
            self.logger.info("Handlers inicializados")
            
            # Adicionar views persistentes
            self.add_view(MentoriaRequestView())
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
        
        # Processar respostas do formulário de mentoria
        if self.mentoria_handler:
            print(f"Processando resposta do formulário de mentoria para usuário {message.author.id}")
            await self.mentoria_handler.process_mentoria_answer(message)
        
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
bot = MentoriaBot()

@bot.command(name='setup')
@commands.has_permissions(administrator=True)
async def setup_mentoria(ctx):
    """Comando para configurar o painel de mentoria"""
    embed = discord.Embed(
        title="🎓 Sistema de Mentoria",
        description="""**Bem-vindo ao sistema de solicitação de mentoria!**

Aqui você pode solicitar ajuda de mentores experientes em diversas áreas do conhecimento.

**Como funciona:**
• Clique no botão abaixo para solicitar ajuda
• Preencha o formulário com sua dúvida
• Os mentores serão notificados
• Um mentor assumirá sua solicitação
• Você receberá ajuda personalizada!

**Áreas disponíveis:**
• Programação (Python, JavaScript, Java, C++, etc.)
• Desenvolvimento Web e Mobile
• Ciência de Dados e Machine Learning
• Design e UX/UI
• DevOps e Cloud Computing
• E muito mais!

Clique no botão abaixo para solicitar mentoria!""",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎯 Para quem é?",
        value="Estudantes, profissionais iniciantes, e qualquer pessoa que precise de orientação técnica.",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Resposta rápida",
        value="Nossos mentores se comprometem a responder rapidamente baseado na urgência da sua solicitação.",
        inline=False
    )
    
    embed.set_footer(text="Sistema de Mentoria | Solicite ajuda quando precisar!")
    
    view = MentoriaRequestView()
    await ctx.send(embed=embed, view=view)

@bot.command(name='stats')
@commands.has_permissions(administrator=True)
async def mentoria_stats(ctx):
    """Mostra estatísticas das solicitações de mentoria"""
    try:
        from sqlalchemy import func, select
        from database.models import SolicitacaoMentoria, StatusSolicitacaoEnum
        
        async with await DatabaseManager.get_session() as session:
            # Total de solicitações
            total_result = await session.execute(select(func.count(SolicitacaoMentoria.id)))
            total = total_result.scalar()
            
            # Por status
            status_result = await session.execute(
                select(SolicitacaoMentoria.status, func.count(SolicitacaoMentoria.id))
                .group_by(SolicitacaoMentoria.status)
            )
            status_counts = status_result.fetchall()
            
            # Por área de conhecimento
            area_result = await session.execute(
                select(SolicitacaoMentoria.area_conhecimento, func.count(SolicitacaoMentoria.id))
                .group_by(SolicitacaoMentoria.area_conhecimento)
                .order_by(func.count(SolicitacaoMentoria.id).desc())
                .limit(5)
            )
            areas = area_result.fetchall()
            
            # Por urgência
            urgencia_result = await session.execute(
                select(SolicitacaoMentoria.nivel_urgencia, func.count(SolicitacaoMentoria.id))
                .group_by(SolicitacaoMentoria.nivel_urgencia)
            )
            urgencias = urgencia_result.fetchall()
        
        embed = discord.Embed(
            title="📊 Estatísticas de Mentoria",
            description=f"**Total de Solicitações:** {total}",
            color=discord.Color.green()
        )
        
        # Status
        status_text = ""
        status_emojis = {
            'Pendente': '⏳',
            'Em Andamento': '🔄',
            'Concluída': '✅',
            'Cancelada': '❌'
        }
        for status, count in status_counts:
            emoji = status_emojis.get(status.value, '📝')
            status_text += f"{emoji} {status.value}: {count}\n"
        
        if status_text:
            embed.add_field(name="Por Status", value=status_text, inline=True)
        
        # Áreas mais solicitadas
        if areas:
            area_text = ""
            for area, count in areas:
                area_text += f"• {area}: {count}\n"
            embed.add_field(name="Top 5 Áreas", value=area_text, inline=True)
        
        # Por urgência
        if urgencias:
            urgencia_text = ""
            urgencia_emojis = {
                'Baixa': '🟢',
                'Média': '🟡',
                'Alta': '🔴'
            }
            for urgencia, count in urgencias:
                emoji = urgencia_emojis.get(urgencia, '⚪')
                urgencia_text += f"{emoji} {urgencia}: {count}\n"
            embed.add_field(name="Por Urgência", value=urgencia_text, inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"Erro ao buscar estatísticas: {str(e)}")

@bot.command(name='export')
@commands.has_permissions(administrator=True)
async def export_solicitacoes(ctx):
    """Exporta lista de solicitações de mentoria em formato texto"""
    try:
        from database.models import SolicitacaoMentoria
        from sqlalchemy import select
        
        async with await DatabaseManager.get_session() as session:
            result = await session.execute(select(SolicitacaoMentoria).order_by(SolicitacaoMentoria.data_solicitacao))
            solicitacoes = result.scalars().all()
        
        if not solicitacoes:
            await ctx.send("Nenhuma solicitação encontrada.")
            return
        
        # Criar arquivo texto
        content = "RELATÓRIO DE SOLICITAÇÕES DE MENTORIA\n"
        content += "=" * 50 + "\n\n"
        
        for i, s in enumerate(solicitacoes, 1):
            content += f"{i:03d}. {s.titulo}\n"
            content += f"     Solicitante: {s.discord_username}\n"
            content += f"     Área: {s.area_conhecimento}\n"
            content += f"     Urgência: {s.nivel_urgencia}\n"
            content += f"     Status: {s.status.value}\n"
            if s.mentor_username:
                content += f"     Mentor: {s.mentor_username}\n"
            content += f"     Data: {s.data_solicitacao.strftime('%d/%m/%Y %H:%M')}\n"
            content += f"     Descrição: {s.descricao[:100]}{'...' if len(s.descricao) > 100 else ''}\n"
            content += "-" * 40 + "\n"
        
        content += f"\nTotal: {len(solicitacoes)} solicitações"
        
        # Salvar em arquivo
        with open("solicitacoes_mentoria.txt", "w", encoding="utf-8") as f:
            f.write(content)
        
        # Enviar arquivo
        file = discord.File("solicitacoes_mentoria.txt")
        await ctx.send("Relatório de solicitações:", file=file)
        
    except Exception as e:
        await ctx.send(f"Erro ao exportar dados: {str(e)}")

# Versões slash dos comandos
@bot.tree.command(name='setup', description='Configurar o painel de mentoria')
@discord.app_commands.default_permissions(administrator=True)
async def setup_mentoria_slash(interaction: discord.Interaction):
    """Comando slash para configurar o painel de mentoria"""
    embed = discord.Embed(
        title="🎓 Sistema de Mentoria",
        description="""**Bem-vindo ao sistema de solicitação de mentoria!**

Aqui você pode solicitar ajuda de mentores experientes em diversas áreas do conhecimento.

**Como funciona:**
• Clique no botão abaixo para solicitar ajuda
• Preencha o formulário com sua dúvida
• Os mentores serão notificados
• Um mentor assumirá sua solicitação
• Você receberá ajuda personalizada!

**Áreas disponíveis:**
• Programação (Python, JavaScript, Java, C++, etc.)
• Desenvolvimento Web e Mobile
• Ciência de Dados e Machine Learning
• Design e UX/UI
• DevOps e Cloud Computing
• E muito mais!

Clique no botão abaixo para solicitar mentoria!""",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎯 Para quem é?",
        value="Estudantes, profissionais iniciantes, e qualquer pessoa que precise de orientação técnica.",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Resposta rápida",
        value="Nossos mentores se comprometem a responder rapidamente baseado na urgência da sua solicitação.",
        inline=False
    )
    
    embed.set_footer(text="Sistema de Mentoria | Solicite ajuda quando precisar!")
    
    view = MentoriaRequestView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='stats', description='Mostrar estatísticas de mentoria')
@discord.app_commands.default_permissions(administrator=True)
async def mentoria_stats_slash(interaction: discord.Interaction):
    """Comando slash para mostrar estatísticas de mentoria"""
    try:
        from sqlalchemy import func, select
        from database.models import SolicitacaoMentoria, StatusSolicitacaoEnum
        
        async with await DatabaseManager.get_session() as session:
            # Total de solicitações
            total_result = await session.execute(select(func.count(SolicitacaoMentoria.id)))
            total = total_result.scalar()
            
            # Por status
            status_result = await session.execute(
                select(SolicitacaoMentoria.status, func.count(SolicitacaoMentoria.id))
                .group_by(SolicitacaoMentoria.status)
            )
            status_counts = status_result.fetchall()
            
            # Por área de conhecimento
            area_result = await session.execute(
                select(SolicitacaoMentoria.area_conhecimento, func.count(SolicitacaoMentoria.id))
                .group_by(SolicitacaoMentoria.area_conhecimento)
                .order_by(func.count(SolicitacaoMentoria.id).desc())
                .limit(5)
            )
            areas = area_result.fetchall()
        
        embed = discord.Embed(
            title="📊 Estatísticas de Mentoria",
            description=f"**Total de Solicitações:** {total}",
            color=discord.Color.green()
        )
        
        # Status
        status_text = ""
        status_emojis = {
            'Pendente': '⏳',
            'Em Andamento': '🔄',
            'Concluída': '✅',
            'Cancelada': '❌'
        }
        for status, count in status_counts:
            emoji = status_emojis.get(status.value, '📝')
            status_text += f"{emoji} {status.value}: {count}\n"
        
        if status_text:
            embed.add_field(name="Por Status", value=status_text, inline=True)
        
        # Áreas mais solicitadas
        if areas:
            area_text = ""
            for area, count in areas:
                area_text += f"• {area}: {count}\n"
            embed.add_field(name="Top 5 Áreas", value=area_text, inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"Erro ao buscar estatísticas: {str(e)}")

@bot.tree.command(name='export', description='Exportar relatório de solicitações de mentoria')
@discord.app_commands.default_permissions(administrator=True)
async def export_solicitacoes_slash(interaction: discord.Interaction):
    """Comando slash para exportar relatório de solicitações"""
    try:
        from database.models import SolicitacaoMentoria
        from sqlalchemy import select
        
        async with await DatabaseManager.get_session() as session:
            result = await session.execute(select(SolicitacaoMentoria).order_by(SolicitacaoMentoria.data_solicitacao))
            solicitacoes = result.scalars().all()
        
        if not solicitacoes:
            await interaction.response.send_message("Nenhuma solicitação encontrada.")
            return
        
        # Criar arquivo texto
        content = "RELATÓRIO DE SOLICITAÇÕES DE MENTORIA\n"
        content += "=" * 50 + "\n\n"
        
        for i, s in enumerate(solicitacoes, 1):
            content += f"{i:03d}. {s.titulo}\n"
            content += f"     Solicitante: {s.discord_username}\n"
            content += f"     Área: {s.area_conhecimento}\n"
            content += f"     Urgência: {s.nivel_urgencia}\n"
            content += f"     Status: {s.status.value}\n"
            if s.mentor_username:
                content += f"     Mentor: {s.mentor_username}\n"
            content += f"     Data: {s.data_solicitacao.strftime('%d/%m/%Y %H:%M')}\n"
            content += f"     Descrição: {s.descricao[:100]}{'...' if len(s.descricao) > 100 else ''}\n"
            content += "-" * 40 + "\n"
        
        content += f"\nTotal: {len(solicitacoes)} solicitações"
        
        # Salvar em arquivo
        with open("solicitacoes_mentoria.txt", "w", encoding="utf-8") as f:
            f.write(content)
        
        # Enviar arquivo
        file = discord.File("solicitacoes_mentoria.txt")
        await interaction.response.send_message("Relatório de solicitações:", file=file)
        
        # Limpar arquivo após envio
        import os
        try:
            os.remove("solicitacoes_mentoria.txt")
        except:
            pass
        
    except Exception as e:
        await interaction.response.send_message(f"Erro ao exportar dados: {str(e)}")

# Comando para listar solicitações pendentes (apenas mentores)
@bot.tree.command(name='solicitacoes', description='Ver solicitações de mentoria pendentes')
async def list_solicitacoes(interaction: discord.Interaction):
    """Lista solicitações pendentes para mentores"""
    try:
        # Verificar se usuário tem papel de mentor
        if not any(role.name.lower() == 'mentor' for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Apenas mentores podem usar este comando.",
                ephemeral=True
            )
            return
        
        from sqlalchemy import select
        from database.models import SolicitacaoMentoria, StatusSolicitacaoEnum
        
        async with await DatabaseManager.get_session() as session:
            result = await session.execute(
                select(SolicitacaoMentoria)
                .where(SolicitacaoMentoria.status == StatusSolicitacaoEnum.PENDENTE)
                .order_by(SolicitacaoMentoria.data_solicitacao.desc())
                .limit(10)
            )
            solicitacoes = result.scalars().all()
        
        if not solicitacoes:
            embed = discord.Embed(
                title="📭 Nenhuma Solicitação Pendente",
                description="Não há solicitações pendentes no momento.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 Solicitações Pendentes",
            description=f"**{len(solicitacoes)}** solicitação(ões) aguardando mentor",
            color=discord.Color.blue()
        )
        
        urgencia_emojis = {
            'Baixa': '🟢',
            'Média': '🟡',
            'Alta': '🔴'
        }
        
        for s in solicitacoes[:5]:
            urgencia_emoji = urgencia_emojis.get(s.nivel_urgencia, '⚪')
            
            field_value = f"**Solicitante:** {s.discord_username}\n"
            field_value += f"**Área:** {s.area_conhecimento}\n"
            field_value += f"**Urgência:** {urgencia_emoji} {s.nivel_urgencia}\n"
            field_value += f"**Data:** {s.data_solicitacao.strftime('%d/%m %H:%M')}\n"
            field_value += f"**Descrição:** {s.descricao[:100]}{'...' if len(s.descricao) > 100 else ''}"
            
            embed.add_field(
                name=f"#{s.id} - {s.titulo}",
                value=field_value,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(
            "❌ Erro ao buscar solicitações.",
            ephemeral=True
        )
        bot.logger.error(f"Erro ao listar solicitações", exc_info=e)



# Error handlers para comandos de prefixo
@setup_mentoria.error
@mentoria_stats.error
@export_solicitacoes.error
async def command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Você não tem permissão para usar este comando.")

# Error handlers para comandos slash
@setup_mentoria_slash.error
@mentoria_stats_slash.error
@export_solicitacoes_slash.error
@list_solicitacoes.error
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