import discord
from discord.ext import commands
import asyncio
from utils.logger import get_logger

class VoiceHandler:
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger()

        # IDs configuráveis
        self.trigger_channel_id = 1421849681637670993  # Canal que ativa a criação
        self.category_id = 1421849561072144534  # Categoria onde criar novos canais

        # Controle de canais temporários
        self.temp_channels = set()  # IDs dos canais temporários criados
        self.channel_creators = {}  # channel_id: creator_id

    async def handle_voice_state_update(self, member, before, after):
        """Processa mudanças de estado de voz"""
        try:
            # Verificar se alguém entrou no canal trigger
            if after.channel and after.channel.id == self.trigger_channel_id:
                await self.create_temp_channel(member)

            # Verificar se alguém saiu de um canal temporário (limpeza)
            if before.channel and before.channel.id in self.temp_channels:
                await self.check_temp_channel_cleanup(before.channel)

        except Exception as e:
            self.logger.error(f"Erro no handler de voz para {member.id}", exc_info=e)

    async def create_temp_channel(self, member):
        """Cria um canal de voz temporário e move o usuário"""
        try:
            guild = member.guild
            category = guild.get_channel(self.category_id)

            if not category:
                self.logger.error(f"Categoria {self.category_id} não encontrada")
                return

            # Verificar se usuário já tem um canal temporário ativo
            existing_channel = self.get_user_temp_channel(member.id)
            if existing_channel:
                # Se já tem canal, apenas move para ele
                if member.voice and member.voice.channel:
                    await member.move_to(existing_channel)
                return

            # Gerar nome único para o canal
            base_name = f"🔊 {member.display_name}"
            channel_name = base_name
            counter = 1

            # Verificar se já existe canal com este nome
            while any(ch.name == channel_name for ch in category.voice_channels):
                counter += 1
                channel_name = f"{base_name} ({counter})"

            # Configurar permissões do canal
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True
                ),
                member: discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    manage_channels=True,  # Criador pode gerenciar
                    manage_permissions=True,  # Criador pode alterar permissões
                    move_members=True,  # Criador pode mover membros
                    mute_members=True,  # Criador pode mutar
                    deafen_members=True  # Criador pode ensurdecer
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    manage_channels=True,
                    move_members=True
                )
            }

            # Criar canal temporário
            temp_channel = await category.create_voice_channel(
                name=channel_name,
                overwrites=overwrites,
                reason=f"Canal temporário criado para {member.display_name}"
            )

            # Registrar canal como temporário
            self.temp_channels.add(temp_channel.id)
            self.channel_creators[temp_channel.id] = member.id

            # Mover o usuário para o novo canal
            if member.voice and member.voice.channel:
                await member.move_to(temp_channel)

            self.logger.info(f"Canal temporário '{channel_name}' criado para {member.id} ({member.display_name})")

            # Enviar mensagem de boas-vindas (opcional)
            try:
                embed = discord.Embed(
                    title="🎙️ Canal de Voz Criado!",
                    description=f"""**Bem-vindo ao seu canal pessoal, {member.mention}!**

**🎮 Recursos disponíveis:**
• Você tem controle total sobre este canal
• Pode gerenciar permissões de outros usuários
• Pode mover, mutar e ensurdecer membros
• O canal será deletado automaticamente quando vazio

**👥 Convide amigos:**
Outros usuários podem entrar livremente, mas você mantém o controle!

**🗑️ Limpeza automática:**
Este canal será removido automaticamente quando todos saírem.""",
                    color=discord.Color.green()
                )

                embed.set_footer(text="Sistema de Canais Temporários")

                # Tentar enviar DM para o usuário
                try:
                    await member.send(embed=embed)
                except discord.Forbidden:
                    # Se não conseguir enviar DM, ignorar
                    pass

            except Exception as e:
                self.logger.error(f"Erro ao enviar mensagem de boas-vindas", exc_info=e)

        except discord.Forbidden:
            self.logger.error(f"Sem permissão para criar canal de voz na categoria {self.category_id}")
        except Exception as e:
            self.logger.error(f"Erro ao criar canal temporário para {member.id}", exc_info=e)

    async def check_temp_channel_cleanup(self, channel):
        """Verifica se um canal temporário deve ser deletado"""
        try:
            # Aguardar um pouco para evitar deletar muito rapidamente
            await asyncio.sleep(2)

            # Verificar se ainda é um canal temporário válido
            if channel.id not in self.temp_channels:
                return

            # Recarregar o canal para ter dados atualizados
            try:
                updated_channel = self.bot.get_channel(channel.id)
                if not updated_channel:
                    # Canal já foi deletado
                    self.temp_channels.discard(channel.id)
                    self.channel_creators.pop(channel.id, None)
                    return

                # Verificar se há membros no canal
                if len(updated_channel.members) == 0:
                    await self.delete_temp_channel(updated_channel)

            except discord.NotFound:
                # Canal já foi deletado
                self.temp_channels.discard(channel.id)
                self.channel_creators.pop(channel.id, None)

        except Exception as e:
            self.logger.error(f"Erro ao verificar limpeza do canal {channel.id}", exc_info=e)

    async def delete_temp_channel(self, channel):
        """Deleta um canal temporário"""
        try:
            channel_id = channel.id
            creator_id = self.channel_creators.get(channel_id)

            await channel.delete(reason="Canal temporário vazio - limpeza automática")

            # Remover dos registros
            self.temp_channels.discard(channel_id)
            self.channel_creators.pop(channel_id, None)

            creator_name = "Desconhecido"
            if creator_id:
                creator = self.bot.get_user(creator_id)
                if creator:
                    creator_name = creator.display_name

            self.logger.info(f"Canal temporário {channel.name} (ID: {channel_id}) deletado - criado por {creator_name}")

        except discord.NotFound:
            # Canal já foi deletado
            self.temp_channels.discard(channel.id)
            self.channel_creators.pop(channel.id, None)
        except Exception as e:
            self.logger.error(f"Erro ao deletar canal temporário {channel.id}", exc_info=e)

    def get_user_temp_channel(self, user_id):
        """Verifica se um usuário já tem um canal temporário ativo"""
        for channel_id in self.temp_channels:
            if self.channel_creators.get(channel_id) == user_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    return channel
        return None

    async def cleanup_abandoned_channels(self):
        """Limpa canais temporários abandonados (executado periodicamente)"""
        try:
            channels_to_remove = []

            for channel_id in list(self.temp_channels):
                channel = self.bot.get_channel(channel_id)

                if not channel:
                    # Canal não existe mais
                    channels_to_remove.append(channel_id)
                    continue

                # Verificar se está vazio
                if len(channel.members) == 0:
                    await self.delete_temp_channel(channel)

            # Limpar registros de canais que não existem mais
            for channel_id in channels_to_remove:
                self.temp_channels.discard(channel_id)
                self.channel_creators.pop(channel_id, None)

        except Exception as e:
            self.logger.error("Erro na limpeza periódica de canais", exc_info=e)

    async def force_cleanup_user_channels(self, user_id):
        """Remove todos os canais temporários de um usuário específico"""
        try:
            channels_to_delete = []

            for channel_id, creator_id in list(self.channel_creators.items()):
                if creator_id == user_id:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        channels_to_delete.append(channel)

            for channel in channels_to_delete:
                await self.delete_temp_channel(channel)

        except Exception as e:
            self.logger.error(f"Erro ao limpar canais do usuário {user_id}", exc_info=e)

    def get_temp_channels_info(self):
        """Retorna informações sobre canais temporários ativos"""
        info = []

        for channel_id in self.temp_channels:
            channel = self.bot.get_channel(channel_id)
            creator_id = self.channel_creators.get(channel_id)

            if channel:
                creator = self.bot.get_user(creator_id) if creator_id else None
                creator_name = creator.display_name if creator else "Desconhecido"

                info.append({
                    'channel': channel,
                    'creator': creator_name,
                    'member_count': len(channel.members),
                    'members': [m.display_name for m in channel.members]
                })

        return info