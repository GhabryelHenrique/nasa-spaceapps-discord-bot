import discord
from typing import Optional, Dict
import asyncio

from database.db import DatabaseManager
from database.models import Participante, MatchmakingEquipe
from matchmaking.team_formation import TeamFormation


class TeamChannelManager:
    def __init__(self, bot):
        self.bot = bot
        self.db_manager = DatabaseManager()
        
        # Configurações dos canais
        self.CHANNEL_PREFIX = "🤖matchmaking-"
        self.CATEGORY_NAME = "🎯 MATCHMAKING DE EQUIPES"
        
    async def criar_categoria_matchmaking(self, guild: discord.Guild) -> discord.CategoryChannel:
        """
        Cria ou encontra a categoria para canais de matchmaking
        """
        # Procurar categoria existente
        for category in guild.categories:
            if category.name == self.CATEGORY_NAME:
                return category
        
        # Criar nova categoria
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                embed_links=True,
                add_reactions=True
            )
        }
        
        category = await guild.create_category(
            self.CATEGORY_NAME,
            overwrites=overwrites,
            reason="Sistema de matchmaking automático"
        )
        
        return category
    
    async def criar_canal_equipe(self, guild: discord.Guild, lider: Participante, nome_equipe: str) -> Optional[discord.TextChannel]:
        """
        Cria canal privado para o líder controlar matchmaking da equipe
        """
        try:
            # Buscar usuário no Discord
            lider_user = await self.bot.fetch_user(lider.discord_user_id)
            if not lider_user:
                return None
            
            # Buscar membro no servidor
            lider_member = guild.get_member(lider.discord_user_id)
            if not lider_member:
                return None
            
            # Criar/obter categoria
            category = await self.criar_categoria_matchmaking(guild)
            
            # Nome do canal (sanitizado)
            nome_canal = f"{self.CHANNEL_PREFIX}{nome_equipe.lower().replace(' ', '-')}"[:100]
            
            # Verificar se canal já existe
            existing_channel = discord.utils.get(guild.text_channels, name=nome_canal)
            if existing_channel:
                return existing_channel
            
            # Configurar permissões
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                lider_member: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    add_reactions=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True,
                    add_reactions=True
                )
            }
            
            # Criar canal
            canal = await guild.create_text_channel(
                nome_canal,
                category=category,
                overwrites=overwrites,
                topic=f"Painel de controle de matchmaking para a equipe {nome_equipe}",
                reason=f"Canal de matchmaking para equipe {nome_equipe}"
            )
            
            # Enviar mensagem inicial
            await self.enviar_painel_controle(canal, lider, nome_equipe)
            
            return canal
            
        except Exception as e:
            print(f"Erro ao criar canal para equipe {nome_equipe}: {e}")
            return None
    
    async def enviar_painel_controle(self, canal: discord.TextChannel, lider: Participante, nome_equipe: str):
        """
        Envia painel de controle do matchmaking no canal da equipe
        """
        embed = discord.Embed(
            title=f"🤖 Painel de Matchmaking - {nome_equipe}",
            description=f"""**Bem-vindo ao sistema de matchmaking automático!**

Olá, **{lider.nome}**! Este é o painel de controle da sua equipe.

**O que você pode fazer aqui:**
🟢 **Ativar Matchmaking** - Sistema encontra candidatos automaticamente
🔴 **Desativar Matchmaking** - Para de receber candidatos
⚙️ **Configurar Preferências** - Define habilidades procuradas
📊 **Ver Estatísticas** - Acompanha candidatos recebidos

**Como funciona:**
• Quando ativado, pessoas compatíveis aplicarão automaticamente
• Você receberá notificações via DM com perfis detalhados  
• Use `/aplicacoes` para gerenciar as candidaturas
• Sistema analisa habilidades, região e modalidade""",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Status Atual",
            value="🔴 **Matchmaking Desativado**\nClique em 'Ativar' para começar a receber candidatos.",
            inline=False
        )
        
        embed.add_field(
            name="👑 Líder da Equipe",
            value=f"{lider.nome} {lider.sobrenome}",
            inline=True
        )
        
        embed.add_field(
            name="📍 Localização",
            value=lider.cidade,
            inline=True
        )
        
        embed.add_field(
            name="💻 Modalidade",
            value=lider.modalidade.value,
            inline=True
        )
        
        embed.set_footer(text="Use os botões abaixo para controlar o matchmaking da sua equipe")
        
        view = TeamMatchmakingControlView(nome_equipe, lider.id)
        
        await canal.send(embed=embed, view=view)
    
    async def atualizar_painel_controle(self, canal: discord.TextChannel, nome_equipe: str, ativo: bool, config: Dict = None):
        """
        Atualiza o painel de controle com novo status
        """
        try:
            # Buscar mensagem do painel (primeira mensagem do bot no canal)
            async for message in canal.history(limit=50):
                if (message.author == self.bot.user and 
                    message.embeds and 
                    "Painel de Matchmaking" in message.embeds[0].title):
                    
                    embed = message.embeds[0]
                    
                    # Atualizar status
                    if ativo:
                        status_text = "🟢 **Matchmaking Ativado**\nSistema está procurando candidatos compatíveis."
                        embed.color = discord.Color.green()
                    else:
                        status_text = "🔴 **Matchmaking Desativado**\nClique em 'Ativar' para começar a receber candidatos."
                        embed.color = discord.Color.red()
                    
                    # Encontrar e atualizar campo de status
                    for i, field in enumerate(embed.fields):
                        if "Status Atual" in field.name:
                            embed.set_field_at(i, name="🎯 Status Atual", value=status_text, inline=False)
                            break
                    
                    # Adicionar configurações se fornecidas
                    if config and ativo:
                        config_text = ""
                        if config.get("habilidades_desejadas"):
                            config_text += f"**Habilidades:** {config['habilidades_desejadas'][:100]}\n"
                        if config.get("tamanho_maximo"):
                            config_text += f"**Tamanho Máximo:** {config['tamanho_maximo']} membros\n"
                        
                        # Verificar se já existe campo de configuração
                        config_field_exists = False
                        for i, field in enumerate(embed.fields):
                            if "Configuração" in field.name:
                                embed.set_field_at(i, name="⚙️ Configuração", value=config_text, inline=False)
                                config_field_exists = True
                                break
                        
                        if not config_field_exists and config_text:
                            embed.add_field(name="⚙️ Configuração", value=config_text, inline=False)
                    
                    view = TeamMatchmakingControlView(nome_equipe, None, ativo)
                    await message.edit(embed=embed, view=view)
                    break
                    
        except Exception as e:
            print(f"Erro ao atualizar painel de controle: {e}")
    
    async def obter_canal_equipe(self, guild: discord.Guild, nome_equipe: str) -> Optional[discord.TextChannel]:
        """
        Obtém o canal de matchmaking de uma equipe
        """
        nome_canal = f"{self.CHANNEL_PREFIX}{nome_equipe.lower().replace(' ', '-')}"[:100]
        return discord.utils.get(guild.text_channels, name=nome_canal)
    
    async def notificar_novo_candidato(self, guild: discord.Guild, nome_equipe: str, candidato_info: Dict):
        """
        Envia notificação no canal da equipe sobre novo candidato
        """
        try:
            canal = await self.obter_canal_equipe(guild, nome_equipe)
            if not canal:
                return
            
            embed = discord.Embed(
                title="👤 Novo Candidato via Matchmaking!",
                description=f"**{candidato_info['nome']}** aplicou automaticamente para sua equipe.",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="🎯 Score de Compatibilidade",
                value=f"**{candidato_info.get('score', 'N/A')}%**",
                inline=True
            )
            
            embed.add_field(
                name="📍 Localização",
                value=candidato_info.get("cidade", "N/A"),
                inline=True
            )
            
            embed.add_field(
                name="🎓 Escolaridade", 
                value=candidato_info.get("escolaridade", "N/A"),
                inline=True
            )
            
            if candidato_info.get("habilidades"):
                embed.add_field(
                    name="🛠️ Habilidades",
                    value=candidato_info["habilidades"][:200] + ("..." if len(candidato_info.get("habilidades", "")) > 200 else ""),
                    inline=False
                )
            
            embed.add_field(
                name="📬 Próximos Passos",
                value="• Você receberá um DM com detalhes completos\n• Use `/aplicacoes` para responder\n• Candidato aguarda sua decisão",
                inline=False
            )
            
            embed.set_footer(text="Sistema de Matchmaking Automático")
            
            await canal.send(embed=embed)
            
        except Exception as e:
            print(f"Erro ao notificar novo candidato: {e}")


