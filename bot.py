import discord
from discord.ext import commands
import asyncio
import config
from database.db import create_tables, DatabaseManager
from views.mentoria_view import MentoriaRequestView
from views.team_view import TeamRequestView
from handlers.mentoria_handler import MentoriaHandler
from handlers.team_handler import TeamHandler
from handlers.voice_handler import VoiceHandler
from utils.logger import get_logger, set_bot_instance

# Configurações do bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class MentoriaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='n!',
            intents=intents,
            description="Bot para solicitações de mentoria"
        )
        self.mentoria_handler = None
        self.team_handler = None
        self.voice_handler = None
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
            self.team_handler = TeamHandler(self)
            self.voice_handler = VoiceHandler(self)
            self.logger.info("Handlers inicializados")

            # Adicionar views persistentes
            self.add_view(MentoriaRequestView())
            self.add_view(TeamRequestView())
            self.logger.info("Views persistentes adicionadas")
            
            # Adicionar views de convites (serão recriadas dinamicamente quando necessário)
            # As views de convite são temporárias e não precisam ser persistentes
            
            self.logger.info(f'Bot configurado e pronto!')
            
        except Exception as e:
            self.logger.error("Erro crítico durante inicialização do bot", exc_info=e)

    async def on_ready(self):
        """Evento executado quando o bot fica online"""
        self.logger.info(f'Bot conectado como {self.user.name} (ID: {self.user.id})')

        # Configurar atividade do bot
        activity = discord.Activity(type=discord.ActivityType.watching, name="mentores e estudantes | n!ajuda")
        await self.change_presence(activity=activity, status=discord.Status.online)

        # Configurar logger para Discord (agora que o bot está online)
        set_bot_instance(self)

        # Sincronizar comandos slash
        try:
            synced = await self.tree.sync()
            self.logger.info(f'Sincronizados {len(synced)} comando(s) slash')
        except Exception as e:
            self.logger.error('Erro ao sincronizar comandos slash', exc_info=e)

        # Limpar canais e enviar painéis
        await self.setup_channels_and_panels()

        # Iniciar limpeza periódica de canais de voz
        if self.voice_handler:
            self.loop.create_task(self.periodic_voice_cleanup())

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

        # Processar respostas do formulário de criação de equipes
        if self.team_handler:
            await self.team_handler.process_team_creation(message)

        # Processar comandos
        await self.process_commands(message)

    async def on_voice_state_update(self, member, before, after):
        """Processa mudanças de estado de voz"""
        # Processar sistema de canais temporários
        if self.voice_handler:
            await self.voice_handler.handle_voice_state_update(member, before, after)

    async def on_command_error(self, ctx, error):
        """Trata erros de comandos de prefixo"""
        if isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                title="❌ Comando não encontrado",
                description=f"O comando `{ctx.invoked_with}` não existe.\n\nUse `n!ajuda` para ver todos os comandos disponíveis.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)
            return

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


    async def periodic_voice_cleanup(self):
        """Limpeza periódica de canais de voz temporários"""
        while not self.is_closed():
            try:
                await asyncio.sleep(300)  # A cada 5 minutos
                if self.voice_handler:
                    await self.voice_handler.cleanup_abandoned_channels()
            except Exception as e:
                self.logger.error("Erro na limpeza periódica de canais de voz", exc_info=e)
                await asyncio.sleep(60)  # Aguardar 1 minuto antes de tentar novamente

    async def setup_channels_and_panels(self):
        """Limpa canais e envia painéis no startup"""
        try:
            # IDs dos canais
            team_channel_id = 1421842573760135268      # Canal de criação de equipes
            mentoria_channel_id = 1404479492814016703  # Canal de mentoria
            announcements_channel_id = 1421850940767473715  # Canal de anúncios

            # Buscar canais
            team_channel = self.get_channel(team_channel_id)
            mentoria_channel = self.get_channel(mentoria_channel_id)
            announcements_channel = self.get_channel(announcements_channel_id)

            channels_cleaned = 0

            # Limpar canal de equipes
            if team_channel:
                try:
                    deleted_messages = await team_channel.purge(limit=None)
                    channels_cleaned += 1
                    self.logger.info(f"Canal de equipes limpo: {len(deleted_messages)} mensagens removidas")
                except Exception as e:
                    self.logger.error(f"Erro ao limpar canal de equipes", exc_info=e)

            # Limpar canal de mentoria
            if mentoria_channel:
                try:
                    deleted_messages = await mentoria_channel.purge(limit=None)
                    channels_cleaned += 1
                    self.logger.info(f"Canal de mentoria limpo: {len(deleted_messages)} mensagens removidas")
                except Exception as e:
                    self.logger.error(f"Erro ao limpar canal de mentoria", exc_info=e)

            # Aguardar um pouco para evitar rate limits
            await asyncio.sleep(2)

            # Enviar painel de mentoria
            if mentoria_channel:
                await self.send_mentoria_panel(mentoria_channel)

            # Enviar painel de equipes
            if team_channel:
                await self.send_team_panel_to_channel(team_channel)

            # Enviar notificação de novidades
            if announcements_channel:
                await self.send_updates_announcement(announcements_channel, channels_cleaned)

        except Exception as e:
            self.logger.error("Erro no setup de canais e painéis", exc_info=e)

    async def send_mentoria_panel(self, channel):
        """Envia o painel de mentoria para um canal específico"""
        try:
            embed = discord.Embed(
                title="🎓 Sistema de Mentoria",
                description="""**Bem-vindo ao sistema de solicitação de mentoria!**

Aqui você pode solicitar ajuda de mentores experientes em diversas áreas do conhecimento.

**🎯 Como funciona:**
• Clique no botão abaixo para solicitar ajuda
• Preencha o formulário com sua dúvida
• Os mentores serão notificados
• Um mentor assumirá sua solicitação
• Você receberá ajuda personalizada!

**📚 Áreas disponíveis:**
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
            embed.set_thumbnail(url=channel.guild.icon.url if channel.guild.icon else None)

            view = MentoriaRequestView()
            await channel.send(embed=embed, view=view)

            self.logger.info(f"Painel de mentoria enviado para o canal {channel.id}")

        except Exception as e:
            self.logger.error("Erro ao enviar painel de mentoria", exc_info=e)

    async def send_team_panel_to_channel(self, channel):
        """Envia o painel de equipes para um canal específico"""
        try:
            # Criar embed do painel
            embed = discord.Embed(
                title="🏆 Sistema de Equipes",
                description="""**Bem-vindo ao sistema de criação de equipes!**

Aqui você pode criar sua própria equipe e liderar projetos incríveis com outros membros da comunidade.

**🎯 Como funciona:**
• Clique no botão abaixo para criar sua equipe
• Preencha um formulário simples de 3 passos
• Escolha seu desafio do NASA Space Apps Challenge
• Receba canais exclusivos e role da equipe
• Ganhe um canal privado de liderança
• Adicione até 5 membros à sua equipe

**📋 O que você ganha:**
• 💬 Canal de texto exclusivo da equipe
• 🔊 Canal de voz para reuniões
• 👑 Canal privado de liderança
• 🏷️ Role colorida da equipe
• 🎮 Controle total sobre membros

**⚡ Recursos do líder:**
• Adicionar/remover membros (máximo 6 total)
• Editar informações da equipe
• Gerenciar a equipe completamente
• Canal privado só para você

**🎨 Categorias disponíveis:**
• 💻 Programação & Desenvolvimento
• 🎨 Design & Criatividade
• 📊 Dados & Analytics
• 🎮 Jogos & Entretenimento
• 🔬 Ciência & Pesquisa
• 💼 Negócios & Empreendedorismo
• 🎓 Educação & Ensino
• 🌐 Geral & Outros

Clique no botão abaixo para criar sua equipe!""",
                color=discord.Color.gold()
            )

            embed.add_field(
                name="👑 Para quem é?",
                value="Qualquer membro pode criar e liderar uma equipe. Ideal para projetos, estudos em grupo, ou iniciativas colaborativas.",
                inline=False
            )

            embed.add_field(
                name="📊 Limite",
                value="• Cada usuário pode liderar apenas **1 equipe**\n• Cada equipe pode ter no máximo **6 membros** (incluindo o líder)\n• Processo 100% automatizado",
                inline=False
            )

            embed.set_footer(text="Sistema de Equipes | Crie a sua agora!")
            embed.set_thumbnail(url=channel.guild.icon.url if channel.guild.icon else None)

            view = TeamRequestView()
            await channel.send(embed=embed, view=view)

            self.logger.info(f"Painel de equipes enviado para o canal {channel.id}")

        except Exception as e:
            self.logger.error("Erro ao enviar painel de equipes", exc_info=e)

    async def send_updates_announcement(self, channel, channels_cleaned):
        """Envia anúncio de atualizações do bot"""
        try:
            embed = discord.Embed(
                title="🤖 Bot Atualizado e Online!",
                description=f"""@everyone **O bot foi atualizado e está online novamente!**

**🧹 Limpeza Automática:**
• {channels_cleaned} canal(is) foi(ram) limpo(s) e reorganizado(s)
• Painéis atualizados e funcionando perfeitamente

**🆕 NOVIDADE: Sistema de Equipes**
Agora você pode criar e liderar sua própria equipe!

**🎯 Como funciona o Sistema de Equipes:**
• Clique no botão "Criar Equipe" no canal correspondente
• Preencha um formulário rápido de 3 passos
• Receba automaticamente:
  - 💬 Canal de texto exclusivo
  - 🔊 Canal de voz privado
  - 👑 Canal de liderança (só para você)
  - 🏷️ Role colorida da equipe

**👑 Como Líder você pode:**
• Adicionar até 5 membros (6 total incluindo você)
• Remover membros da equipe
• Editar informações da equipe
• Gerenciar permissões e configurações
• Ter controle total sobre os canais

**🎮 Outras Funcionalidades:**
• Sistema de mentoria aprimorado
• Canais de voz temporários automáticos
• Comandos de administração melhorados

**🔧 Sistemas Ativos:**
✅ Sistema de Mentoria
✅ Sistema de Equipes (NOVO!)
✅ Canais de Voz Temporários
✅ Comandos Administrativos
✅ Logging Avançado""",
                color=discord.Color.green()
            )

            embed.add_field(
                name="📍 Onde Encontrar",
                value="""
                🎓 **Mentoria:** <#1404479492814016703>
                🏆 **Equipes:** <#1421842573760135268>
                🔊 **Canais Temporários:** Entre no canal trigger de voz
                """,
                inline=False
            )

            embed.add_field(
                name="💡 Dicas",
                value="""
                • Use `n!ajuda` para ver todos os comandos
                • Cada usuário pode liderar apenas 1 equipe
                • Equipes podem ter até 6 membros
                • Canais de voz temporários são criados automaticamente
                • O líder tem controle total sobre sua equipe
                """,
                inline=False
            )

            embed.set_footer(text=f"Bot Online • Sistema atualizado em {discord.utils.utcnow().strftime('%d/%m/%Y às %H:%M')} UTC")
            embed.set_thumbnail(url=channel.guild.icon.url if channel.guild.icon else None)

            await channel.send(embed=embed)

            self.logger.info(f"Anúncio de atualizações enviado para o canal {channel.id}")

        except Exception as e:
            self.logger.error("Erro ao enviar anúncio de atualizações", exc_info=e)

# Instância do bot
bot = MentoriaBot()

@bot.command(name='ajuda', aliases=['comandos'])
async def help_command(ctx):
    """Mostra todos os comandos disponíveis"""
    embed = discord.Embed(
        title="🤖 Comandos do Bot de Mentoria",
        description="Aqui estão todos os comandos disponíveis:",
        color=discord.Color.blue()
    )

    # Comandos para usuários
    embed.add_field(
        name="👥 Comandos para Usuários",
        value="""
        `n!ajuda` - Mostra esta mensagem de ajuda
        `n!info_equipe` - Ver informações sobre uma equipe
        `n!listar_equipes` - Listar todas as equipes do servidor
        """,
        inline=False
    )

    # Comandos para mentores
    embed.add_field(
        name="🎓 Comandos para Mentores",
        value="""
        `/solicitacoes` - Ver solicitações pendentes (apenas mentores)
        """,
        inline=False
    )

    # Comandos administrativos
    embed.add_field(
        name="⚙️ Comandos Administrativos",
        value="""
        `n!setup` ou `/setup` - Configurar painel de mentoria
        `n!stats` ou `/stats` - Ver estatísticas de mentoria
        `n!export` ou `/export` - Exportar relatório de solicitações
        `n!clear` ou `/clear` - Limpar mensagens do chat
        `n!setup_equipes` - Configurar painel de equipes
        `n!canais_temp` - Listar canais de voz temporários
        `n!limpar_canais` - Forçar limpeza de canais vazios
        `n!remover_canal_usuario` - Remover canais de um usuário
        """,
        inline=False
    )

    # Comandos slash
    embed.add_field(
        name="⚡ Comandos Slash",
        value="""
        Você também pode usar comandos slash digitando `/` e escolhendo o comando:
        • `/setup` - Configurar painel
        • `/stats` - Ver estatísticas
        • `/export` - Exportar dados
        • `/clear` - Limpar mensagens
        • `/solicitacoes` - Ver solicitações (mentores)
        • `/ajuda` - Esta mensagem de ajuda
        """,
        inline=False
    )

    embed.add_field(
        name="🎯 Como Solicitar Mentoria",
        value="Use o botão **'Solicitar Ajuda'** no painel de mentoria para enviar uma solicitação.",
        inline=False
    )

    embed.set_footer(text="Bot de Mentoria | Use n! como prefixo para comandos")

    await ctx.send(embed=embed)

@bot.command(name='setup_equipes', aliases=['setup_teams'])
@commands.has_permissions(administrator=True)
async def setup_equipes(ctx):
    """Comando para configurar o painel de equipes"""
    await bot.send_team_panel()
    await ctx.send("✅ Painel de equipes configurado!")

@bot.command(name='info_equipe', aliases=['equipe_info'])
async def info_equipe(ctx, *, nome_equipe: str = None):
    """Mostra informações sobre uma equipe"""
    try:
        guild = ctx.guild

        # Se não especificou a equipe, tentar detectar pelo canal atual
        if not nome_equipe:
            if ctx.channel.category and ctx.channel.category.name == "🏆 EQUIPES":
                channel_name = ctx.channel.name.replace("💬│", "").replace("🔊│", "")
                team_role = None
                for role in guild.roles:
                    if role.name.startswith("Equipe "):
                        team_name_clean = ''.join(c for c in role.name.replace("Equipe ", "").lower() if c.isalnum() or c in ['-', '_']).replace(' ', '-')
                        if team_name_clean == channel_name:
                            team_role = role
                            nome_equipe = role.name.replace("Equipe ", "")
                            break
            else:
                await ctx.send("❌ Especifique o nome da equipe ou use este comando em um canal de equipe!")
                return
        else:
            team_role = discord.utils.get(guild.roles, name=f"Equipe {nome_equipe}")

        if not team_role:
            await ctx.send(f"❌ Equipe '{nome_equipe}' não encontrada!")
            return

        # Buscar role de líder
        leader_role = discord.utils.get(guild.roles, name=f"Líder {nome_equipe}")
        leader = None
        if leader_role:
            leader_members = [member for member in guild.members if leader_role in member.roles]
            if leader_members:
                leader = leader_members[0]

        # Buscar canais da equipe
        category = discord.utils.get(guild.categories, name="🏆 EQUIPES")
        text_channel = None
        voice_channel = None

        if category:
            nome_limpo = ''.join(c for c in nome_equipe.lower() if c.isalnum() or c in ['-', '_']).replace(' ', '-')
            text_channel = discord.utils.get(category.text_channels, name=f"💬│{nome_limpo}")
            voice_channel = discord.utils.get(category.voice_channels, name=f"🔊│{nome_limpo}")

        # Listar membros
        members = [member for member in guild.members if team_role in member.roles]

        embed = discord.Embed(
            title=f"📋 Informações da Equipe {nome_equipe}",
            color=team_role.color
        )

        embed.add_field(
            name="🏷️ Role",
            value=team_role.mention,
            inline=True
        )

        embed.add_field(
            name="👥 Membros",
            value=f"{len(members)}/6",
            inline=True
        )

        if leader:
            embed.add_field(
                name="👑 Líder",
                value=leader.mention,
                inline=True
            )

        if text_channel:
            embed.add_field(
                name="💬 Canal de Texto",
                value=text_channel.mention,
                inline=True
            )

        if voice_channel:
            embed.add_field(
                name="🔊 Canal de Voz",
                value=voice_channel.mention,
                inline=True
            )

        # Listar membros
        if members:
            members_list = []
            for member in members:
                if leader_role and leader_role in member.roles:
                    members_list.append(f"👑 {member.display_name} (Líder)")
                else:
                    status_emoji = "🟢" if member.status == discord.Status.online else "🟠" if member.status == discord.Status.idle else "🔴" if member.status == discord.Status.dnd else "⚫"
                    members_list.append(f"{status_emoji} {member.display_name}")

            embed.add_field(
                name="👥 Lista de Membros",
                value="\n".join(members_list),
                inline=False
            )

        embed.set_footer(text=f"Criada em: {team_role.created_at.strftime('%d/%m/%Y às %H:%M')}")

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao buscar informações da equipe: {str(e)}")

@bot.command(name='listar_equipes', aliases=['list_equipes'])
async def listar_equipes(ctx):
    """Lista todas as equipes existentes no servidor"""
    try:
        guild = ctx.guild
        team_roles = [role for role in guild.roles if role.name.startswith("Equipe ")]

        if not team_roles:
            embed = discord.Embed(
                title="📭 Nenhuma Equipe Encontrada",
                description="Não há equipes criadas neste servidor.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="🏆 Equipes do Servidor",
            description=f"Total de {len(team_roles)} equipe(s) encontrada(s):",
            color=discord.Color.blue()
        )

        teams_info = []
        for role in team_roles:
            team_name = role.name.replace("Equipe ", "")
            member_count = len([member for member in guild.members if role in member.roles])

            # Buscar líder
            leader_role = discord.utils.get(guild.roles, name=f"Líder {team_name}")
            leader_name = "Sem líder"
            if leader_role:
                leader_members = [m for m in guild.members if leader_role in m.roles]
                if leader_members:
                    leader_name = leader_members[0].display_name

            teams_info.append(f"🏷️ **{team_name}** - {member_count}/6 membros - Líder: {leader_name}")

        # Dividir em grupos de 8 para não exceder limite do embed
        for i in range(0, len(teams_info), 8):
            chunk = teams_info[i:i+8]
            embed.add_field(
                name=f"Equipes {i+1}-{min(i+8, len(teams_info))}",
                value="\n".join(chunk),
                inline=False
            )

        embed.set_footer(text="Use n!info_equipe <nome> para mais detalhes sobre uma equipe específica")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao listar equipes: {str(e)}")

@bot.command(name='canais_temp', aliases=['temp_channels'])
@commands.has_permissions(administrator=True)
async def listar_canais_temp(ctx):
    """Lista todos os canais de voz temporários ativos"""
    try:
        if not bot.voice_handler:
            await ctx.send("❌ Sistema de canais temporários não está ativo.")
            return

        channels_info = bot.voice_handler.get_temp_channels_info()

        if not channels_info:
            embed = discord.Embed(
                title="📭 Nenhum Canal Temporário",
                description="Não há canais de voz temporários ativos no momento.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="🔊 Canais de Voz Temporários",
            description=f"Total de {len(channels_info)} canal(is) temporário(s) ativo(s):",
            color=discord.Color.blue()
        )

        for i, info in enumerate(channels_info, 1):
            channel = info['channel']
            creator = info['creator']
            member_count = info['member_count']
            members = info['members']

            members_text = ", ".join(members) if members else "Vazio"
            if len(members_text) > 100:
                members_text = members_text[:100] + "..."

            embed.add_field(
                name=f"{i}. {channel.name}",
                value=f"""
                **Criador:** {creator}
                **Membros:** {member_count}
                **Usuários:** {members_text}
                **ID:** {channel.id}
                """,
                inline=False
            )

        embed.set_footer(text="Use n!limpar_canais para remover canais vazios")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao listar canais temporários: {str(e)}")

@bot.command(name='limpar_canais', aliases=['cleanup_voice'])
@commands.has_permissions(administrator=True)
async def limpar_canais_temp(ctx):
    """Força a limpeza de canais temporários vazios"""
    try:
        if not bot.voice_handler:
            await ctx.send("❌ Sistema de canais temporários não está ativo.")
            return

        # Executar limpeza
        channels_before = len(bot.voice_handler.temp_channels)
        await bot.voice_handler.cleanup_abandoned_channels()
        channels_after = len(bot.voice_handler.temp_channels)

        cleaned = channels_before - channels_after

        embed = discord.Embed(
            title="🧹 Limpeza de Canais Concluída",
            description=f"""
            **Canais antes da limpeza:** {channels_before}
            **Canais após limpeza:** {channels_after}
            **Canais removidos:** {cleaned}
            """,
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao limpar canais temporários: {str(e)}")

@bot.command(name='remover_canal_usuario', aliases=['remove_user_channels'])
@commands.has_permissions(administrator=True)
async def remover_canais_usuario(ctx, user: discord.Member):
    """Remove todos os canais temporários de um usuário específico"""
    try:
        if not bot.voice_handler:
            await ctx.send("❌ Sistema de canais temporários não está ativo.")
            return

        # Contar canais do usuário antes da remoção
        user_channels = 0
        for channel_id, creator_id in bot.voice_handler.channel_creators.items():
            if creator_id == user.id:
                user_channels += 1

        if user_channels == 0:
            await ctx.send(f"❌ {user.mention} não possui canais temporários ativos.")
            return

        # Remover canais do usuário
        await bot.voice_handler.force_cleanup_user_channels(user.id)

        embed = discord.Embed(
            title="🗑️ Canais Removidos",
            description=f"Removidos {user_channels} canal(is) temporário(s) de {user.mention}.",
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao remover canais do usuário: {str(e)}")

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

# Comando para limpar mensagens do chat
@bot.command(name='clear')
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    """Comando para limpar mensagens do chat"""
    try:
        if amount <= 0:
            await ctx.send("❌ Quantidade deve ser maior que 0.", delete_after=5)
            return
        
        if amount > 100:
            await ctx.send("❌ Máximo de 100 mensagens por vez.", delete_after=5)
            return
        
        # Deletar a mensagem do comando primeiro
        await ctx.message.delete()
        
        # Deletar as mensagens
        deleted = await ctx.channel.purge(limit=amount)
        
        # Enviar confirmação que será deletada após 5 segundos
        confirmation = await ctx.send(f"🗑️ **{len(deleted)}** mensagens foram removidas.")
        await asyncio.sleep(3)
        await confirmation.delete()
        
        bot.logger.info(f"Usuário {ctx.author.id} ({ctx.author.name}) limpou {len(deleted)} mensagens no canal {ctx.channel.name}")
        
    except discord.Forbidden:
        await ctx.send("❌ Não tenho permissão para deletar mensagens neste canal.", delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Erro ao limpar mensagens: {str(e)}", delete_after=5)
        bot.logger.error(f"Erro ao limpar mensagens no canal {ctx.channel.name}", exc_info=e)

# Comando slash para limpar mensagens
@bot.tree.command(name='clear', description='Limpar mensagens do chat')
@discord.app_commands.describe(amount="Número de mensagens para limpar (padrão: 10, máximo: 100)")
@discord.app_commands.default_permissions(manage_messages=True)
async def clear_messages_slash(interaction: discord.Interaction, amount: int = 10):
    """Comando slash para limpar mensagens do chat"""
    try:
        if amount <= 0:
            await interaction.response.send_message("❌ Quantidade deve ser maior que 0.", ephemeral=True)
            return
        
        if amount > 100:
            await interaction.response.send_message("❌ Máximo de 100 mensagens por vez.", ephemeral=True)
            return
        
        # Deletar as mensagens
        deleted = await interaction.channel.purge(limit=amount)
        
        # Responder com confirmação
        await interaction.response.send_message(f"🗑️ **{len(deleted)}** mensagens foram removidas.", ephemeral=True)
        
        bot.logger.info(f"Usuário {interaction.user.id} ({interaction.user.name}) limpou {len(deleted)} mensagens no canal {interaction.channel.name}")
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ Não tenho permissão para deletar mensagens neste canal.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao limpar mensagens: {str(e)}", ephemeral=True)
        bot.logger.error(f"Erro ao limpar mensagens no canal {interaction.channel.name}", exc_info=e)

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

# Comando slash para ajuda
@bot.tree.command(name='ajuda', description='Mostrar todos os comandos disponíveis')
async def help_command_slash(interaction: discord.Interaction):
    """Comando slash para mostrar ajuda"""
    embed = discord.Embed(
        title="🤖 Comandos do Bot de Mentoria",
        description="Aqui estão todos os comandos disponíveis:",
        color=discord.Color.blue()
    )

    # Comandos para usuários
    embed.add_field(
        name="👥 Comandos para Usuários",
        value="""
        `n!ajuda` ou `/ajuda` - Mostra esta mensagem de ajuda
        """,
        inline=False
    )

    # Comandos para mentores
    embed.add_field(
        name="🎓 Comandos para Mentores",
        value="""
        `/solicitacoes` - Ver solicitações pendentes (apenas mentores)
        """,
        inline=False
    )

    # Comandos administrativos
    embed.add_field(
        name="⚙️ Comandos Administrativos",
        value="""
        `n!setup` ou `/setup` - Configurar painel de mentoria
        `n!stats` ou `/stats` - Ver estatísticas de mentoria
        `n!export` ou `/export` - Exportar relatório de solicitações
        `n!clear` ou `/clear` - Limpar mensagens do chat
        """,
        inline=False
    )

    # Comandos slash
    embed.add_field(
        name="⚡ Comandos Slash",
        value="""
        Você também pode usar comandos slash digitando `/` e escolhendo o comando:
        • `/setup` - Configurar painel
        • `/stats` - Ver estatísticas
        • `/export` - Exportar dados
        • `/clear` - Limpar mensagens
        • `/solicitacoes` - Ver solicitações (mentores)
        • `/ajuda` - Esta mensagem de ajuda
        """,
        inline=False
    )

    embed.add_field(
        name="🎯 Como Solicitar Mentoria",
        value="Use o botão **'Solicitar Ajuda'** no painel de mentoria para enviar uma solicitação.",
        inline=False
    )

    embed.set_footer(text="Bot de Mentoria | Use n! como prefixo para comandos")

    await interaction.response.send_message(embed=embed, ephemeral=True)




# Error handlers para comandos de prefixo
@help_command.error
@setup_equipes.error
@info_equipe.error
@listar_canais_temp.error
@limpar_canais_temp.error
@remover_canais_usuario.error
@setup_mentoria.error
@mentoria_stats.error
@export_solicitacoes.error
@clear_messages.error
async def command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Você não tem permissão para usar este comando.")

# Error handlers para comandos slash
@help_command_slash.error
@setup_mentoria_slash.error
@mentoria_stats_slash.error
@export_solicitacoes_slash.error
@list_solicitacoes.error
@clear_messages_slash.error
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