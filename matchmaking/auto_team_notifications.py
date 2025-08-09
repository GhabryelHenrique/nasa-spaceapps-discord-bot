import discord
import json
from typing import List, Dict, Optional
from datetime import datetime

from database.db import DatabaseManager
from database.models import Participante, MatchSugestao, StatusMatchEnum, AplicacaoEquipe, StatusAplicacaoEnum
from matchmaking.auto_team_formation import AutoTeamFormation


class AutoTeamNotificationSystem:
    def __init__(self, bot):
        self.bot = bot
        self.db_manager = DatabaseManager()
    
    def criar_embed_equipe_sugerida(self, equipe_info: Dict, participante_nome: str) -> discord.Embed:
        """
        Cria embed para notificação de equipe sugerida
        """
        embed = discord.Embed(
            title="🚀 Nova Equipe Sugerida!",
            description=f"**{participante_nome}**, encontramos uma equipe perfeita para você!",
            color=discord.Color.gold()
        )
        
        # Informações básicas da equipe
        embed.add_field(
            name="🏆 Nome da Equipe",
            value=equipe_info["nome_sugerido"],
            inline=True
        )
        
        embed.add_field(
            name="⭐ Compatibilidade",
            value=f"**{equipe_info['score_compatibilidade']}%**",
            inline=True
        )
        
        embed.add_field(
            name="👥 Tamanho",
            value=f"{equipe_info['tamanho']} membros",
            inline=True
        )
        
        # Lista de membros (excluindo o próprio usuário)
        outros_membros = [m for m in equipe_info["membros"] if participante_nome not in m["nome"]]
        if outros_membros:
            membros_text = ""
            for i, membro in enumerate(outros_membros[:4], 1):  # Max 4 para não ficar muito longo
                membros_text += f"`{i}.` **{membro['nome']}**\n"
                membros_text += f"    📍 {membro['cidade']} • 🎓 {membro['escolaridade']}\n"
            
            if len(outros_membros) > 4:
                membros_text += f"    ... e mais {len(outros_membros) - 4} membros"
            
            embed.add_field(
                name="👤 Seus Futuros Companheiros",
                value=membros_text,
                inline=False
            )
        
        # Habilidades em comum
        detalhes = equipe_info.get("detalhes_compatibilidade", {})
        habilidades_comum = detalhes.get("habilidades_comum", [])
        if habilidades_comum:
            habilidades_text = ", ".join(habilidades_comum[:6])  # Max 6 habilidades
            if len(habilidades_comum) > 6:
                habilidades_text += f" +{len(habilidades_comum) - 6} mais"
            
            embed.add_field(
                name="🔧 Habilidades em Comum",
                value=habilidades_text,
                inline=False
            )
        
        # Informações de localização
        regioes = detalhes.get("regioes", [])
        if regioes:
            regioes_unicas = list(set(regioes))
            if len(regioes_unicas) == 1 and regioes_unicas[0] != "desconhecida":
                embed.add_field(
                    name="🌎 Localização",
                    value=f"✅ Todos da região: **{regioes_unicas[0].title()}**",
                    inline=True
                )
            elif len(regioes_unicas) <= 3:
                embed.add_field(
                    name="🌎 Regiões",
                    value=" • ".join(r.title() for r in regioes_unicas if r != "desconhecida"),
                    inline=True
                )
        
        # Modalidades
        modalidades = detalhes.get("modalidades", [])
        if modalidades:
            modalidades_unicas = list(set(modalidades))
            if len(modalidades_unicas) == 1:
                embed.add_field(
                    name="💻 Modalidade",
                    value=modalidades_unicas[0],
                    inline=True
                )
        
        # Como funciona
        embed.add_field(
            name="🎯 Como Funciona",
            value="• Esta equipe foi formada automaticamente pelo sistema\n• Todos os membros têm alta compatibilidade\n• Aceite para criar a equipe instantaneamente\n• Rejeite se não tiver interesse",
            inline=False
        )
        
        embed.add_field(
            name="⏰ Tempo Limite",
            value="Você tem **3 dias** para decidir",
            inline=True
        )
        
        embed.set_footer(
            text=f"Sistema de Matchmaking • Equipe #{equipe_info['id']} • Score: {equipe_info['score_compatibilidade']}%"
        )
        
        return embed
    
    def criar_view_resposta_equipe(self, equipe_info: Dict, participante_id: int) -> discord.View:
        """
        Cria view com botões para aceitar/rejeitar equipe sugerida
        """
        return AutoTeamResponseView(equipe_info, participante_id)
    
    async def enviar_notificacao_equipe_sugerida(self, participante: Participante, equipe_info: Dict, match_sugestao_id: int = None) -> bool:
        """
        Envia notificação de equipe sugerida via DM
        """
        try:
            user = await self.bot.fetch_user(participante.discord_user_id)
            
            embed = self.criar_embed_equipe_sugerida(equipe_info, f"{participante.nome} {participante.sobrenome}")
            view = self.criar_view_resposta_equipe(equipe_info, participante.id)
            
            await user.send(embed=embed, view=view)
            return True
            
        except discord.Forbidden:
            print(f"Não foi possível enviar DM para {participante.discord_username}")
            return False
        except discord.NotFound:
            print(f"Usuário {participante.discord_user_id} não encontrado")
            return False
        except Exception as e:
            print(f"Erro ao enviar notificação de equipe sugerida: {e}")
            return False
    
    async def processar_equipes_formadas(self, resultados_formacao: Dict) -> Dict:
        """
        Processa todas as equipes formadas e envia notificações
        """
        notificacoes_enviadas = 0
        notificacoes_falharam = 0
        
        for equipe_info in resultados_formacao.get("equipes_detalhes", []):
            # Enviar notificação para cada membro da equipe sugerida
            for membro_info in equipe_info["membros"]:
                try:
                    # Buscar participante
                    async with await self.db_manager.get_session() as session:
                        from sqlalchemy import select
                        result = await session.execute(
                            select(Participante).where(Participante.discord_user_id == membro_info["user_id"])
                        )
                        participante = result.scalars().first()
                        
                        if participante:
                            sucesso = await self.enviar_notificacao_equipe_sugerida(participante, equipe_info)
                            if sucesso:
                                notificacoes_enviadas += 1
                            else:
                                notificacoes_falharam += 1
                        else:
                            notificacoes_falharam += 1
                            
                except Exception as e:
                    print(f"Erro ao processar notificação para {membro_info.get('nome', 'N/A')}: {e}")
                    notificacoes_falharam += 1
        
        return {
            "notificacoes_enviadas": notificacoes_enviadas,
            "notificacoes_falharam": notificacoes_falharam,
            "equipes_processadas": len(resultados_formacao.get("equipes_detalhes", []))
        }
    
    async def executar_formacao_completa(self) -> Dict:
        """
        Executa o processo completo: formação de equipes + notificações
        """
        try:
            from sqlalchemy.orm import sessionmaker
            from database.db import get_sync_engine
            
            sync_engine = get_sync_engine()
            Session = sessionmaker(bind=sync_engine)
            sync_session = Session()
            
            try:
                # Executar algoritmo de formação
                auto_formation = AutoTeamFormation(sync_session)
                resultados_formacao = auto_formation.executar_formacao_automatica()
                
                # Se não há equipes formadas, retornar
                if resultados_formacao["equipes_formadas"] == 0:
                    return {
                        "sucesso": True,
                        "equipes_formadas": 0,
                        "motivo": resultados_formacao.get("erro", "Nenhuma equipe foi formada")
                    }
                
                # Processar sugestões no banco (usando sistema existente)
                sugestoes_resultado = auto_formation.processar_todas_sugestoes(resultados_formacao)
                
                # Enviar notificações
                notificacoes_resultado = await self.processar_equipes_formadas(resultados_formacao)
                
                # Combinar resultados
                resultado_final = {
                    "sucesso": True,
                    "equipes_formadas": resultados_formacao["equipes_formadas"],
                    "participantes_agrupados": resultados_formacao["participantes_agrupados"],
                    "participantes_restantes": resultados_formacao["participantes_restantes"],
                    "sugestoes_criadas": sugestoes_resultado["sugestoes_criadas"],
                    "notificacoes_enviadas": notificacoes_resultado["notificacoes_enviadas"],
                    "notificacoes_falharam": notificacoes_resultado["notificacoes_falharam"],
                    "grupos_por_regiao": resultados_formacao["grupos_por_regiao"],
                    "equipes_detalhes": resultados_formacao["equipes_detalhes"]
                }
                
                return resultado_final
                
            finally:
                sync_session.close()
                
        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e)
            }