class TeamMatchmakingControlView(discord.ui.View):
    def __init__(self, nome_equipe: str, lider_id: Optional[int], ativo: bool = False):
        super().__init__(timeout=None)
        self.nome_equipe = nome_equipe
        self.lider_id = lider_id
        self.ativo = ativo
        
        # Atualizar botões baseado no status
        self.update_buttons()
    
    def update_buttons(self):
        """Atualiza os botões baseado no status atual"""
        self.clear_items()
        
        if self.ativo:
            # Matchmaking ativo - mostrar botão de desativar
            desativar_btn = discord.ui.Button(
                label="🔴 Desativar Matchmaking",
                style=discord.ButtonStyle.danger,
                custom_id=f"matchmaking_toggle_{self.nome_equipe}"
            )
            desativar_btn.callback = self.desativar_matchmaking
            self.add_item(desativar_btn)
            
            # Botão de configurações
            config_btn = discord.ui.Button(
                label="⚙️ Configurar",
                style=discord.ButtonStyle.secondary,
                custom_id=f"matchmaking_config_{self.nome_equipe}"
            )
            config_btn.callback = self.configurar_matchmaking
            self.add_item(config_btn)
            
        else:
            # Matchmaking inativo - mostrar botão de ativar
            ativar_btn = discord.ui.Button(
                label="🟢 Ativar Matchmaking",
                style=discord.ButtonStyle.success,
                custom_id=f"matchmaking_toggle_{self.nome_equipe}"
            )
            ativar_btn.callback = self.ativar_matchmaking
            self.add_item(ativar_btn)
        
        # Botão de estatísticas sempre presente
        stats_btn = discord.ui.Button(
            label="📊 Ver Estatísticas",
            style=discord.ButtonStyle.secondary,
            custom_id=f"matchmaking_stats_{self.nome_equipe}"
        )
        stats_btn.callback = self.ver_estatisticas
        self.add_item(stats_btn)
    
    async def ativar_matchmaking(self, interaction: discord.Interaction):
        """Ativa o matchmaking da equipe"""
        modal = MatchmakingConfigModal(self.nome_equipe, self.lider_id, ativar=True)
        await interaction.response.send_modal(modal)
    
    async def desativar_matchmaking(self, interaction: discord.Interaction):
        """Desativa o matchmaking da equipe"""
        try:
            from sqlalchemy.orm import sessionmaker
            from database.db import get_sync_engine
            
            sync_engine = get_sync_engine()
            Session = sessionmaker(bind=sync_engine)
            sync_session = Session()
            
            try:
                team_formation = TeamFormation(sync_session)
                sucesso = team_formation.desativar_equipe_matchmaking(self.nome_equipe)
                
                if sucesso:
                    embed = discord.Embed(
                        title="🔴 Matchmaking Desativado",
                        description=f"O matchmaking da equipe **{self.nome_equipe}** foi desativado com sucesso.",
                        color=discord.Color.orange()
                    )
                    embed.add_field(
                        name="📋 Próximos Passos",
                        value="• Você não receberá mais candidatos automáticos\n• Pode reativar a qualquer momento\n• Candidatos pendentes ainda podem ser processados",
                        inline=False
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Erro",
                        description="Não foi possível desativar o matchmaking.",
                        color=discord.Color.red()
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Atualizar painel
                if sucesso:
                    channel_manager = TeamChannelManager(interaction.client)
                    await channel_manager.atualizar_painel_controle(
                        interaction.channel, self.nome_equipe, False
                    )
                
            finally:
                sync_session.close()
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao desativar matchmaking: {e}",
                ephemeral=True
            )
    
    async def configurar_matchmaking(self, interaction: discord.Interaction):
        """Abre modal de configuração"""
        modal = MatchmakingConfigModal(self.nome_equipe, self.lider_id, ativar=False)
        await interaction.response.send_modal(modal)
    
    async def ver_estatisticas(self, interaction: discord.Interaction):
        """Mostra estatísticas da equipe"""
        try:
            from sqlalchemy.orm import sessionmaker
            from database.db import get_sync_engine
            from database.models import AplicacaoEquipe
            
            sync_engine = get_sync_engine()
            Session = sessionmaker(bind=sync_engine)
            sync_session = Session()
            
            try:
                # Buscar estatísticas da equipe
                total_aplicacoes = sync_session.query(AplicacaoEquipe).filter(
                    AplicacaoEquipe.equipe_nome == self.nome_equipe
                ).count()
                
                aplicacoes_matchmaking = sync_session.query(AplicacaoEquipe).filter(
                    AplicacaoEquipe.equipe_nome == self.nome_equipe,
                    AplicacaoEquipe.mensagem_aplicacao.like('%matchmaking%')
                ).count()
                
                embed = discord.Embed(
                    title=f"📊 Estatísticas - {self.nome_equipe}",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="📝 Aplicações Totais",
                    value=f"**{total_aplicacoes}** candidatos",
                    inline=True
                )
                
                embed.add_field(
                    name="🤖 Via Matchmaking",
                    value=f"**{aplicacoes_matchmaking}** automáticos",
                    inline=True
                )
                
                if total_aplicacoes > 0:
                    percentual = (aplicacoes_matchmaking / total_aplicacoes) * 100
                    embed.add_field(
                        name="📈 Eficiência do Sistema",
                        value=f"**{percentual:.1f}%** automáticos",
                        inline=True
                    )
                
                embed.set_footer(text="Use /aplicacoes para gerenciar candidaturas")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            finally:
                sync_session.close()
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao obter estatísticas: {e}",
                ephemeral=True
            )


