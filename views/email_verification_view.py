import discord
from discord.ext import commands

class EmailVerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📧 Verificar Email",
        style=discord.ButtonStyle.secondary,
        custom_id="verify_email"
    )
    async def verify_email(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Inicia o processo de verificação por email"""
        # Criar canal privado para verificação
        category = discord.utils.get(interaction.guild.categories, name="NASA Space Apps - Verificações")
        
        if not category:
            # Criar categoria se não existir
            category = await interaction.guild.create_category("NASA Space Apps - Verificações")
        
        # Nome do canal
        channel_name = f"verificacao-{interaction.user.name.lower().replace(' ', '-')}"
        
        # Verificar se já existe um canal para este usuário
        existing_channel = discord.utils.get(category.channels, name=channel_name)
        if existing_channel:
            embed = discord.Embed(
                title="⚠️ Canal já existe",
                description=f"Você já possui um canal de verificação ativo: {existing_channel.mention}",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Criar canal privado
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        private_channel = await category.create_text_channel(
            channel_name,
            overwrites=overwrites,
            topic=f"Canal de verificação por email para {interaction.user.display_name}"
        )
        
        # Iniciar processo de verificação por email
        from handlers.email_verification_handler import EmailVerificationHandler
        handler = EmailVerificationHandler(interaction.client)
        await handler.start_email_verification_process(private_channel, interaction.user)
        
        # Responder ao usuário
        embed = discord.Embed(
            title="✅ Canal de Verificação Criado!",
            description=f"Seu canal de verificação foi criado: {private_channel.mention}\n\nVá até lá para verificar seu email e acessar suas informações de inscrição.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)