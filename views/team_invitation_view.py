import discord
from discord.ext import commands

class TeamInvitationView(discord.ui.View):
    def __init__(self, team_role, team_data, leader_id, invited_member_id):
        super().__init__(timeout=3600)  # 1 hora para responder
        self.team_role = team_role
        self.team_data = team_data
        self.leader_id = leader_id
        self.invited_member_id = invited_member_id

    @discord.ui.button(
        label="✅ Aceitar Convite",
        style=discord.ButtonStyle.success,
        custom_id="accept_team_invitation"
    )
    async def accept_invitation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Aceita o convite para a equipe"""
        if interaction.user.id != self.invited_member_id:
            await interaction.response.send_message("Este convite não é para você!", ephemeral=True)
            return
        
        try:
            # Adicionar role ao membro
            member = interaction.guild.get_member(self.invited_member_id)
            if member:
                await member.add_roles(self.team_role, reason="Convite aceito para equipe")
                
                # Resposta de confirmação
                embed = discord.Embed(
                    title="Convite Aceito! 🎉",
                    description=f"""Você foi adicionado à **{self.team_data['nome_equipe']}**!

**Informações da Equipe:**
• **Líder:** <@{self.leader_id}>
• **Nome da Equipe:** {self.team_data['nome_equipe']}
• **Modalidade:** {self.team_data['modalidade'].value}

Agora você tem acesso aos canais exclusivos da equipe. Boa sorte no NASA Space Apps Challenge! 🚀""",
                    color=discord.Color.green()
                )
                embed.set_footer(text="NASA Space Apps Challenge 2024 - Uberlândia")
                
                # Desabilitar botões
                self.accept_invitation.disabled = True
                self.decline_invitation.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self)
                
                # Notificar o líder da equipe
                try:
                    leader = interaction.guild.get_member(self.leader_id)
                    if leader:
                        leader_embed = discord.Embed(
                            title="Membro Aceitou o Convite! ✅",
                            description=f"**{member.display_name}** aceitou o convite para a equipe **{self.team_data['nome_equipe']}**!",
                            color=discord.Color.green()
                        )
                        await leader.send(embed=leader_embed)
                except:
                    pass  # Não falhar se não conseguir enviar DM ao líder
                
            else:
                await interaction.response.send_message("Erro: Não foi possível encontrar você no servidor.", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"Erro ao aceitar convite: {str(e)}", ephemeral=True)
            print(f"Erro ao aceitar convite da equipe: {e}")

    @discord.ui.button(
        label="❌ Recusar Convite",
        style=discord.ButtonStyle.danger,
        custom_id="decline_team_invitation"
    )
    async def decline_invitation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Recusa o convite para a equipe"""
        if interaction.user.id != self.invited_member_id:
            await interaction.response.send_message("Este convite não é para você!", ephemeral=True)
            return
        
        try:
            # Resposta de confirmação
            embed = discord.Embed(
                title="Convite Recusado",
                description=f"Você recusou o convite para a equipe **{self.team_data['nome_equipe']}**.\n\nSe mudar de ideia, entre em contato com o líder da equipe: <@{self.leader_id}>",
                color=discord.Color.red()
            )
            embed.set_footer(text="NASA Space Apps Challenge 2024 - Uberlândia")
            
            # Desabilitar botões
            self.accept_invitation.disabled = True
            self.decline_invitation.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            # Notificar o líder da equipe
            try:
                leader = interaction.guild.get_member(self.leader_id)
                member = interaction.guild.get_member(self.invited_member_id)
                if leader and member:
                    leader_embed = discord.Embed(
                        title="Membro Recusou o Convite ❌",
                        description=f"**{member.display_name}** recusou o convite para a equipe **{self.team_data['nome_equipe']}**.",
                        color=discord.Color.red()
                    )
                    await leader.send(embed=leader_embed)
            except:
                pass  # Não falhar se não conseguir enviar DM ao líder
                
        except Exception as e:
            await interaction.response.send_message(f"Erro ao recusar convite: {str(e)}", ephemeral=True)
            print(f"Erro ao recusar convite da equipe: {e}")

    async def on_timeout(self):
        """Executado quando o tempo limite é atingido"""
        try:
            # Desabilitar todos os botões
            for item in self.children:
                item.disabled = True
            
            # Notificar que o convite expirou
            embed = discord.Embed(
                title="Convite Expirado ⏰",
                description=f"O convite para a equipe **{self.team_data['nome_equipe']}** expirou.\n\nSe ainda tem interesse, entre em contato com o líder da equipe: <@{self.leader_id}>",
                color=discord.Color.orange()
            )
            embed.set_footer(text="NASA Space Apps Challenge 2024 - Uberlândia")
            
            # Tentar editar a mensagem original
            # Nota: Isso pode não funcionar se a mensagem for muito antiga
            # mas é uma boa prática tentar
            
        except Exception as e:
            print(f"Erro ao processar timeout do convite: {e}")