class MatchmakingConfigModal(discord.ui.Modal):
    def __init__(self, nome_equipe: str, lider_id: Optional[int], ativar: bool = True):
        super().__init__(title=f"{'Ativar' if ativar else 'Configurar'} Matchmaking")
        self.nome_equipe = nome_equipe
        self.lider_id = lider_id
        self.ativar = ativar

    descricao_equipe = discord.ui.TextInput(
        label="Descrição da Equipe",
        placeholder="Descreva o foco e objetivos da equipe...",
        style=discord.TextStyle.paragraph,
        max_length=300,
        required=False
    )
    
    habilidades_procuradas = discord.ui.TextInput(
        label="Habilidades Procuradas",
        placeholder="Ex: Python, Design, Machine Learning, Comunicação...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    tamanho_maximo = discord.ui.TextInput(
        label="Tamanho Máximo da Equipe",
        placeholder="6",
        default="6",
        max_length=1,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar tamanho
            try:
                tamanho = int(self.tamanho_maximo.value)
                if tamanho < 2 or tamanho > 6:
                    raise ValueError()
            except ValueError:
                await interaction.response.send_message(
                    "❌ Tamanho deve ser entre 2 e 6 membros.",
                    ephemeral=True
                )
                return
            
            from sqlalchemy.orm import sessionmaker
            from database.db import get_sync_engine
            
            sync_engine = get_sync_engine()
            Session = sessionmaker(bind=sync_engine)
            sync_session = Session()
            
            try:
                team_formation = TeamFormation(sync_session)
                
                # Buscar líder
                lider = sync_session.query(Participante).filter(
                    Participante.nome_equipe == self.nome_equipe
                ).first()
                
                if not lider:
                    await interaction.response.send_message(
                        "❌ Líder da equipe não encontrado.",
                        ephemeral=True
                    )
                    return
                
                # Registrar/atualizar equipe
                equipe = team_formation.registrar_equipe_para_matchmaking(
                    lider,
                    self.descricao_equipe.value.strip() if self.descricao_equipe.value else None,
                    self.habilidades_procuradas.value.strip(),
                    tamanho,
                    lider.modalidade
                )
                
                if self.ativar:
                    embed = discord.Embed(
                        title="🟢 Matchmaking Ativado!",
                        description=f"O matchmaking da equipe **{self.nome_equipe}** está agora ativo!",
                        color=discord.Color.green()
                    )
                else:
                    embed = discord.Embed(
                        title="⚙️ Configurações Atualizadas!",
                        description=f"As configurações da equipe **{self.nome_equipe}** foram salvas.",
                        color=discord.Color.blue()
                    )
                
                embed.add_field(
                    name="🎯 Habilidades Procuradas",
                    value=self.habilidades_procuradas.value.strip(),
                    inline=False
                )
                
                embed.add_field(
                    name="👥 Tamanho Máximo",
                    value=f"{tamanho} membros",
                    inline=True
                )
                
                if self.descricao_equipe.value:
                    embed.add_field(
                        name="📝 Descrição",
                        value=self.descricao_equipe.value.strip(),
                        inline=False
                    )
                
                if self.ativar:
                    embed.add_field(
                        name="🤖 Sistema Ativo",
                        value="• Candidatos compatíveis aplicarão automaticamente\n• Você receberá notificações via DM\n• Use `/aplicacoes` para gerenciar",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Atualizar painel de controle
                channel_manager = TeamChannelManager(interaction.client)
                config = {
                    "habilidades_desejadas": self.habilidades_procuradas.value.strip(),
                    "tamanho_maximo": tamanho,
                    "descricao": self.descricao_equipe.value.strip() if self.descricao_equipe.value else None
                }
                
                await channel_manager.atualizar_painel_controle(
                    interaction.channel,
                    self.nome_equipe,
                    True,
                    config
                )
                
            finally:
                sync_session.close()
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao configurar matchmaking: {e}",
                ephemeral=True
            )