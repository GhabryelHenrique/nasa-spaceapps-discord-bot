import discord
from discord.ext import commands
from sqlalchemy import select, and_, update
from database.db import DatabaseManager
from database.models import Participante, AplicacaoEquipe, StatusAplicacaoEnum
from utils.logger import get_logger
from datetime import datetime

class ApplicationHandler:
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger()

    async def get_pending_applications(self, lider_user_id):
        """Busca aplicações pendentes para as equipes do líder"""
        try:
            async with await DatabaseManager.get_session() as session:
                # Buscar o líder
                result = await session.execute(
                    select(Participante).where(Participante.discord_user_id == lider_user_id)
                )
                lider = result.scalars().first()
                
                if not lider:
                    return None, "Você não está inscrito no evento."

                # Buscar aplicações pendentes para a equipe do líder
                result = await session.execute(
                    select(AplicacaoEquipe).where(
                        and_(
                            AplicacaoEquipe.lider_id == lider.id,
                            AplicacaoEquipe.status == StatusAplicacaoEnum.PENDENTE
                        )
                    ).order_by(AplicacaoEquipe.data_aplicacao.desc())
                )
                aplicacoes = result.scalars().all()

                return aplicacoes, None
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar aplicações pendentes para líder {lider_user_id}", exc_info=e)
            return None, f"Erro interno: {str(e)}"

    async def respond_to_application(self, lider_user_id, aplicacao_id, aprovada, resposta_texto=None):
        """Responde a uma aplicação (aprovar ou rejeitar)"""
        try:
            self.logger.info(f"Líder {lider_user_id} respondendo aplicação {aplicacao_id}: {'Aprovada' if aprovada else 'Rejeitada'}")
            
            async with await DatabaseManager.get_session() as session:
                # Buscar o líder
                result = await session.execute(
                    select(Participante).where(Participante.discord_user_id == lider_user_id)
                )
                lider = result.scalars().first()
                
                if not lider:
                    self.logger.warning(f"Usuário {lider_user_id} tentou responder aplicação mas não está inscrito")
                    return False, "Você não está inscrito no evento."

                # Buscar a aplicação
                result = await session.execute(
                    select(AplicacaoEquipe).where(
                        and_(
                            AplicacaoEquipe.id == aplicacao_id,
                            AplicacaoEquipe.lider_id == lider.id,
                            AplicacaoEquipe.status == StatusAplicacaoEnum.PENDENTE
                        )
                    )
                )
                aplicacao = result.scalars().first()

                if not aplicacao:
                    self.logger.warning(f"Aplicação {aplicacao_id} não encontrada ou já respondida para líder {lider_user_id}")
                    return False, "Aplicação não encontrada ou já foi respondida."

            # Atualizar status da aplicação
            novo_status = StatusAplicacaoEnum.APROVADA if aprovada else StatusAplicacaoEnum.REJEITADA
            aplicacao.status = novo_status
            aplicacao.resposta_lider = resposta_texto
            aplicacao.data_resposta = datetime.utcnow()

            session.add(aplicacao)
            
            # Se aprovada, adicionar membro à equipe
            if aprovada:
                # Buscar o aplicante
                result = await session.execute(
                    select(Participante).where(Participante.id == aplicacao.aplicante_id)
                )
                aplicante = result.scalars().first()

                if aplicante:
                    # Verificar se a equipe não está cheia (máximo 6 membros)
                    result = await session.execute(
                        select(Participante).where(Participante.nome_equipe == aplicacao.equipe_nome)
                    )
                    membros_atuais = result.scalars().all()

                    if len(membros_atuais) >= 6:
                        aplicacao.status = StatusAplicacaoEnum.REJEITADA
                        aplicacao.resposta_lider = "Equipe já está completa (6 membros máximo)."
                        session.add(aplicacao)
                        await session.commit()
                        return False, "A equipe já está completa (6 membros máximo)."

                    # Transferir o aplicante para a nova equipe
                    antigo_nome_equipe = aplicante.nome_equipe
                    aplicante.nome_equipe = aplicacao.equipe_nome
                    aplicante.disponivel_para_equipe = False  # Não está mais disponível
                    
                    session.add(aplicante)
                    
                    # Cancelar outras aplicações pendentes do mesmo usuário
                    await session.execute(
                        update(AplicacaoEquipe).where(
                            and_(
                                AplicacaoEquipe.aplicante_id == aplicacao.aplicante_id,
                                AplicacaoEquipe.status == StatusAplicacaoEnum.PENDENTE,
                                AplicacaoEquipe.id != aplicacao_id
                            )
                        ).values(
                            status=StatusAplicacaoEnum.CANCELADA,
                            resposta_lider="Usuário foi aceito em outra equipe."
                        )
                    )

            await session.commit()

            # Notificar o aplicante
            try:
                aplicante_user = await self.bot.fetch_user(aplicacao.aplicante.discord_user_id)
                
                if aprovada:
                    embed = discord.Embed(
                        title="🎉 Aplicação Aprovada!",
                        description=f"Parabéns! Sua aplicação para a equipe **{aplicacao.equipe_nome}** foi **APROVADA**!",
                        color=discord.Color.green()
                    )
                    
                    if resposta_texto:
                        embed.add_field(
                            name="💬 Mensagem do Líder",
                            value=resposta_texto,
                            inline=False
                        )
                    
                    embed.add_field(
                        name="🚀 Próximos Passos",
                        value="Você agora faz parte da equipe! Procure pelos canais da sua nova equipe no servidor para se integrar com os outros membros.",
                        inline=False
                    )

                    # Adicionar à role da equipe se possível
                    try:
                        guild = self.bot.guilds[0] if self.bot.guilds else None
                        if guild:
                            member = guild.get_member(aplicacao.aplicante.discord_user_id)
                            if member:
                                # Buscar role da equipe
                                team_role = discord.utils.get(guild.roles, name=f"Equipe {aplicacao.equipe_nome}")
                                if team_role:
                                    await member.add_roles(team_role, reason="Aplicação aprovada para equipe")
                                    
                                    # Remover role da equipe anterior se existir
                                    old_role = discord.utils.get(guild.roles, name=f"Equipe {antigo_nome_equipe}")
                                    if old_role and old_role in member.roles:
                                        await member.remove_roles(old_role, reason="Transferido para nova equipe")
                    except Exception as e:
                        print(f"Erro ao gerenciar roles: {e}")

                else:
                    embed = discord.Embed(
                        title="😔 Aplicação Rejeitada",
                        description=f"Sua aplicação para a equipe **{aplicacao.equipe_nome}** foi **rejeitada**.",
                        color=discord.Color.red()
                    )
                    
                    if resposta_texto:
                        embed.add_field(
                            name="💬 Mensagem do Líder",
                            value=resposta_texto,
                            inline=False
                        )
                    
                    embed.add_field(
                        name="🔄 Continue Tentando",
                        value="Não desanime! Continue procurando por outras equipes ou marque-se como disponível para receber convites.",
                        inline=False
                    )

                embed.set_footer(text="NASA Space Apps Challenge 2025 - Sistema de Equipes")
                await aplicante_user.send(embed=embed)
                
            except Exception as e:
                print(f"Erro ao notificar aplicante: {e}")

            return True, "Resposta enviada com sucesso!"
            
        except Exception as e:
            self.logger.error(f"Erro ao responder aplicação {aplicacao_id} pelo líder {lider_user_id}", exc_info=e)
            return False, f"Erro interno: {str(e)}"

    async def get_user_applications(self, user_id):
        """Busca aplicações do usuário"""
        try:
            async with await DatabaseManager.get_session() as session:
                result = await session.execute(
                    select(Participante).where(Participante.discord_user_id == user_id)
                )
                user_participante = result.scalars().first()
                
                if not user_participante:
                    return None, "Você não está inscrito no evento."

                result = await session.execute(
                    select(AplicacaoEquipe).where(AplicacaoEquipe.aplicante_id == user_participante.id)
                    .order_by(AplicacaoEquipe.data_aplicacao.desc())
                )
                aplicacoes = result.scalars().all()

                return aplicacoes, None
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar aplicações do usuário {user_id}", exc_info=e)
            return None, f"Erro interno: {str(e)}"