class AutoTeamResponseView(discord.ui.View):
    def __init__(self, equipe_info: Dict, participante_id: int):
        super().__init__(timeout=None)  # View persistente
        self.equipe_info = equipe_info
        self.participante_id = participante_id
        
        # Adicionar IDs únicos aos botões
        self.aceitar.custom_id = f"auto_team_accept_{equipe_info['id']}_{participante_id}"
        self.rejeitar.custom_id = f"auto_team_reject_{equipe_info['id']}_{participante_id}"
    
    @discord.ui.button(
        label="✅ Aceitar Equipe",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="auto_team_accept_placeholder"
    )
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Aceita a equipe sugerida automaticamente"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            resultado = await self.processar_aceitacao_equipe(interaction)
            
            if resultado["sucesso"]:
                embed = discord.Embed(
                    title="🎉 Equipe Aceita!",
                    description=f"Parabéns! Você aceitou entrar na equipe **{self.equipe_info['nome_sugerido']}**!",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="🏆 Sua Nova Equipe",
                    value=self.equipe_info['nome_sugerido'],
                    inline=True
                )
                
                embed.add_field(
                    name="👥 Membros",
                    value=f"{self.equipe_info['tamanho']} pessoas",
                    inline=True
                )
                
                embed.add_field(
                    name="📬 Próximos Passos",
                    value="• Outros membros também precisam aceitar\n• Equipe será criada quando todos aceitarem\n• Você receberá mais informações em breve",
                    inline=False
                )
                
                if resultado.get("membros_confirmados"):
                    embed.add_field(
                        name="✅ Status",
                        value=f"{resultado['membros_confirmados']}/{self.equipe_info['tamanho']} membros confirmados",
                        inline=True
                    )
                
            else:
                embed = discord.Embed(
                    title="❌ Erro",
                    description=resultado.get("erro", "Não foi possível aceitar a equipe."),
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Desabilitar botões se aceito com sucesso
            if resultado["sucesso"]:
                for item in self.children:
                    item.disabled = True
                await interaction.edit_original_response(view=self)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description=f"Ocorreu um erro ao processar sua resposta: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(
        label="❌ Rejeitar Equipe",
        style=discord.ButtonStyle.danger,
        emoji="❌",
        custom_id="auto_team_reject_placeholder"
    )
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rejeita a equipe sugerida"""
        modal = RejectTeamModal(self.equipe_info, self.participante_id)
        await interaction.response.send_modal(modal)
    
    async def processar_aceitacao_equipe(self, interaction: discord.Interaction) -> Dict:
        """
        Processa a aceitação de uma equipe sugerida
        """
        try:
            async with await DatabaseManager().get_session() as session:
                from sqlalchemy import select, update
                
                # Buscar participante
                result = await session.execute(
                    select(Participante).where(Participante.id == self.participante_id)
                )
                participante = result.scalars().first()
                
                if not participante:
                    return {"sucesso": False, "erro": "Participante não encontrado"}
                
                # Verificar se já aceito/rejeitado
                if not participante.disponivel_para_equipe:
                    return {"sucesso": False, "erro": "Você já não está mais disponível para equipes"}
                
                # Marcar como indisponível (aceita uma equipe)
                participante.disponivel_para_equipe = False
                
                # Criar entrada temporária de "aceitação de equipe" usando sistema existente
                nova_aplicacao = AplicacaoEquipe(
                    aplicante_id=self.participante_id,
                    equipe_nome=self.equipe_info["nome_sugerido"],
                    lider_id=self.participante_id,  # Temporário - será definido quando equipe for criada
                    mensagem_aplicacao=f"[AUTO_TEAM_ACCEPT] Membro da equipe #{self.equipe_info['id']}",
                    status=StatusAplicacaoEnum.APROVADA
                )
                
                session.add(nova_aplicacao)
                await session.commit()
                
                # TODO: Verificar quantos membros já aceitaram e criar equipe se todos aceitaram
                
                return {
                    "sucesso": True,
                    "equipe": self.equipe_info["nome_sugerido"],
                    "participante": f"{participante.nome} {participante.sobrenome}"
                }
                
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}


class RejectTeamModal(discord.ui.Modal):
    def __init__(self, equipe_info: Dict, participante_id: int):
        super().__init__(title="Rejeitar Equipe Sugerida")
        self.equipe_info = equipe_info
        self.participante_id = participante_id

    motivo = discord.ui.TextInput(
        label="Motivo da rejeição (opcional)",
        placeholder="Por que você está rejeitando esta equipe?",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            async with await DatabaseManager().get_session() as session:
                from sqlalchemy import select
                
                # Buscar participante
                result = await session.execute(
                    select(Participante).where(Participante.id == self.participante_id)
                )
                participante = result.scalars().first()
                
                if not participante:
                    await interaction.response.send_message(
                        "❌ Erro: Participante não encontrado.",
                        ephemeral=True
                    )
                    return
                
                # Criar registro de rejeição
                rejeicao = AplicacaoEquipe(
                    aplicante_id=self.participante_id,
                    equipe_nome=self.equipe_info["nome_sugerido"],
                    lider_id=self.participante_id,
                    mensagem_aplicacao=f"[AUTO_TEAM_REJECT] {self.motivo.value or 'Sem motivo especificado'}",
                    status=StatusAplicacaoEnum.REJEITADA
                )
                
                session.add(rejeicao)
                await session.commit()
                
                embed = discord.Embed(
                    title="👋 Equipe Rejeitada",
                    description=f"Você rejeitou a equipe **{self.equipe_info['nome_sugerido']}**.",
                    color=discord.Color.orange()
                )
                
                embed.add_field(
                    name="🔍 Continuar Procurando",
                    value="Você continua disponível para outras sugestões de equipe ou pode procurar equipes manualmente!",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description=f"Erro ao processar rejeição: {e}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)