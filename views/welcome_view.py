import discord
from discord.ext import commands

class WelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='📋 Ver Regras',
        style=discord.ButtonStyle.secondary,
        emoji='📋',
        custom_id='welcome_rules'
    )
    async def view_rules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para ver as regras do servidor"""
        try:
            # Buscar canal de regras
            rules_channel = discord.utils.get(interaction.guild.text_channels, name="regras")

            embed = discord.Embed(
                title="📋 Regras do Servidor",
                description=f"Confira as regras em {rules_channel.mention if rules_channel else '#regras'}\n\n**Resumo das principais regras:**",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="🤝 Respeito e Colaboração",
                value="• Seja respeitoso com todos os participantes\n• Não toleramos discriminação ou assédio\n• Ajude outros participantes quando possível",
                inline=False
            )

            embed.add_field(
                name="💬 Comunicação",
                value="• Use os canais apropriados para cada assunto\n• Evite spam e mensagens repetitivas\n• Use português ou inglês nas conversas",
                inline=False
            )

            embed.add_field(
                name="🏆 Competição Justa",
                value="• Não copie soluções de outras equipes\n• Use apenas dados públicos da NASA\n• Respeite os prazos estabelecidos",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Erro ao carregar regras. Verifique o canal #regras.", ephemeral=True)

    @discord.ui.button(
        label='🤖 Solicitar Mentoria',
        style=discord.ButtonStyle.primary,
        emoji='🤖',
        custom_id='welcome_mentorship'
    )
    async def request_mentorship_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para solicitar mentoria"""
        try:
            embed = discord.Embed(
                title="🤖 Sistema de Mentoria",
                description="Use nosso sistema integrado para solicitar ajuda de mentores experientes!",
                color=discord.Color.green()
            )

            embed.add_field(
                name="Como Funcionar",
                value="1. Use o comando `/mentoria`\n2. Preencha o formulário simples\n3. Aguarde um mentor assumir sua solicitação\n4. Receba ajuda personalizada!",
                inline=False
            )

            embed.add_field(
                name="Áreas Disponíveis",
                value="🔬 Ciências Exatas • 🧬 Ciências Biológicas\n⚙️ Engenharias • 🌍 Ciências da Terra\n💻 Programação e Tecnologia",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Erro ao carregar informações de mentoria.", ephemeral=True)

    @discord.ui.button(
        label='👥 Criar/Buscar Equipe',
        style=discord.ButtonStyle.success,
        emoji='👥',
        custom_id='welcome_teams'
    )
    async def teams_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para informações sobre equipes"""
        try:
            embed = discord.Embed(
                title="👥 Sistema de Equipes",
                description="Monte sua equipe dos sonhos para o hackathon!",
                color=discord.Color.orange()
            )

            embed.add_field(
                name="🏆 Criando uma Equipe",
                value="• Use o botão **'Criar Equipe'** nos painéis\n• Escolha um nome único e criativo\n• Defina a descrição e objetivos\n• Gerencie membros pelo painel de liderança",
                inline=False
            )

            embed.add_field(
                name="🔍 Procurando Equipe",
                value="• Visite o canal #equipes\n• Veja apresentações de equipes\n• Entre em contato com líderes\n• Participe de até 6 pessoas por equipe",
                inline=False
            )

            embed.add_field(
                name="⚡ Dica Importante",
                value="Forme sua equipe cedo para ter mais tempo de planejamento e integração!",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Erro ao carregar informações de equipes.", ephemeral=True)

    @discord.ui.button(
        label='📝 Se Apresentar',
        style=discord.ButtonStyle.secondary,
        emoji='📝',
        custom_id='welcome_introduce'
    )
    async def introduce_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para se apresentar"""
        try:
            # Buscar canal de apresentações
            intro_channel = discord.utils.get(interaction.guild.text_channels, name="apresente-se")

            embed = discord.Embed(
                title="📝 Hora de se Apresentar!",
                description=f"Vá até {intro_channel.mention if intro_channel else '#apresente-se'} e conte para todos:",
                color=discord.Color.purple()
            )

            embed.add_field(
                name="💫 Fale sobre você",
                value="""
• **Nome** e de onde você é
• **Área de formação** ou interesse
• **Experiência** em hackathons
• **O que espera** do evento
• **Hobbies** ou curiosidades
                """,
                inline=False
            )

            embed.add_field(
                name="🎯 Exemplo de Apresentação",
                value="""
*"Oi pessoal! Sou João, estudante de Engenharia da Computação em Uberlândia. É meu primeiro Space Apps, mas já participei de outros hackathons. Adoro astronomia e programação. Espero formar uma equipe incrível e aprender muito! 🚀"*
                """,
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Erro ao carregar informações de apresentação.", ephemeral=True)