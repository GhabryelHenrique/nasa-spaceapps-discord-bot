import discord
from discord.ext import commands
from utils.logger import get_logger

class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.logger = get_logger()

    @discord.ui.button(
        label="🚀 Fazer Inscrição NASA Space Apps",
        style=discord.ButtonStyle.primary,
        custom_id="start_registration"
    )
    async def start_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Inicia o processo de inscrição"""
        try:
            self.logger.log_user_action(interaction.user.id, 'botão_inscrição', f'Servidor: {interaction.guild.name}')
            
            # Usar o handler do bot que mantém as sessões
            handler = interaction.client.registration_handler
            is_registered = await handler.check_existing_registration(interaction.user.id)
            
            if is_registered:
                self.logger.info(f'Usuário {interaction.user.id} tentou se inscrever mas já está registrado')
                embed = discord.Embed(
                    title="❌ Já Inscrito",
                    description="Você já possui uma inscrição ativa no NASA Space Apps Challenge!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Criar canal privado para o usuário
            category = discord.utils.get(interaction.guild.categories, name="NASA Space Apps - Inscrições")
            
            if not category:
                # Criar categoria se não existir
                category = await interaction.guild.create_category("NASA Space Apps - Inscrições")
            
            # Nome do canal
            channel_name = f"inscricao-{interaction.user.name.lower().replace(' ', '-')}"
            
            # Verificar se já existe um canal para este usuário
            existing_channel = discord.utils.get(category.channels, name=channel_name)
            if existing_channel:
                self.logger.info(f'Usuário {interaction.user.id} tentou criar canal de inscrição mas já existe: {existing_channel.name}')
                embed = discord.Embed(
                    title="⚠️ Canal já existe",
                    description=f"Você já possui um canal de inscrição ativo: {existing_channel.mention}",
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
                topic=f"Canal de inscrição para {interaction.user.display_name}"
            )
            
            self.logger.info(f'Canal de inscrição criado para usuário {interaction.user.id}: {private_channel.name}')
            
            # Iniciar processo de inscrição
            await handler.start_registration_process(private_channel, interaction.user)
            
            # Responder ao usuário
            embed = discord.Embed(
                title="✅ Canal Criado!",
                description=f"Seu canal de inscrição foi criado: {private_channel.mention}\n\nVá até lá para completar sua inscrição no NASA Space Apps Challenge!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f'Erro ao processar botão de inscrição para usuário {interaction.user.id}', exc_info=e)
            
            try:
                error_embed = discord.Embed(
                    title="❌ Erro",
                    description="Ocorreu um erro ao processar sua solicitação. Tente novamente ou contate um administrador.",
                    color=discord.Color.red()
                )
                if interaction.response.is_done():
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except:
                pass

    @discord.ui.button(
        label="📧 Já Estou Inscrito",
        style=discord.ButtonStyle.secondary,
        custom_id="verify_existing_registration"
    )
    async def verify_existing_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Verifica uma inscrição existente por email"""
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
                title="Canal já existe",
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
            title="Canal de Verificação Criado!",
            description=f"Seu canal de verificação foi criado: {private_channel.mention}\n\nVá até lá para verificar seu email e acessar suas informações de inscrição.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="🔍 Buscar Equipes",
        style=discord.ButtonStyle.secondary,
        custom_id="search_teams",
        emoji="🔍"
    )
    async def search_teams(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Abre o sistema de busca de equipes"""
        embed = discord.Embed(
            title="🔍 Sistema de Busca de Equipes",
            description="""**Encontre a equipe perfeita para o NASA Space Apps Challenge!**

🔍 **Ver Equipes Disponíveis** - Veja todas as equipes que estão procurando membros
💼 **Marcar Como Disponível** - Se marque como disponível para outras equipes te convidarem
👥 **Ver Pessoas Disponíveis** - (Apenas líderes) Veja pessoas procurando equipes

**Como funciona:**
1. Marque-se como disponível e descreva suas habilidades
2. Procure equipes que combinem com você
3. Envie uma aplicação explicando por que quer se juntar
4. Aguarde a resposta do líder da equipe
5. Se aprovado, você será transferido para a nova equipe!

**Comandos úteis:**
• `/equipes` - Abrir este painel
• `/aplicacoes` - Gerenciar aplicações (líderes)
• `/minhas_aplicacoes` - Ver suas aplicações

**Importante:** Você pode estar em apenas uma equipe por vez.""",
            color=discord.Color.blue()
        )
        embed.set_footer(text="NASA Space Apps Challenge 2025 - Sistema de Equipes")
        
        from views.team_search_view import TeamSearchView
        view = TeamSearchView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)