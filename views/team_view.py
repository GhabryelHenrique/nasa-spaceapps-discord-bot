import discord
from discord.ext import commands

class TeamRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Criar Equipe',
        style=discord.ButtonStyle.primary,
        emoji='🏆',
        custom_id='create_team_button'
    )
    async def create_team_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para iniciar criação de equipe"""
        try:
            # Verificar se já está criando uma equipe
            bot = interaction.client
            if hasattr(bot, 'team_handler') and bot.team_handler:
                # Verificar se usuário já tem sessão ativa
                if interaction.user.id in bot.team_handler.user_sessions:
                    await interaction.response.send_message(
                        "❌ Você já tem uma criação de equipe em andamento! Complete ou cancele a atual primeiro.",
                        ephemeral=True
                    )
                    return

                # Verificar se usuário já é líder de uma equipe
                guild = interaction.guild
                leader_roles = [role for role in interaction.user.roles if role.name.startswith("Líder ")]
                if leader_roles:
                    await interaction.response.send_message(
                        f"❌ Você já é líder da equipe **{leader_roles[0].name.replace('Líder ', '')}**! Cada usuário pode liderar apenas uma equipe.",
                        ephemeral=True
                    )
                    return

                # Iniciar processo de criação
                await bot.team_handler.start_team_creation(interaction)
            else:
                await interaction.response.send_message(
                    "❌ Sistema de equipes não está disponível no momento.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"Erro no botão de criar equipe: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ Erro interno. Tente novamente mais tarde.",
                        ephemeral=True
                    )
            except:
                pass

class TeamManagementView(discord.ui.View):
    def __init__(self, team_name: str, leader_id: int):
        super().__init__(timeout=None)
        self.team_name = team_name
        self.leader_id = leader_id

    @discord.ui.button(
        label='Adicionar Membro',
        style=discord.ButtonStyle.success,
        emoji='➕',
        custom_id='add_team_member'
    )
    async def add_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para adicionar membro à equipe"""
        if interaction.user.id != self.leader_id:
            await interaction.response.send_message("❌ Apenas o líder da equipe pode usar este botão!", ephemeral=True)
            return

        try:
            bot = interaction.client
            if hasattr(bot, 'team_handler') and bot.team_handler:
                await bot.team_handler.start_add_member(interaction, self.team_name)
            else:
                await interaction.response.send_message("❌ Sistema indisponível.", ephemeral=True)
        except Exception as e:
            print(f"Erro ao adicionar membro: {e}")
            await interaction.response.send_message("❌ Erro interno.", ephemeral=True)

    @discord.ui.button(
        label='Remover Membro',
        style=discord.ButtonStyle.danger,
        emoji='➖',
        custom_id='remove_team_member'
    )
    async def remove_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para remover membro da equipe"""
        if interaction.user.id != self.leader_id:
            await interaction.response.send_message("❌ Apenas o líder da equipe pode usar este botão!", ephemeral=True)
            return

        try:
            bot = interaction.client
            if hasattr(bot, 'team_handler') and bot.team_handler:
                await bot.team_handler.start_remove_member(interaction, self.team_name)
            else:
                await interaction.response.send_message("❌ Sistema indisponível.", ephemeral=True)
        except Exception as e:
            print(f"Erro ao remover membro: {e}")
            await interaction.response.send_message("❌ Erro interno.", ephemeral=True)

    @discord.ui.button(
        label='Editar Equipe',
        style=discord.ButtonStyle.secondary,
        emoji='✏️',
        custom_id='edit_team_info'
    )
    async def edit_team_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para editar informações da equipe"""
        if interaction.user.id != self.leader_id:
            await interaction.response.send_message("❌ Apenas o líder da equipe pode usar este botão!", ephemeral=True)
            return

        try:
            bot = interaction.client
            if hasattr(bot, 'team_handler') and bot.team_handler:
                await bot.team_handler.start_edit_team(interaction, self.team_name)
            else:
                await interaction.response.send_message("❌ Sistema indisponível.", ephemeral=True)
        except Exception as e:
            print(f"Erro ao editar equipe: {e}")
            await interaction.response.send_message("❌ Erro interno.", ephemeral=True)

    @discord.ui.button(
        label='Deletar Equipe',
        style=discord.ButtonStyle.danger,
        emoji='🗑️',
        custom_id='delete_team',
        row=1
    )
    async def delete_team_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para deletar a equipe"""
        if interaction.user.id != self.leader_id:
            await interaction.response.send_message("❌ Apenas o líder da equipe pode usar este botão!", ephemeral=True)
            return

        # Confirmar exclusão
        embed = discord.Embed(
            title="⚠️ Confirmar Exclusão",
            description=f"Tem certeza que deseja **DELETAR PERMANENTEMENTE** a equipe **{self.team_name}**?\n\n**Esta ação não pode ser desfeita!**\n\nIsso irá:\n• Deletar todos os canais da equipe\n• Remover todas as roles da equipe\n• Remover todos os membros",
            color=discord.Color.red()
        )

        confirm_view = TeamDeleteConfirmView(self.team_name, self.leader_id)
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class TeamDeleteConfirmView(discord.ui.View):
    def __init__(self, team_name: str, leader_id: int):
        super().__init__(timeout=60)
        self.team_name = team_name
        self.leader_id = leader_id

    @discord.ui.button(
        label='SIM, DELETAR',
        style=discord.ButtonStyle.danger,
        emoji='✅'
    )
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirmar exclusão da equipe"""
        if interaction.user.id != self.leader_id:
            await interaction.response.send_message("❌ Apenas o líder pode confirmar!", ephemeral=True)
            return

        try:
            bot = interaction.client
            if hasattr(bot, 'team_handler') and bot.team_handler:
                await bot.team_handler.delete_team(interaction, self.team_name)
            else:
                await interaction.response.send_message("❌ Sistema indisponível.", ephemeral=True)
        except Exception as e:
            print(f"Erro ao deletar equipe: {e}")
            await interaction.response.send_message("❌ Erro interno.", ephemeral=True)

    @discord.ui.button(
        label='Cancelar',
        style=discord.ButtonStyle.secondary,
        emoji='❌'
    )
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancelar exclusão"""
        embed = discord.Embed(
            title="✅ Exclusão Cancelada",
            description="A exclusão da equipe foi cancelada.",
            color=discord.Color.green()
        )
        try:
            await interaction.response.edit_message(embed=embed, view=None)
        except discord.NotFound:
            await interaction.followup.send(embed=embed, ephemeral=True)

class MemberSelectView(discord.ui.View):
    def __init__(self, members: list, action: str, team_name: str, leader_id: int):
        super().__init__(timeout=60)
        self.action = action
        self.team_name = team_name
        self.leader_id = leader_id

        # Criar select menu com membros
        options = []
        for member in members[:25]:  # Discord limit
            options.append(discord.SelectOption(
                label=member.display_name,
                description=f"@{member.name}",
                value=str(member.id)
            ))

        if options:
            select = discord.ui.Select(
                placeholder=f"Selecione um membro para {action}...",
                options=options,
                custom_id=f"{action}_member_select"
            )
            select.callback = self.member_selected
            self.add_item(select)

    async def member_selected(self, interaction: discord.Interaction):
        """Callback quando membro é selecionado"""
        if interaction.user.id != self.leader_id:
            await interaction.response.send_message("❌ Apenas o líder pode usar isto!", ephemeral=True)
            return

        try:
            member_id = int(interaction.data['values'][0])
            member = interaction.guild.get_member(member_id)

            if not member:
                await interaction.response.send_message("❌ Membro não encontrado!", ephemeral=True)
                return

            bot = interaction.client
            if hasattr(bot, 'team_handler') and bot.team_handler:
                if self.action == "remover":
                    await bot.team_handler.confirm_remove_member(interaction, member, self.team_name)
                elif self.action == "adicionar":
                    await bot.team_handler.confirm_add_member(interaction, member, self.team_name)
            else:
                await interaction.response.send_message("❌ Sistema indisponível.", ephemeral=True)

        except Exception as e:
            print(f"Erro na seleção de membro: {e}")
            await interaction.response.send_message("❌ Erro interno.", ephemeral=True)