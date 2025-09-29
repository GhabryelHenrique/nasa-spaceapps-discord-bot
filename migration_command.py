"""
Comando para adicionar a role Participante a todos os membros existentes.
Adicione este código ao bot.py para ter um comando de migração.
"""

import discord
from discord.ext import commands
import asyncio

# Adicione este comando ao seu bot.py

@bot.command(name='migrar_participantes', aliases=['migrate_participants'])
@commands.has_permissions(administrator=True)
async def migrate_participante_role(ctx):
    """Adiciona a role Participante a todos os membros existentes"""
    try:
        guild = ctx.guild
        if not guild:
            await ctx.send("❌ Este comando só pode ser usado em um servidor.")
            return

        # Mensagem de confirmação
        embed = discord.Embed(
            title="⚠️ Migração da Role Participante",
            description=f"""
            **Este comando irá adicionar a role 'Participante' a todos os membros do servidor.**

            📊 **Estatísticas do servidor:**
            • Total de membros: {guild.member_count}
            • Bots serão automaticamente pulados

            ⚠️ **Atenção:**
            • Esta operação pode demorar alguns minutos
            • O bot pode ficar temporariamente lento
            • A operação não pode ser desfeita facilmente

            **Deseja continuar?**
            """,
            color=discord.Color.orange()
        )

        # Criar view de confirmação
        view = MigrationConfirmView(ctx.author.id)
        message = await ctx.send(embed=embed, view=view)

        # Aguardar resposta
        await view.wait()

        if view.value is None:
            embed.color = discord.Color.red()
            embed.title = "❌ Tempo Esgotado"
            embed.description = "Migração cancelada por inatividade."
            await message.edit(embed=embed, view=None)
            return

        if not view.value:
            embed.color = discord.Color.red()
            embed.title = "❌ Migração Cancelada"
            embed.description = "Operação cancelada pelo usuário."
            await message.edit(embed=embed, view=None)
            return

        # Executar migração
        await execute_migration(ctx, message, guild)

    except Exception as e:
        ctx.bot.logger.error(f"Erro no comando de migração", exc_info=e)
        await ctx.send("❌ Erro interno durante a migração.")

class MigrationConfirmView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=30)
        self.value = None
        self.user_id = user_id

    @discord.ui.button(label='✅ Confirmar', style=discord.ButtonStyle.success)
    async def confirm_migration(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode confirmar.", ephemeral=True)
            return

        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label='❌ Cancelar', style=discord.ButtonStyle.danger)
    async def cancel_migration(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode cancelar.", ephemeral=True)
            return

        self.value = False
        self.stop()
        await interaction.response.defer()

async def execute_migration(ctx, message, guild):
    """Executa a migração da role Participante"""
    try:
        # Buscar ou criar role "Participante"
        participante_role = discord.utils.get(guild.roles, name="Participante")

        if not participante_role:
            # Criar role
            embed = discord.Embed(
                title="🔧 Criando Role...",
                description="Criando a role 'Participante'...",
                color=discord.Color.blue()
            )
            await message.edit(embed=embed, view=None)

            participante_role = await guild.create_role(
                name="Participante",
                color=discord.Color(0x87CEEB),  # Azul claro
                reason=f"Role automática criada por {ctx.author} via comando de migração"
            )

        # Estatísticas
        stats = {
            'total_members': len(guild.members),
            'processed': 0,
            'added': 0,
            'already_had': 0,
            'skipped_bots': 0,
            'errors': 0
        }

        # Embed de progresso
        progress_embed = discord.Embed(
            title="🚀 Migração em Andamento...",
            color=discord.Color.blue()
        )

        # Filtrar membros (sem bots)
        members_to_process = [member for member in guild.members if not member.bot]
        stats['total_members'] = len(members_to_process)
        stats['skipped_bots'] = len(guild.members) - len(members_to_process)

        # Processar em lotes
        batch_size = 10
        total_batches = (len(members_to_process) + batch_size - 1) // batch_size

        for batch_num, i in enumerate(range(0, len(members_to_process), batch_size), 1):
            batch = members_to_process[i:i + batch_size]

            # Processar lote
            for member in batch:
                try:
                    if participante_role in member.roles:
                        stats['already_had'] += 1
                    else:
                        await member.add_roles(participante_role, reason="Migração automática - Role Participante")
                        stats['added'] += 1

                except discord.Forbidden:
                    stats['errors'] += 1
                except Exception:
                    stats['errors'] += 1

                stats['processed'] += 1

            # Atualizar progresso a cada lote
            progress = (batch_num / total_batches) * 100

            progress_embed.description = f"""
            **Progresso:** {progress:.1f}% ({stats['processed']}/{stats['total_members']})

            ✅ **Roles adicionadas:** {stats['added']}
            🔄 **Já possuíam:** {stats['already_had']}
            🤖 **Bots pulados:** {stats['skipped_bots']}
            ❌ **Erros:** {stats['errors']}

            ⏳ Processando lote {batch_num}/{total_batches}...
            """

            if batch_num % 3 == 0 or batch_num == total_batches:  # Atualizar a cada 3 lotes
                try:
                    await message.edit(embed=progress_embed)
                except:
                    pass  # Ignorar erros de edição

            # Pequeno delay para evitar rate limits
            if batch_num < total_batches:
                await asyncio.sleep(1)

        # Resultado final
        success_rate = (stats['added'] / max(1, stats['total_members'])) * 100

        final_embed = discord.Embed(
            title="🎉 Migração Concluída!",
            description=f"""
            **Resultados da migração:**

            👥 **Total de membros:** {len(guild.members)}
            ✅ **Roles adicionadas:** {stats['added']}
            🔄 **Já possuíam a role:** {stats['already_had']}
            🤖 **Bots pulados:** {stats['skipped_bots']}
            ❌ **Erros:** {stats['errors']}

            📊 **Taxa de sucesso:** {success_rate:.1f}%

            {"✨ Migração completada com sucesso!" if stats['errors'] == 0 else f"⚠️ Migração completada com {stats['errors']} erros."}
            """,
            color=discord.Color.green() if stats['errors'] == 0 else discord.Color.orange()
        )

        await message.edit(embed=final_embed)

        # Log da operação
        ctx.bot.logger.info(f"Migração de role Participante executada por {ctx.author} - {stats['added']} roles adicionadas")

    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Erro na Migração",
            description=f"Ocorreu um erro durante a migração: {str(e)}",
            color=discord.Color.red()
        )
        await message.edit(embed=error_embed, view=None)
        ctx.bot.logger.error(f"Erro na migração de role Participante", exc_info=e)