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
        elif step == 'descricao':
            await self._process_descricao(message, session)

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
        session['step'] = 'descricao'

        await message.reply("✅ **Título registrado!**\n\n📝 **Descreva sua dúvida ou o que precisa de ajuda:**\nSeja específico para que os mentores possam te ajudar melhor. Inclua a área do conhecimento se relevante.\n\n**Exemplos de áreas:** Biologia, Física, Química, Matemática, Termodinâmica, Mecânica, Astronomia, Geologia, etc.")


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

        # Finalizar solicitação diretamente
        success, result = await self._process_finalizacao(message.author.id)
        if success:
            embed = discord.Embed(
                title="✅ Solicitação Enviada!",
                description=f"Sua solicitação foi registrada com sucesso! ID: #{result}\n\nOs mentores foram notificados e em breve alguém entrará em contato com você.",
                color=discord.Color.green()
            )
            await message.reply(embed=embed)
        else:
            await message.reply(f"❌ Erro: {result}")

    async def _process_finalizacao(self, user_id):
        """Finaliza a solicitação"""
        if user_id not in self.user_sessions:
            return False, "Sessão não encontrada."

        session = self.user_sessions[user_id]

        # Salvar no banco de dados
        try:
            async with await DatabaseManager.get_session() as db_session:
                solicitacao = SolicitacaoMentoria(
                    discord_user_id=user_id,
                    discord_username=session['username'],
                    team_name=session.get('team_name'),
                    titulo=session['titulo'],
                    descricao=session['descricao'],
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
            
            embed = discord.Embed(
                title="🆕 Nova Solicitação de Mentoria",
                description=f"**{solicitacao.titulo}**",
                color=discord.Color.blue()
            )

            if solicitacao.team_name:
                embed.add_field(
                    name="👥 Equipe",
                    value=f"**{solicitacao.team_name}**\n*Solicitado por {solicitacao.discord_username}*",
                    inline=True
                )
            else:
                embed.add_field(
                    name="👤 Solicitante",
                    value=solicitacao.discord_username,
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
        """Notifica a equipe que um mentor assumiu sua solicitação"""
        try:
            # Se há nome da equipe, tentar notificar o canal da equipe
            if solicitacao.team_name:
                guild = self.bot.get_guild(int(config.GUILD_ID)) if config.GUILD_ID else None
                if not guild:
                    guild = self.bot.guilds[0] if self.bot.guilds else None

                if guild:
                    # Procurar canal da equipe
                    team_channel = discord.utils.get(
                        guild.text_channels,
                        name=f"💬│{solicitacao.team_name.lower().replace(' ', '-')}"
                    )

                    if team_channel:
                        embed = discord.Embed(
                            title="✅ Mentor Encontrado para a Equipe!",
                            description=f"A solicitação **\"{solicitacao.titulo}\"** da equipe foi assumida por um mentor!",
                            color=discord.Color.green()
                        )

                        embed.add_field(
                            name="👥 Equipe",
                            value=solicitacao.team_name,
                            inline=True
                        )

                        embed.add_field(
                            name="👨‍🏫 Mentor",
                            value=mentor_username,
                            inline=True
                        )

                        embed.add_field(
                            name="📝 Solicitação",
                            value=solicitacao.descricao[:200] + ("..." if len(solicitacao.descricao) > 200 else ""),
                            inline=False
                        )

                        embed.set_footer(text="O mentor entrará em contato com a equipe em breve!")

                        await team_channel.send(embed=embed)
                        return

            # Fallback: notificar o usuário individual por DM
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
                name="📝 Sua solicitação",
                value=solicitacao.descricao[:200] + ("..." if len(solicitacao.descricao) > 200 else ""),
                inline=False
            )

            embed.set_footer(text="O mentor entrará em contato com você em breve!")

            await user.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Erro ao notificar usuário sobre mentor atribuído", exc_info=e)

    def start_mentoria_request(self, user_id, username, team_name=None):
        """Inicia o processo de solicitação de mentoria"""
        self.user_sessions[user_id] = {
            'step': 'titulo',
            'username': username,
            'team_name': team_name
        }


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
            try:
                await interaction.response.edit_message(view=self)
            except discord.NotFound:
                pass  # Se a mensagem não existir mais, ignora
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)