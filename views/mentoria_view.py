import discord

class MentoriaRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Solicitar Ajuda',
        style=discord.ButtonStyle.primary,
        emoji='🆘'
    )
    async def solicitar_ajuda(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Inicia o processo de solicitação de mentoria"""
        try:
            # Verificar se há um handler de mentoria
            bot = interaction.client
            if not hasattr(bot, 'mentoria_handler'):
                await interaction.response.send_message(
                    "❌ Sistema de mentoria não está disponível no momento.",
                    ephemeral=True
                )
                return
            
            # Criar canal privado ou usar DM
            try:
                # Tentar criar canal privado no servidor
                guild = interaction.guild
                if guild:
                    category = discord.utils.get(guild.categories, name='Solicitações Mentoria')
                    
                    # Criar categoria se não existir
                    if not category:
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                        }
                        category = await guild.create_category_channel('Solicitações Mentoria', overwrites=overwrites)
                    
                    # Verificar se usuário já tem canal aberto
                    existing_channel = discord.utils.get(
                        category.channels, 
                        name=f'mentoria-{interaction.user.name.lower()}'
                    )
                    
                    if existing_channel:
                        embed = discord.Embed(
                            title="📝 Canal já existe",
                            description=f"Você já tem um canal de solicitação aberto: {existing_channel.mention}",
                            color=discord.Color.orange()
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    
                    # Criar canal privado
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }
                    
                    # Adicionar mentores ao canal se existir papel
                    mentor_role = discord.utils.get(guild.roles, name='Mentor')
                    if mentor_role:
                        overwrites[mentor_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    
                    channel = await category.create_text_channel(
                        f'mentoria-{interaction.user.name.lower()}',
                        overwrites=overwrites
                    )
                    
                    # Iniciar processo de solicitação
                    bot.mentoria_handler.start_mentoria_request(interaction.user.id, interaction.user.display_name)
                    
                    embed = discord.Embed(
                        title="📝 Solicitação de Mentoria",
                        description="Vamos começar! Responda às perguntas para criar sua solicitação.",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="📋 Primeiro passo",
                        value="**Qual é o título da sua solicitação?**\nDê um nome curto e descritivo para sua dúvida ou problema.",
                        inline=False
                    )
                    embed.set_footer(text="Digite 'cancelar' a qualquer momento para interromper.")
                    
                    await channel.send(f"{interaction.user.mention}", embed=embed)
                    
                    response_embed = discord.Embed(
                        title="✅ Canal criado!",
                        description=f"Sua solicitação foi iniciada em {channel.mention}.\nResponda às perguntas para completar sua solicitação.",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=response_embed, ephemeral=True)
                
                else:
                    # Fallback para DM se não estiver em servidor
                    bot.mentoria_handler.start_mentoria_request(interaction.user.id, interaction.user.display_name)
                    
                    embed = discord.Embed(
                        title="📝 Solicitação de Mentoria",
                        description="Vamos começar! Responda às perguntas para criar sua solicitação.",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="📋 Primeiro passo",
                        value="**Qual é o título da sua solicitação?**\nDê um nome curto e descritivo para sua dúvida ou problema.",
                        inline=False
                    )
                    
                    await interaction.user.send(embed=embed)
                    await interaction.response.send_message(
                        "✅ Processo iniciado! Verifique suas mensagens diretas.",
                        ephemeral=True
                    )
            
            except discord.Forbidden:
                # Se não conseguir criar canal, usar DM
                bot.mentoria_handler.start_mentoria_request(interaction.user.id, interaction.user.display_name)
                
                embed = discord.Embed(
                    title="📝 Solicitação de Mentoria",
                    description="Vamos começar! Responda às perguntas para criar sua solicitação.",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="📋 Primeiro passo",
                    value="**Qual é o título da sua solicitação?**\nDê um nome curto e descritivo para sua dúvida ou problema.",
                    inline=False
                )
                
                try:
                    await interaction.user.send(embed=embed)
                    await interaction.response.send_message(
                        "✅ Processo iniciado! Verifique suas mensagens diretas.",
                        ephemeral=True
                    )
                except discord.Forbidden:
                    await interaction.response.send_message(
                        "❌ Não foi possível criar canal nem enviar DM. Verifique suas configurações de privacidade.",
                        ephemeral=True
                    )
        
        except Exception as e:
            await interaction.response.send_message(
                "❌ Erro interno. Tente novamente mais tarde.",
                ephemeral=True
            )
            if hasattr(interaction.client, 'logger'):
                interaction.client.logger.error(f"Erro ao iniciar solicitação de mentoria", exc_info=e)