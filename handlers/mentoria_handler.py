import discord
from database.db import DatabaseManager
from database.models import SolicitacaoMentoria, StatusSolicitacaoEnum
from sqlalchemy import select, update
from datetime import datetime
import config

class MentoriaHandler:
    def __init__(self, bot):
        self.bot = bot
        self.user_sessions = {}  # Para armazenar estados das solicitações
        self.logger = self.bot.logger

    async def process_mentoria_answer(self, message):
        """Processa respostas do formulário de mentoria"""
        user_id = message.author.id
        
        if user_id not in self.user_sessions:
            return
        
        session = self.user_sessions[user_id]
        step = session.get('step')
        
        if step == 'titulo':
            await self._process_titulo(message, session)
        elif step == 'area':
            await self._process_area(message, session)
        elif step == 'descricao':
            await self._process_descricao(message, session)
        elif step == 'urgencia':
            await self._process_urgencia(message, session)

    async def _process_titulo(self, message, session):
        """Processa o título da solicitação"""
        titulo = message.content.strip()
        
        if len(titulo) < 5:
            await message.reply("❌ O título deve ter pelo menos 5 caracteres. Tente novamente:")
            return
        
        if len(titulo) > 200:
            await message.reply("❌ O título deve ter no máximo 200 caracteres. Tente novamente:")
            return
        
        session['titulo'] = titulo
        session['step'] = 'area'
        
        await message.reply("✅ **Título registrado!**\n\n📚 **Qual é a área de conhecimento?**\nExemplos: Python, JavaScript, Machine Learning, Design, etc.")

    async def _process_area(self, message, session):
        """Processa a área de conhecimento"""
        area = message.content.strip()
        
        if len(area) < 3:
            await message.reply("❌ A área deve ter pelo menos 3 caracteres. Tente novamente:")
            return
        
        if len(area) > 100:
            await message.reply("❌ A área deve ter no máximo 100 caracteres. Tente novamente:")
            return
        
        session['area'] = area
        session['step'] = 'descricao'
        
        await message.reply("✅ **Área registrada!**\n\n📝 **Descreva sua dúvida ou o que precisa de ajuda:**\nSeja específico para que os mentores possam te ajudar melhor.")

    async def _process_descricao(self, message, session):
        """Processa a descrição da solicitação"""
        descricao = message.content.strip()
        
        if len(descricao) < 10:
            await message.reply("❌ A descrição deve ter pelo menos 10 caracteres. Tente novamente:")
            return
        
        if len(descricao) > 2000:
            await message.reply("❌ A descrição deve ter no máximo 2000 caracteres. Tente novamente:")
            return
        
        session['descricao'] = descricao
        session['step'] = 'urgencia'
        
        urgencia_embed = discord.Embed(
            title="⏱️ Nível de Urgência",
            description="Escolha o nível de urgência da sua solicitação:",
            color=discord.Color.blue()
        )
        urgencia_embed.add_field(name="🟢 Baixa", value="Não é urgente, posso aguardar", inline=True)
        urgencia_embed.add_field(name="🟡 Média", value="Preciso de ajuda nos próximos dias", inline=True)
        urgencia_embed.add_field(name="🔴 Alta", value="Preciso de ajuda urgentemente", inline=True)
        
        view = UrgenciaSelectionView(self)
        await message.reply(embed=urgencia_embed, view=view)

    async def _process_urgencia(self, urgencia, user_id):
        """Finaliza a solicitação com o nível de urgência"""
        if user_id not in self.user_sessions:
            return False, "Sessão não encontrada."
        
        session = self.user_sessions[user_id]
        
        # Salvar no banco de dados
        try:
            async with await DatabaseManager.get_session() as db_session:
                solicitacao = SolicitacaoMentoria(
                    discord_user_id=user_id,
                    discord_username=session['username'],
                    titulo=session['titulo'],
                    descricao=session['descricao'],
                    area_conhecimento=session['area'],
                    nivel_urgencia=urgencia,
                    status=StatusSolicitacaoEnum.PENDENTE
                )
                
                db_session.add(solicitacao)
                await db_session.commit()
                
                # Limpar sessão
                del self.user_sessions[user_id]
                
                # Notificar mentores
                await self._notify_mentors(solicitacao)
                
                self.logger.info(f"Nova solicitação de mentoria criada: {solicitacao.titulo} por {session['username']}")
                
                return True, solicitacao.id
        
        except Exception as e:
            self.logger.error(f"Erro ao salvar solicitação de mentoria para usuário {user_id}", exc_info=e)
            return False, "Erro interno. Tente novamente."

    async def _notify_mentors(self, solicitacao):
        """Notifica os mentores sobre nova solicitação"""
        try:
            # Buscar canal dos mentores
            guild = self.bot.get_guild(int(config.GUILD_ID)) if config.GUILD_ID else None
            if not guild:
                guild = self.bot.guilds[0] if self.bot.guilds else None
            
            if not guild:
                self.logger.error("Nenhuma guild encontrada para notificar mentores")
                return
            
            # Procurar canal de mentores
            mentor_channel = discord.utils.get(guild.channels, id=1404498946482503906)  # ID do canal de mentores
            if not mentor_channel:
                self.logger.warning("Canal 'mentores' não encontrado")
                return
            
            # Emoji baseado na urgência
            urgencia_emoji = {
                'Baixa': '🟢',
                'Média': '🟡', 
                'Alta': '🔴'
            }
            
            embed = discord.Embed(
                title="🆕 Nova Solicitação de Mentoria",
                description=f"**{solicitacao.titulo}**",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="👤 Solicitante",
                value=solicitacao.discord_username,
                inline=True
            )
            
            embed.add_field(
                name="📚 Área",
                value=solicitacao.area_conhecimento,
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Urgência",
                value=f"{urgencia_emoji.get(solicitacao.nivel_urgencia, '⚪')} {solicitacao.nivel_urgencia}",
                inline=True
            )
            
            embed.add_field(
                name="📝 Descrição",
                value=solicitacao.descricao[:500] + ("..." if len(solicitacao.descricao) > 500 else ""),
                inline=False
            )
            
            embed.set_footer(text=f"ID: {solicitacao.id} | {solicitacao.data_solicitacao.strftime('%d/%m/%Y %H:%M')}")
            
            view = MentorResponseView(solicitacao.id, self)
            await mentor_channel.send(embed=embed, view=view)
            
            self.logger.info(f"Mentores notificados sobre solicitação {solicitacao.id}")
            
        except Exception as e:
            self.logger.error(f"Erro ao notificar mentores sobre solicitação {solicitacao.id}", exc_info=e)

    async def assumir_mentoria(self, solicitacao_id, mentor_id, mentor_username):
        """Mentor assume uma solicitação"""
        try:
            async with await DatabaseManager.get_session() as session:
                # Verificar se solicitação existe e está pendente
                result = await session.execute(
                    select(SolicitacaoMentoria).where(
                        SolicitacaoMentoria.id == solicitacao_id,
                        SolicitacaoMentoria.status == StatusSolicitacaoEnum.PENDENTE
                    )
                )
                solicitacao = result.scalar_one_or_none()
                
                if not solicitacao:
                    return False, "Solicitação não encontrada ou já foi assumida."
                
                # Atualizar solicitação
                await session.execute(
                    update(SolicitacaoMentoria).where(
                        SolicitacaoMentoria.id == solicitacao_id
                    ).values(
                        status=StatusSolicitacaoEnum.EM_ANDAMENTO,
                        mentor_discord_id=mentor_id,
                        mentor_username=mentor_username,
                        data_assumida=datetime.utcnow()
                    )
                )
                await session.commit()
                
                # Notificar o solicitante
                await self._notify_user_mentor_assigned(solicitacao, mentor_username)
                
                self.logger.info(f"Mentoria {solicitacao_id} assumida por {mentor_username}")
                return True, "Mentoria assumida com sucesso!"
        
        except Exception as e:
            self.logger.error(f"Erro ao assumir mentoria {solicitacao_id}", exc_info=e)
            return False, "Erro interno."

    async def _notify_user_mentor_assigned(self, solicitacao, mentor_username):
        """Notifica o usuário que um mentor assumiu sua solicitação"""
        try:
            user = self.bot.get_user(solicitacao.discord_user_id)
            if not user:
                return
            
            embed = discord.Embed(
                title="✅ Mentor Encontrado!",
                description=f"Sua solicitação **\"{solicitacao.titulo}\"** foi assumida por um mentor!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="👨‍🏫 Mentor",
                value=mentor_username,
                inline=True
            )
            
            embed.add_field(
                name="📚 Área",
                value=solicitacao.area_conhecimento,
                inline=True
            )
            
            embed.add_field(
                name="📝 Sua solicitação",
                value=solicitacao.descricao[:200] + ("..." if len(solicitacao.descricao) > 200 else ""),
                inline=False
            )
            
            embed.set_footer(text="O mentor entrará em contato com você em breve!")
            
            await user.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Erro ao notificar usuário sobre mentor atribuído", exc_info=e)

    def start_mentoria_request(self, user_id, username):
        """Inicia o processo de solicitação de mentoria"""
        self.user_sessions[user_id] = {
            'step': 'titulo',
            'username': username
        }