class ApplicationResponseView(discord.ui.View):
    def __init__(self, aplicacao_id, handler):
        super().__init__(timeout=None)  # Persistent view
        self.aplicacao_id = aplicacao_id
        self.handler = handler

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.green)
    async def approve_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Aprova a aplicação"""
        modal = ResponseModal(self.aplicacao_id, True, self.handler)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="❌ Rejeitar", style=discord.ButtonStyle.red)
    async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rejeita a aplicação"""
        modal = ResponseModal(self.aplicacao_id, False, self.handler)
        await interaction.response.send_modal(modal)


class ResponseModal(discord.ui.Modal):
    def __init__(self, aplicacao_id, aprovada, handler):
        self.aplicacao_id = aplicacao_id
        self.aprovada = aprovada
        self.handler = handler
        
        title = "Aprovar Candidato" if aprovada else "Rejeitar Candidato"
        super().__init__(title=title)

    resposta = discord.ui.TextInput(
        label="Mensagem para o candidato (opcional)",
        placeholder="Deixe uma mensagem explicando sua decisão...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            sucesso, mensagem = await self.handler.respond_to_application(
                interaction.user.id, 
                self.aplicacao_id, 
                self.aprovada,
                self.resposta.value.strip() if self.resposta.value.strip() else None
            )

            if sucesso:
                status_text = "aprovada" if self.aprovada else "rejeitada"
                embed = discord.Embed(
                    title="✅ Resposta Enviada!",
                    description=f"A aplicação foi **{status_text}** com sucesso!\n\nO candidato foi notificado da sua decisão.",
                    color=discord.Color.green() if self.aprovada else discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="❌ Erro",
                    description=mensagem,
                    color=discord.Color.red()
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description="Ocorreu um erro ao processar sua resposta. Tente novamente.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"Erro ao responder aplicação: {e}")