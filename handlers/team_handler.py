import discord
from discord.ext import commands
import asyncio
from views.team_view import TeamManagementView, MemberSelectView
from utils.logger import get_logger

class TeamHandler:
    def __init__(self, bot):
        self.bot = bot
        self.user_sessions = {}  # user_id: session_data
        self.logger = get_logger()

    async def start_team_creation(self, interaction: discord.Interaction):
        """Inicia o processo de criação de equipe"""
        user_id = interaction.user.id

        # Criar sessão
        self.user_sessions[user_id] = {
            'step': 'name',
            'data': {},
            'channel': None
        }

        # Criar canal privado para o usuário
        try:
            guild = interaction.guild

            # Buscar ou criar categoria para criação de equipes
            category = discord.utils.get(guild.categories, name="📝 CRIAÇÃO DE EQUIPES")
            if not category:
                category = await guild.create_category(
                    "📝 CRIAÇÃO DE EQUIPES",
                    reason="Categoria para criação de equipes"
                )

            # Configurar permissões (apenas o usuário e o bot)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )
            }

            # Criar canal temporário
            temp_channel = await guild.create_text_channel(
                f"equipe-{interaction.user.display_name.lower()}",
                category=category,
                overwrites=overwrites,
                topic=f"Criação de equipe para {interaction.user.display_name}",
                reason=f"Canal temporário para criação de equipe por {interaction.user}"
            )

            self.user_sessions[user_id]['channel'] = temp_channel

            # Responder à interação
            await interaction.response.send_message(
                f"✅ Canal privado criado! Continue a criação da equipe em {temp_channel.mention}",
                ephemeral=True
            )

            # Enviar primeira pergunta no canal
            embed = discord.Embed(
                title="🏆 Criação de Equipe - Passo 1/3",
                description="""**Bem-vindo ao sistema de criação de equipes!**

Vamos criar sua equipe em 3 passos simples:

**📝 Passo 1: Nome da Equipe**
Escolha um nome único e criativo para sua equipe.

**Regras para o nome:**
• Entre 3 e 30 caracteres
• Apenas letras, números, espaços e hífens
• Não pode já existir outra equipe com este nome

**Digite o nome da sua equipe:**""",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="💡 Dicas",
                value="• Seja criativo e único\n• O nome será usado nos canais e roles\n• Pode usar espaços normalmente",
                inline=False
            )

            embed.set_footer(text="Digite 'cancelar' a qualquer momento para cancelar")

            await temp_channel.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Erro ao criar canal temporário para {user_id}", exc_info=e)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Erro ao criar canal temporário!", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Erro ao criar canal temporário!", ephemeral=True)
            except:
                pass

    async def process_team_creation(self, message):
        """Processa as respostas do formulário de criação"""
        user_id = message.author.id

        if user_id not in self.user_sessions:
            return

        session = self.user_sessions[user_id]

        # Verificar se está no canal correto
        if message.channel != session['channel']:
            return

        # Verificar cancelamento
        if message.content.lower() in ['cancelar', 'cancel', 'sair', 'exit']:
            await self.cancel_team_creation(message.author, session['channel'])
            return

        step = session['step']

        try:
            if step == 'name':
                await self.process_name_step(message, session)
            elif step == 'description':
                await self.process_description_step(message, session)
            elif step == 'category':
                await self.process_category_step(message, session)

        except Exception as e:
            self.logger.error(f"Erro no processamento da criação de equipe para {user_id}", exc_info=e)
            await message.channel.send("❌ Erro interno. Tente novamente ou digite 'cancelar'.")

    async def process_name_step(self, message, session):
        """Processa o nome da equipe"""
        nome = message.content.strip()

        # Validar nome
        if len(nome) < 3 or len(nome) > 30:
            await message.channel.send("❌ O nome deve ter entre 3 e 30 caracteres. Tente novamente:")
            return

        # Verificar caracteres válidos
        import re
        if not re.match(r'^[a-zA-ZÀ-ÿ0-9\s\-]+$', nome):
            await message.channel.send("❌ O nome pode conter apenas letras, números, espaços e hífens. Tente novamente:")
            return

        # Verificar se já existe
        guild = message.guild
        existing_role = discord.utils.get(guild.roles, name=f"Equipe {nome}")
        if existing_role:
            await message.channel.send(f"❌ Já existe uma equipe com o nome '{nome}'. Escolha outro nome:")
            return

        # Salvar nome e avançar
        session['data']['name'] = nome
        session['step'] = 'description'

        embed = discord.Embed(
            title="🏆 Criação de Equipe - Passo 2/3",
            description=f"""**Nome escolhido:** {nome} ✅

**📋 Passo 2: Descrição da Equipe**
Descreva o propósito da sua equipe e o que vocês pretendem fazer.

**Regras para a descrição:**
• Entre 10 e 500 caracteres
• Seja claro sobre os objetivos da equipe
• Pode incluir áreas de interesse, projetos, etc.

**Digite a descrição da sua equipe:**""",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="💡 Exemplo",
            value="Equipe focada em desenvolvimento web com React e Node.js. Buscamos criar projetos inovadores e aprender juntos!",
            inline=False
        )

        await message.channel.send(embed=embed)

    async def process_description_step(self, message, session):
        """Processa a descrição da equipe"""
        descricao = message.content.strip()

        # Validar descrição
        if len(descricao) < 10 or len(descricao) > 500:
            await message.channel.send("❌ A descrição deve ter entre 10 e 500 caracteres. Tente novamente:")
            return

        # Salvar descrição e avançar
        session['data']['description'] = descricao
        session['step'] = 'category'

        embed = discord.Embed(
            title="🏆 Criação de Equipe - Passo 3/3",
            description=f"""**Nome:** {session['data']['name']} ✅
**Descrição:** {descricao} ✅

**🎯 Passo 3: Categoria da Equipe**
Escolha a categoria que melhor representa sua equipe.

**Categorias disponíveis:**
`1` - 💻 **Programação & Desenvolvimento**
`2` - 🎨 **Design & Criatividade**
`3` - 📊 **Dados & Analytics**
`4` - 🎮 **Jogos & Entretenimento**
`5` - 🔬 **Ciência & Pesquisa**
`6` - 💼 **Negócios & Empreendedorismo**
`7` - 🎓 **Educação & Ensino**
`8` - 🌐 **Geral & Outros**

**Digite o número da categoria escolhida:**""",
            color=discord.Color.blue()
        )

        await message.channel.send(embed=embed)

    async def process_category_step(self, message, session):
        """Processa a categoria e finaliza criação"""
        try:
            categoria_num = int(message.content.strip())
            if categoria_num not in range(1, 9):
                raise ValueError()
        except ValueError:
            await message.channel.send("❌ Digite um número válido de 1 a 8:")
            return

        categorias = {
            1: "💻 Programação & Desenvolvimento",
            2: "🎨 Design & Criatividade",
            3: "📊 Dados & Analytics",
            4: "🎮 Jogos & Entretenimento",
            5: "🔬 Ciência & Pesquisa",
            6: "💼 Negócios & Empreendedorismo",
            7: "🎓 Educação & Ensino",
            8: "🌐 Geral & Outros"
        }

        session['data']['category'] = categorias[categoria_num]

        # Criar a equipe
        await self.create_team(message, session)

    async def create_team(self, message, session):
        """Cria a equipe efetivamente"""
        try:
            guild = message.guild
            user = message.author
            data = session['data']

            nome = data['name']
            descricao = data['description']
            categoria = data['category']

            # Criar role da equipe
            team_color = discord.Color.random()
            team_role = await guild.create_role(
                name=f"Equipe {nome}",
                color=team_color,
                mentionable=True,
                reason=f"Equipe criada por {user}"
            )

            # Criar role de líder
            leader_role = await guild.create_role(
                name=f"Líder {nome}",
                color=team_color,
                mentionable=False,
                reason=f"Role de líder da equipe {nome}"
            )

            # Adicionar roles ao criador
            await user.add_roles(team_role, leader_role, reason="Criador da equipe")

            # Buscar ou criar categoria "EQUIPES"
            teams_category = discord.utils.get(guild.categories, name="🏆 EQUIPES")
            if not teams_category:
                teams_category = await guild.create_category(
                    "🏆 EQUIPES",
                    reason="Categoria para equipes"
                )

            # Buscar ou criar categoria "LIDERANÇA"
            leader_category = discord.utils.get(guild.categories, name="👑 LIDERANÇA")
            if not leader_category:
                leader_category = await guild.create_category(
                    "👑 LIDERANÇA",
                    reason="Categoria para canais de liderança"
                )

            nome_limpo = ''.join(c for c in nome.lower() if c.isalnum() or c in ['-', '_']).replace(' ', '-')

            # Configurar permissões para canais da equipe
            team_overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                team_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    connect=True,
                    speak=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )
            }

            # Configurar permissões para canal do líder
            leader_overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                leader_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )
            }

            # Criar canais da equipe
            text_channel = await guild.create_text_channel(
                f"💬│{nome_limpo}",
                category=teams_category,
                overwrites=team_overwrites,
                topic=f"Canal da equipe {nome} - {descricao}",
                reason=f"Canal da equipe criado por {user}"
            )

            voice_channel = await guild.create_voice_channel(
                f"🔊│{nome_limpo}",
                category=teams_category,
                overwrites=team_overwrites,
                reason=f"Canal de voz da equipe criado por {user}"
            )

            # Criar canal do líder
            leader_channel = await guild.create_text_channel(
                f"👑│{nome_limpo}-lider",
                category=leader_category,
                overwrites=leader_overwrites,
                topic=f"Canal de gerenciamento da equipe {nome} - Apenas para o líder",
                reason=f"Canal de liderança criado por {user}"
            )

            # Embed de sucesso
            success_embed = discord.Embed(
                title="🎉 Equipe Criada com Sucesso!",
                description=f"Parabéns! A equipe **{nome}** foi criada!",
                color=team_color
            )

            success_embed.add_field(
                name="📋 Informações da Equipe",
                value=f"""
                **Nome:** {nome}
                **Categoria:** {categoria}
                **Líder:** {user.mention}
                **Membros:** 1/6
                """,
                inline=False
            )

            success_embed.add_field(
                name="📍 Canais Criados",
                value=f"""
                **Equipe:** {text_channel.mention}
                **Voz:** {voice_channel.mention}
                **Liderança:** {leader_channel.mention}
                """,
                inline=False
            )

            success_embed.add_field(
                name="📝 Descrição",
                value=descricao,
                inline=False
            )

            success_embed.set_footer(text="Use o canal de liderança para gerenciar sua equipe!")

            await message.channel.send(embed=success_embed)

            # Configurar canal de liderança
            await self.setup_leader_channel(leader_channel, nome, user.id, team_color, descricao)

            # Mensagem de boas-vindas no canal da equipe
            welcome_embed = discord.Embed(
                title=f"🎉 Bem-vindos à Equipe {nome}!",
                description=f"""
                **{categoria}**

                {descricao}

                **👑 Líder:** {user.mention}
                **👥 Membros:** 1/6

                **🎯 Como funciona:**
                • Use este canal para conversas da equipe
                • Use o canal de voz para reuniões
                • O líder pode adicionar até 5 membros
                • Trabalhem juntos em seus projetos!

                Boa sorte! 🚀
                """,
                color=team_color
            )

            await text_channel.send(embed=welcome_embed)

            # Limpar sessão e deletar canal temporário
            await asyncio.sleep(5)
            await session['channel'].delete(reason="Criação de equipe concluída")
            del self.user_sessions[user.id]

            self.logger.info(f"Equipe '{nome}' criada por {user.id} ({user.name})")

        except Exception as e:
            self.logger.error(f"Erro ao criar equipe", exc_info=e)
            await message.channel.send("❌ Erro ao criar equipe. Tente novamente mais tarde.")

    async def setup_leader_channel(self, channel, team_name, leader_id, color, description):
        """Configura o canal de liderança com painel de controle"""
        embed = discord.Embed(
            title=f"👑 Painel de Liderança - {team_name}",
            description=f"""**Bem-vindo ao seu painel de liderança!**

Aqui você pode gerenciar sua equipe completamente.

**📋 Informações Atuais:**
• **Nome:** {team_name}
• **Descrição:** {description}
• **Membros:** 1/6
• **Status:** Ativa

**🎮 Use os botões abaixo para:**
• ➕ Adicionar membros (máximo 6 total)
• ➖ Remover membros
• ✏️ Editar informações da equipe
• 🗑️ Deletar a equipe permanentemente

**⚠️ Importante:**
• Apenas você pode usar estes controles
• Mudanças são aplicadas imediatamente
• A exclusão da equipe é irreversível""",
            color=color
        )

        embed.set_footer(text="Sistema de Equipes | Liderança")

        view = TeamManagementView(team_name, leader_id)
        await channel.send(embed=embed, view=view)

    async def cancel_team_creation(self, user, channel):
        """Cancela a criação de equipe"""
        try:
            embed = discord.Embed(
                title="❌ Criação Cancelada",
                description="A criação da equipe foi cancelada. Este canal será deletado em alguns segundos.",
                color=discord.Color.red()
            )

            await channel.send(embed=embed)

            await asyncio.sleep(3)
            await channel.delete(reason="Criação de equipe cancelada")

            if user.id in self.user_sessions:
                del self.user_sessions[user.id]

        except Exception as e:
            self.logger.error(f"Erro ao cancelar criação de equipe", exc_info=e)

    async def start_add_member(self, interaction, team_name):
        """Inicia processo de adicionar membro"""
        await interaction.response.send_message(
            "📝 **Digite o @mention ou ID do usuário que deseja adicionar:**\n\n"
            "Exemplo: `@usuario` ou `123456789`\n\n"
            "❌ Digite `cancelar` para cancelar.",
            ephemeral=True
        )

        # Aguardar resposta
        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            message = await self.bot.wait_for('message', check=check, timeout=60.0)

            if message.content.lower() == 'cancelar':
                await message.delete()
                return

            # Processar menção ou ID
            member = None
            content = message.content.strip()

            # Tentar extrair ID da menção
            if content.startswith('<@') and content.endswith('>'):
                user_id = content[2:-1]
                if user_id.startswith('!'):
                    user_id = user_id[1:]
                try:
                    member = interaction.guild.get_member(int(user_id))
                except:
                    pass
            else:
                # Tentar como ID direto
                try:
                    member = interaction.guild.get_member(int(content))
                except:
                    pass

            await message.delete()

            if not member:
                await interaction.followup.send("❌ Usuário não encontrado!", ephemeral=True)
                return

            await self.confirm_add_member(interaction, member, team_name)

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado!", ephemeral=True)

    async def confirm_add_member(self, interaction, member, team_name):
        """Confirma adição de membro"""
        guild = interaction.guild
        team_role = discord.utils.get(guild.roles, name=f"Equipe {team_name}")

        if not team_role:
            await interaction.followup.send("❌ Equipe não encontrada!", ephemeral=True)
            return

        # Verificar se já é membro
        if team_role in member.roles:
            await interaction.followup.send(f"❌ {member.mention} já faz parte desta equipe!", ephemeral=True)
            return

        # Verificar limite de membros
        current_members = len([m for m in guild.members if team_role in m.roles])
        if current_members >= 6:
            await interaction.followup.send("❌ A equipe já tem o máximo de 6 membros!", ephemeral=True)
            return

        # Adicionar membro
        try:
            await member.add_roles(team_role, reason=f"Adicionado à equipe {team_name} pelo líder")

            embed = discord.Embed(
                title="✅ Membro Adicionado!",
                description=f"{member.mention} foi adicionado à equipe **{team_name}**!",
                color=discord.Color.green()
            )

            new_count = current_members + 1
            embed.add_field(name="👥 Membros", value=f"{new_count}/6", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

            # Notificar no canal da equipe
            team_channel = discord.utils.get(guild.text_channels, name=f"💬│{team_name.lower().replace(' ', '-')}")
            if team_channel:
                welcome_msg = discord.Embed(
                    title="👥 Novo Membro!",
                    description=f"Bem-vindo {member.mention} à equipe **{team_name}**! 🎉",
                    color=team_role.color
                )
                await team_channel.send(embed=welcome_msg)

        except Exception as e:
            self.logger.error(f"Erro ao adicionar membro {member.id} à equipe {team_name}", exc_info=e)
            await interaction.followup.send("❌ Erro ao adicionar membro!", ephemeral=True)

    async def start_remove_member(self, interaction, team_name):
        """Inicia processo de remover membro"""
        guild = interaction.guild
        team_role = discord.utils.get(guild.roles, name=f"Equipe {team_name}")
        leader_role = discord.utils.get(guild.roles, name=f"Líder {team_name}")

        if not team_role:
            await interaction.response.send_message("❌ Equipe não encontrada!", ephemeral=True)
            return

        # Buscar membros (exceto o líder)
        members = [m for m in guild.members if team_role in m.roles and leader_role not in m.roles]

        if not members:
            await interaction.response.send_message("❌ Não há membros para remover (além do líder)!", ephemeral=True)
            return

        # Criar select menu
        view = MemberSelectView(members, "remover", team_name, interaction.user.id)
        await interaction.response.send_message("👥 **Selecione o membro para remover:**", view=view, ephemeral=True)

    async def confirm_remove_member(self, interaction, member, team_name):
        """Confirma remoção de membro"""
        guild = interaction.guild
        team_role = discord.utils.get(guild.roles, name=f"Equipe {team_name}")

        try:
            await member.remove_roles(team_role, reason=f"Removido da equipe {team_name} pelo líder")

            embed = discord.Embed(
                title="✅ Membro Removido!",
                description=f"{member.mention} foi removido da equipe **{team_name}**.",
                color=discord.Color.orange()
            )

            current_members = len([m for m in guild.members if team_role in m.roles])
            embed.add_field(name="👥 Membros", value=f"{current_members}/6", inline=True)

            try:
                await interaction.response.edit_message(content=None, embed=embed, view=None)
            except discord.NotFound:
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Erro ao remover membro {member.id} da equipe {team_name}", exc_info=e)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Erro ao remover membro!", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Erro ao remover membro!", ephemeral=True)
            except:
                pass

    async def start_edit_team(self, interaction, team_name):
        """Inicia edição de informações da equipe"""
        await interaction.response.send_message(
            "🚧 **Funcionalidade em desenvolvimento!**\n\n"
            "Em breve você poderá editar:\n"
            "• Nome da equipe\n"
            "• Descrição\n"
            "• Categoria",
            ephemeral=True
        )

    async def delete_team(self, interaction, team_name):
        """Deleta a equipe completamente"""
        try:
            guild = interaction.guild

            # Buscar roles
            team_role = discord.utils.get(guild.roles, name=f"Equipe {team_name}")
            leader_role = discord.utils.get(guild.roles, name=f"Líder {team_name}")

            # Buscar canais
            nome_limpo = ''.join(c for c in team_name.lower() if c.isalnum() or c in ['-', '_']).replace(' ', '-')
            text_channel = discord.utils.get(guild.text_channels, name=f"💬│{nome_limpo}")
            voice_channel = discord.utils.get(guild.voice_channels, name=f"🔊│{nome_limpo}")
            leader_channel = discord.utils.get(guild.text_channels, name=f"👑│{nome_limpo}-lider")

            deleted_items = []

            # Deletar canais
            if text_channel:
                await text_channel.delete(reason=f"Equipe {team_name} deletada pelo líder")
                deleted_items.append("Canal de texto")

            if voice_channel:
                await voice_channel.delete(reason=f"Equipe {team_name} deletada pelo líder")
                deleted_items.append("Canal de voz")

            if leader_channel:
                await leader_channel.delete(reason=f"Equipe {team_name} deletada pelo líder")
                deleted_items.append("Canal de liderança")

            # Deletar roles
            if team_role:
                await team_role.delete(reason=f"Equipe {team_name} deletada pelo líder")
                deleted_items.append("Role da equipe")

            if leader_role:
                await leader_role.delete(reason=f"Equipe {team_name} deletada pelo líder")
                deleted_items.append("Role de líder")

            # Embed de sucesso
            embed = discord.Embed(
                title="🗑️ Equipe Deletada!",
                description=f"A equipe **{team_name}** foi completamente removida.",
                color=discord.Color.red()
            )

            embed.add_field(
                name="📝 Itens Removidos",
                value="\n".join([f"• {item}" for item in deleted_items]),
                inline=False
            )

            try:
                await interaction.response.edit_message(embed=embed, view=None)
            except discord.NotFound:
                # Se a mensagem não existir mais, criar uma nova resposta
                await interaction.followup.send(embed=embed, ephemeral=True)

            self.logger.info(f"Equipe '{team_name}' deletada pelo líder {interaction.user.id}")

        except Exception as e:
            self.logger.error(f"Erro ao deletar equipe {team_name}", exc_info=e)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Erro ao deletar equipe!", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Erro ao deletar equipe!", ephemeral=True)
            except:
                pass