class UrgenciaSelectionView(discord.ui.View):
    def __init__(self, handler):
        super().__init__(timeout=300)
        self.handler = handler

    @discord.ui.button(label='Baixa', style=discord.ButtonStyle.success, emoji='🟢')
    async def urgencia_baixa(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, result = await self.handler._process_urgencia('Baixa', interaction.user.id)
        if success:
            embed = discord.Embed(
                title="✅ Solicitação Enviada!",
                description=f"Sua solicitação foi registrada com sucesso! ID: #{result}\n\nOs mentores foram notificados e em breve alguém entrará em contato com você.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ Erro: {result}", ephemeral=True)

    @discord.ui.button(label='Média', style=discord.ButtonStyle.primary, emoji='🟡')
    async def urgencia_media(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, result = await self.handler._process_urgencia('Média', interaction.user.id)
        if success:
            embed = discord.Embed(
                title="✅ Solicitação Enviada!",
                description=f"Sua solicitação foi registrada com sucesso! ID: #{result}\n\nOs mentores foram notificados e em breve alguém entrará em contato com você.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ Erro: {result}", ephemeral=True)

    @discord.ui.button(label='Alta', style=discord.ButtonStyle.danger, emoji='🔴')
    async def urgencia_alta(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, result = await self.handler._process_urgencia('Alta', interaction.user.id)
        if success:
            embed = discord.Embed(
                title="✅ Solicitação Enviada!",
                description=f"Sua solicitação foi registrada com sucesso! ID: #{result}\n\nOs mentores foram notificados e em breve alguém entrará em contato com você.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ Erro: {result}", ephemeral=True)

class MentorResponseView(discord.ui.View):
    def __init__(self, solicitacao_id, handler):
        super().__init__(timeout=None)
        self.solicitacao_id = solicitacao_id
        self.handler = handler

    @discord.ui.button(label='Assumir Mentoria', style=discord.ButtonStyle.primary, emoji='✋')
    async def assumir_mentoria(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, message = await self.handler.assumir_mentoria(
            self.solicitacao_id,
            interaction.user.id,
            interaction.user.display_name
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Mentoria Assumida!",
                description=message,
                color=discord.Color.green()
            )
            # Desabilitar o botão
            button.disabled = True
            button.label = "Já Assumida"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)