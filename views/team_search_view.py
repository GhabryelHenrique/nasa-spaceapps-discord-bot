import discord
from discord.ext import commands
from sqlalchemy import select, and_
from database.db import DatabaseManager
from database.models import Participante, AplicacaoEquipe, StatusAplicacaoEnum
import asyncio

class TeamSearchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔍 Ver Equipes Disponíveis",
        style=discord.ButtonStyle.secondary,
        custom_id="view_available_teams",
        emoji="🔍"
    )
    async def view_available_teams(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mostra equipes que estão procurando membros"""
        try:
            async with await DatabaseManager.get_session() as session:
                # Buscar participante atual
                result = await session.execute(
                    select(Participante).where(Participante.discord_user_id == interaction.user.id)
                )
                user_participante = result.scalars().first()

                if not user_participante:
                    embed = discord.Embed(
                        title="❌ Não Inscrito",
                        description="Você precisa se inscrever no evento primeiro antes de procurar equipes.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Buscar todas as equipes (exceto a do usuário atual)
                result = await session.execute(
                    select(Participante).where(
                        and_(
                            Participante.nome_equipe != user_participante.nome_equipe,
                            Participante.modalidade == user_participante.modalidade  # Mesma modalidade
                        )
                    )
                )
                outras_equipes = result.scalars().all()

                if not outras_equipes:
                    embed = discord.Embed(
                        title="📭 Nenhuma Equipe Encontrada",
                        description="Não há outras equipes disponíveis na sua modalidade no momento.",
                        color=discord.Color.orange()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Agrupar por equipe
                equipes = {}
                for participante in outras_equipes:
                    if participante.nome_equipe not in equipes:
                        equipes[participante.nome_equipe] = {
                            'lider': participante,
                            'membros': [],
                            'total_membros': 1
                        }
                    else:
                        equipes[participante.nome_equipe]['membros'].append(participante)
                        equipes[participante.nome_equipe]['total_membros'] += 1

                # Criar embed com lista de equipes
                embed = discord.Embed(
                    title="🏆 Equipes Disponíveis",
                    description=f"Encontradas **{len(equipes)}** equipes na sua modalidade ({user_participante.modalidade.value})",
                    color=discord.Color.blue()
                )

                # Limitar a 10 equipes por página
                count = 0
                for nome_equipe, info in list(equipes.items())[:10]:
                    lider = info['lider']
                    total = info['total_membros']
                    
                    field_value = f"**Líder:** {lider.nome} {lider.sobrenome}\n"
                    field_value += f"**Membros:** {total}/6\n"
                    field_value += f"**Modalidade:** {lider.modalidade.value}"
                    
                    embed.add_field(
                        name=f"🚀 {nome_equipe}",
                        value=field_value,
                        inline=True
                    )
                    count += 1

                embed.set_footer(text="Clique em 'Aplicar para Equipe' para enviar sua candidatura!")

                # Criar view com botão para aplicar
                view = TeamApplicationView(user_participante.id)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description="Ocorreu um erro ao buscar equipes. Tente novamente.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"Erro ao buscar equipes: {e}")

    @discord.ui.button(
        label="💼 Marcar Como Disponível",
        style=discord.ButtonStyle.green,
        custom_id="mark_as_available",
        emoji="💼"
    )
    async def mark_as_available(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Marca o usuário como disponível para outras equipes"""
        try:
            async with await DatabaseManager.get_session() as session:
                # Buscar participante atual
                result = await session.execute(
                    select(Participante).where(Participante.discord_user_id == interaction.user.id)
                )
                user_participante = result.scalars().first()

                if not user_participante:
                    embed = discord.Embed(
                        title="❌ Não Inscrito",
                        description="Você precisa se inscrever no evento primeiro.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                if user_participante.disponivel_para_equipe:
                    embed = discord.Embed(
                        title="ℹ️ Já Disponível",
                        description="Você já está marcado como disponível para outras equipes.",
                        color=discord.Color.blue()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Criar modal para coletar descrição das habilidades
                modal = AvailabilityModal(user_participante)
                await interaction.response.send_modal(modal)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description="Ocorreu um erro. Tente novamente.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"Erro ao marcar disponibilidade: {e}")

    @discord.ui.button(
        label="👥 Ver Pessoas Disponíveis",
        style=discord.ButtonStyle.secondary,
        custom_id="view_available_people",
        emoji="👥"
    )
    async def view_available_people(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mostra pessoas disponíveis para equipes (apenas líderes de equipe podem ver)"""
        try:
            async with await DatabaseManager.get_session() as session:
                # Verificar se o usuário é líder de equipe
                result = await session.execute(
                    select(Participante).where(Participante.discord_user_id == interaction.user.id)
                )
                user_participante = result.scalars().first()

                if not user_participante:
                    embed = discord.Embed(
                        title="❌ Não Inscrito",
                        description="Você precisa se inscrever no evento primeiro.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Buscar pessoas disponíveis na mesma modalidade (exceto o próprio usuário)
                result = await session.execute(
                    select(Participante).where(
                        and_(
                            Participante.disponivel_para_equipe == True,
                            Participante.modalidade == user_participante.modalidade,
                            Participante.discord_user_id != interaction.user.id
                        )
                    ).order_by(Participante.data_inscricao.desc())
                )
                pessoas_disponiveis = result.scalars().all()

                if not pessoas_disponiveis:
                    embed = discord.Embed(
                        title="📭 Nenhuma Pessoa Disponível",
                        description="Não há pessoas marcadas como disponíveis na sua modalidade no momento.",
                        color=discord.Color.orange()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Criar embed com lista de pessoas
                embed = discord.Embed(
                    title="👥 Pessoas Disponíveis Para Equipes",
                    description=f"**{len(pessoas_disponiveis)}** pessoas estão procurando equipe na sua modalidade",
                    color=discord.Color.green()
                )

                # Limitar a 8 pessoas por página
                for pessoa in pessoas_disponiveis[:8]:
                    field_value = f"**Escolaridade:** {pessoa.escolaridade.value}\n"
                    field_value += f"**Cidade:** {pessoa.cidade}\n"
                    if pessoa.descricao_habilidades:
                        # Limitar descrição a 100 caracteres
                        desc = pessoa.descricao_habilidades[:100]
                        if len(pessoa.descricao_habilidades) > 100:
                            desc += "..."
                        field_value += f"**Habilidades:** {desc}"
                    
                    embed.add_field(
                        name=f"👤 {pessoa.nome} {pessoa.sobrenome}",
                        value=field_value,
                        inline=True
                    )

                embed.set_footer(text="Estas pessoas estão procurando equipes para participar do evento!")

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description="Ocorreu um erro ao buscar pessoas disponíveis.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"Erro ao buscar pessoas disponíveis: {e}")


class AvailabilityModal(discord.ui.Modal, title="Marcar Como Disponível"):
    def __init__(self, participante):
        super().__init__()
        self.participante = participante

    habilidades = discord.ui.TextInput(
        label="Descreva suas habilidades",
        placeholder="Ex: Programação Python, Design UI/UX, Análise de Dados...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            async with await DatabaseManager.get_session() as session:
                # Atualizar participante
                self.participante.disponivel_para_equipe = True
                self.participante.descricao_habilidades = self.habilidades.value.strip()
                
                session.add(self.participante)
                await session.commit()

                embed = discord.Embed(
                    title="✅ Marcado Como Disponível!",
                    description=f"""Você agora está marcado como disponível para outras equipes!

**Suas habilidades:**
{self.habilidades.value.strip()}

Outras equipes poderão ver seu perfil e te convidar. Você também pode procurar equipes disponíveis e aplicar para elas.""",
                    color=discord.Color.green()
                )
                embed.set_footer(text="Boa sorte na busca por uma equipe!")

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description="Ocorreu um erro ao salvar sua disponibilidade. Tente novamente.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"Erro ao salvar disponibilidade: {e}")


class TeamApplicationView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)  # 5 minutos
        self.user_id = user_id

    @discord.ui.button(
        label="📝 Aplicar para Equipe",
        style=discord.ButtonStyle.primary,
        emoji="📝"
    )
    async def apply_to_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Abre modal para aplicar para uma equipe"""
        modal = TeamApplicationModal(self.user_id)
        await interaction.response.send_modal(modal)


class TeamApplicationModal(discord.ui.Modal, title="Aplicar Para Equipe"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    nome_equipe = discord.ui.TextInput(
        label="Nome da Equipe",
        placeholder="Digite exatamente o nome da equipe que deseja aplicar",
        max_length=100,
        required=True
    )

    mensagem = discord.ui.TextInput(
        label="Mensagem para o Líder",
        placeholder="Conte por que deseja se juntar a esta equipe e como pode contribuir...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            async with await DatabaseManager.get_session() as session:
                # Buscar o aplicante
                result = await session.execute(
                    select(Participante).where(Participante.id == self.user_id)
                )
                aplicante = result.scalars().first()

                # Buscar o líder da equipe
                result = await session.execute(
                    select(Participante).where(Participante.nome_equipe == self.nome_equipe.value.strip())
                )
                lider = result.scalars().first()

                if not lider:
                    embed = discord.Embed(
                        title="❌ Equipe Não Encontrada",
                        description=f"A equipe '{self.nome_equipe.value}' não foi encontrada. Verifique se digitou o nome corretamente.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Verificar se já existe uma aplicação pendente
                result = await session.execute(
                    select(AplicacaoEquipe).where(
                        and_(
                            AplicacaoEquipe.aplicante_id == self.user_id,
                            AplicacaoEquipe.equipe_nome == self.nome_equipe.value.strip(),
                            AplicacaoEquipe.status == StatusAplicacaoEnum.PENDENTE
                        )
                    )
                )
                aplicacao_existente = result.scalars().first()

                if aplicacao_existente:
                    embed = discord.Embed(
                        title="⚠️ Aplicação Já Enviada",
                        description=f"Você já tem uma aplicação pendente para a equipe '{self.nome_equipe.value}'. Aguarde a resposta do líder.",
                        color=discord.Color.orange()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Criar nova aplicação
                aplicacao = AplicacaoEquipe(
                    aplicante_id=self.user_id,
                    equipe_nome=self.nome_equipe.value.strip(),
                    lider_id=lider.id,
                    mensagem_aplicacao=self.mensagem.value.strip()
                )

                session.add(aplicacao)
                await session.commit()

                # Notificar o líder por DM
                try:
                    lider_user = await interaction.client.fetch_user(lider.discord_user_id)
                    
                    embed_lider = discord.Embed(
                        title="📥 Nova Aplicação Para Sua Equipe!",
                        description=f"**{aplicante.nome} {aplicante.sobrenome}** quer se juntar à equipe **{lider.nome_equipe}**",
                        color=discord.Color.blue()
                    )
                    
                    embed_lider.add_field(
                        name="👤 Sobre o Candidato",
                        value=f"**Escolaridade:** {aplicante.escolaridade.value}\n**Cidade:** {aplicante.cidade}\n**Modalidade:** {aplicante.modalidade.value}",
                        inline=False
                    )
                    
                    embed_lider.add_field(
                        name="💬 Mensagem do Candidato",
                        value=self.mensagem.value.strip(),
                        inline=False
                    )

                    if aplicante.descricao_habilidades:
                        embed_lider.add_field(
                            name="🛠️ Habilidades",
                            value=aplicante.descricao_habilidades,
                            inline=False
                        )

                    embed_lider.set_footer(text="Use o comando /aplicacoes para responder a esta aplicação")

                    await lider_user.send(embed=embed_lider)
                    
                except Exception as e:
                    print(f"Erro ao enviar DM para líder: {e}")

                # Confirmar para o aplicante
                embed = discord.Embed(
                    title="✅ Aplicação Enviada!",
                    description=f"Sua aplicação para a equipe **{self.nome_equipe.value}** foi enviada com sucesso!\n\nO líder da equipe receberá uma notificação e poderá aprovar ou rejeitar sua candidatura.",
                    color=discord.Color.green()
                )
                embed.set_footer(text="Você receberá uma resposta em breve!")

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description="Ocorreu um erro ao enviar sua aplicação. Tente novamente.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"Erro ao processar aplicação: {e}")

    @discord.ui.button(
        label="🤖 Formar Equipes Automaticamente",
        style=discord.ButtonStyle.primary,
        custom_id="auto_form_teams",
        emoji="🤖"
    )
    async def auto_form_teams(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Executa algoritmo de formação automática de equipes entre pessoas disponíveis"""
        # Verificar se usuário é administrador
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="⚠️ Permissão Necessária",
                description="Apenas administradores podem executar a formação automática de equipes.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Executar algoritmo de formação automática
            from matchmaking.auto_team_notifications import AutoTeamNotificationSystem
            
            notification_system = AutoTeamNotificationSystem(interaction.client)
            resultados = await notification_system.executar_formacao_completa()
            
            if not resultados["sucesso"]:
                embed = discord.Embed(
                    title="❌ Erro na Formação Automática",
                    description=f"Erro: {resultados.get('erro', 'Erro desconhecido')}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if resultados["equipes_formadas"] == 0:
                embed = discord.Embed(
                    title="📭 Nenhuma Equipe Formada",
                    description=resultados.get("motivo", "Não foi possível formar equipes no momento."),
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Criar embed com resultados
            embed = discord.Embed(
                title="🤖 Formação Automática Executada!",
                description="O algoritmo analisou todas as pessoas disponíveis e formou equipes automaticamente.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="🏆 Equipes Formadas",
                value=f"**{resultados['equipes_formadas']}** novas equipes",
                inline=True
            )
            
            embed.add_field(
                name="👥 Pessoas Agrupadas", 
                value=f"**{resultados['participantes_agrupados']}** participantes",
                inline=True
            )
            
            embed.add_field(
                name="📬 Notificações Enviadas",
                value=f"**{resultados['notificacoes_enviadas']}** DMs enviadas",
                inline=True
            )
            
            if resultados["participantes_restantes"] > 0:
                embed.add_field(
                    name="⏳ Participantes Restantes",
                    value=f"**{resultados['participantes_restantes']}** ainda procurando",
                    inline=False
                )
            
            # Mostrar distribuição por região
            if resultados.get("grupos_por_regiao"):
                regioes_text = ""
                for regiao, count in resultados["grupos_por_regiao"].items():
                    regioes_text += f"• **{regiao.replace('_', ' ').title()}**: {count} pessoas\n"
                
                embed.add_field(
                    name="🌎 Distribuição Regional",
                    value=regioes_text,
                    inline=False
                )
            
            # Mostrar algumas equipes formadas
            if resultados.get("equipes_detalhes"):
                equipes_preview = ""
                for equipe in resultados["equipes_detalhes"][:3]:  # Mostrar apenas 3
                    equipes_preview += f"🏆 **{equipe['nome_sugerido']}** ({equipe['tamanho']} membros, {equipe['score_compatibilidade']}%)\n"
                
                if len(resultados["equipes_detalhes"]) > 3:
                    equipes_preview += f"... e mais {len(resultados['equipes_detalhes']) - 3} equipes"
                
                embed.add_field(
                    name="🎯 Equipes Criadas",
                    value=equipes_preview,
                    inline=False
                )
            
            embed.add_field(
                name="📋 Próximos Passos",
                value="• Participantes receberão notificações via DM\n• Cada pessoa pode aceitar ou rejeitar a equipe\n• Equipes são criadas quando todos os membros aceitam",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description=f"Erro ao executar formação automática: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"Erro na formação automática de equipes: {e}")

    @discord.ui.button(
        label="🏢 Criar Canal de Controle",
        style=discord.ButtonStyle.secondary,
        custom_id="create_team_control_channel",
        emoji="🏢"
    )
    async def create_team_control_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cria canal de controle de matchmaking para líderes de equipe"""
        try:
            async with await DatabaseManager.get_session() as session:
                # Buscar participante atual
                result = await session.execute(
                    select(Participante).where(Participante.discord_user_id == interaction.user.id)
                )
                user_participante = result.scalars().first()

                if not user_participante:
                    embed = discord.Embed(
                        title="❌ Não Inscrito",
                        description="Você precisa se inscrever no evento primeiro.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Verificar se usuário tem equipe
                if not user_participante.nome_equipe:
                    embed = discord.Embed(
                        title="⚠️ Sem Equipe",
                        description="Você precisa criar uma equipe primeiro para ter um canal de controle.",
                        color=discord.Color.orange()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                await interaction.response.defer(ephemeral=True)

                # Criar canal de controle
                from matchmaking.team_channel_manager import TeamChannelManager
                
                channel_manager = TeamChannelManager(interaction.client)
                canal_criado = await channel_manager.criar_canal_equipe(
                    interaction.guild,
                    user_participante,
                    user_participante.nome_equipe
                )

                if canal_criado:
                    embed = discord.Embed(
                        title="🏢 Canal de Controle Criado!",
                        description=f"Canal de matchmaking criado para a equipe **{user_participante.nome_equipe}**!",
                        color=discord.Color.green()
                    )
                    
                    embed.add_field(
                        name="📱 Canal Criado",
                        value=canal_criado.mention,
                        inline=True
                    )
                    
                    embed.add_field(
                        name="🎯 Funcionalidades",
                        value="• Ativar/Desativar matchmaking\n• Configurar habilidades procuradas\n• Ver estatísticas da equipe\n• Receber notificações de candidatos",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="👑 Acesso",
                        value="Apenas você (líder da equipe) pode ver e usar este canal.",
                        inline=False
                    )
                else:
                    embed = discord.Embed(
                        title="⚠️ Canal Já Existe",
                        description="Sua equipe já possui um canal de controle de matchmaking.",
                        color=discord.Color.orange()
                    )

                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description="Erro ao criar canal de controle. Tente novamente.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"Erro ao criar canal de controle: {e}")