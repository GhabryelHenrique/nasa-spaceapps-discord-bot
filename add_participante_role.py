#!/usr/bin/env python3
"""
Script para adicionar a role "Participante" a todos os membros existentes do servidor.
Execute este script uma vez para atualizar todos os membros existentes.
"""

import discord
import asyncio
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('participante_role_migration.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

class ParticipanteRoleMigration:
    def __init__(self):
        self.bot_token = os.getenv('DISCORD_TOKEN')
        self.guild_id = os.getenv('GUILD_ID')

        if not self.bot_token:
            raise ValueError("DISCORD_TOKEN não encontrado no arquivo .env")

        # Configurar intents
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True

        self.client = discord.Client(intents=intents)

        # Estatísticas
        self.stats = {
            'total_members': 0,
            'members_processed': 0,
            'members_added': 0,
            'members_already_had': 0,
            'members_skipped': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }

    async def run_migration(self):
        """Executa a migração completa"""
        try:
            logger.info("🚀 Iniciando migração da role Participante...")
            self.stats['start_time'] = datetime.now()

            @self.client.event
            async def on_ready():
                logger.info(f"✅ Bot conectado como {self.client.user}")
                await self.migrate_all_members()
                await self.client.close()

            # Conectar e executar
            await self.client.start(self.bot_token)

        except Exception as e:
            logger.error(f"❌ Erro fatal na migração: {e}")
            raise

    async def migrate_all_members(self):
        """Migra todos os membros do servidor"""
        try:
            # Buscar guild
            if self.guild_id:
                guild = self.client.get_guild(int(self.guild_id))
            else:
                # Se não especificado, usar o primeiro servidor
                guild = self.client.guilds[0] if self.client.guilds else None

            if not guild:
                logger.error("❌ Servidor não encontrado!")
                return

            logger.info(f"🏰 Servidor encontrado: {guild.name} (ID: {guild.id})")
            logger.info(f"👥 Total de membros: {guild.member_count}")

            # Buscar ou criar role "Participante"
            participante_role = await self.get_or_create_participante_role(guild)
            if not participante_role:
                logger.error("❌ Não foi possível criar ou encontrar a role Participante!")
                return

            # Processar todos os membros
            self.stats['total_members'] = len(guild.members)
            logger.info(f"📝 Processando {self.stats['total_members']} membros...")

            # Processar em lotes para evitar rate limits
            batch_size = 10
            delay_between_batches = 2  # segundos

            members_list = list(guild.members)
            total_batches = (len(members_list) + batch_size - 1) // batch_size

            for batch_num, i in enumerate(range(0, len(members_list), batch_size), 1):
                batch = members_list[i:i + batch_size]

                logger.info(f"📦 Processando lote {batch_num}/{total_batches} ({len(batch)} membros)")

                # Processar lote atual
                tasks = []
                for member in batch:
                    task = self.process_member(member, participante_role)
                    tasks.append(task)

                # Executar lote concorrentemente
                await asyncio.gather(*tasks, return_exceptions=True)

                # Progresso
                progress = (batch_num / total_batches) * 100
                logger.info(f"📊 Progresso: {progress:.1f}% ({self.stats['members_processed']}/{self.stats['total_members']} membros)")

                # Delay entre lotes (exceto no último)
                if batch_num < total_batches:
                    await asyncio.sleep(delay_between_batches)

            # Finalizar
            await self.finalize_migration()

        except Exception as e:
            logger.error(f"❌ Erro durante migração: {e}")
            self.stats['errors'] += 1

    async def get_or_create_participante_role(self, guild):
        """Busca ou cria a role Participante"""
        try:
            # Tentar encontrar role existente
            participante_role = discord.utils.get(guild.roles, name="Participante")

            if participante_role:
                logger.info(f"✅ Role 'Participante' encontrada (ID: {participante_role.id})")
                return participante_role

            # Criar nova role
            logger.info("🔧 Criando role 'Participante'...")
            participante_role = await guild.create_role(
                name="Participante",
                color=discord.Color(0x87CEEB),  # Azul claro
                reason="Role automática para todos os membros - Migração inicial"
            )

            logger.info(f"✅ Role 'Participante' criada com sucesso (ID: {participante_role.id})")
            return participante_role

        except discord.Forbidden:
            logger.error("❌ Sem permissão para criar roles!")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao criar role Participante: {e}")
            return None

    async def process_member(self, member, participante_role):
        """Processa um membro individual"""
        try:
            # Pular bots
            if member.bot:
                self.stats['members_skipped'] += 1
                logger.debug(f"🤖 Pulando bot: {member.display_name}")
                return

            # Verificar se já tem a role
            if participante_role in member.roles:
                self.stats['members_already_had'] += 1
                logger.debug(f"✅ {member.display_name} já possui a role Participante")
                return

            # Adicionar role
            await member.add_roles(participante_role, reason="Migração automática - Role Participante")
            self.stats['members_added'] += 1
            logger.info(f"➕ Role adicionada para: {member.display_name} ({member.id})")

        except discord.Forbidden:
            logger.warning(f"⚠️  Sem permissão para adicionar role ao membro: {member.display_name}")
            self.stats['errors'] += 1
        except discord.HTTPException as e:
            logger.warning(f"⚠️  Erro HTTP ao processar {member.display_name}: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            logger.error(f"❌ Erro ao processar {member.display_name}: {e}")
            self.stats['errors'] += 1
        finally:
            self.stats['members_processed'] += 1

    async def finalize_migration(self):
        """Finaliza a migração e mostra estatísticas"""
        self.stats['end_time'] = datetime.now()
        duration = self.stats['end_time'] - self.stats['start_time']

        logger.info("=" * 60)
        logger.info("🎉 MIGRAÇÃO CONCLUÍDA!")
        logger.info("=" * 60)
        logger.info(f"⏱️  Duração: {duration}")
        logger.info(f"👥 Total de membros: {self.stats['total_members']}")
        logger.info(f"✅ Membros processados: {self.stats['members_processed']}")
        logger.info(f"➕ Roles adicionadas: {self.stats['members_added']}")
        logger.info(f"🔄 Já possuíam a role: {self.stats['members_already_had']}")
        logger.info(f"🤖 Bots pulados: {self.stats['members_skipped']}")
        logger.info(f"❌ Erros: {self.stats['errors']}")

        success_rate = (self.stats['members_added'] / max(1, self.stats['total_members'] - self.stats['members_skipped'])) * 100
        logger.info(f"📊 Taxa de sucesso: {success_rate:.1f}%")

        logger.info("=" * 60)

        if self.stats['errors'] > 0:
            logger.warning(f"⚠️  {self.stats['errors']} erros encontrados. Verifique o log para detalhes.")
        else:
            logger.info("✨ Migração completada sem erros!")

def main():
    """Função principal"""
    print("🚀 Script de Migração - Role Participante")
    print("=" * 50)
    print("Este script irá:")
    print("• Buscar ou criar a role 'Participante'")
    print("• Adicionar a role a todos os membros existentes")
    print("• Pular bots automaticamente")
    print("• Gerar relatório completo da migração")
    print("=" * 50)

    # Confirmar execução
    confirm = input("Deseja continuar? (s/N): ").lower().strip()
    if confirm not in ['s', 'sim', 'y', 'yes']:
        print("❌ Migração cancelada pelo usuário.")
        return

    # Executar migração
    migration = ParticipanteRoleMigration()

    try:
        asyncio.run(migration.run_migration())
        print("\n✅ Script executado com sucesso!")
        print("📄 Verifique o arquivo 'participante_role_migration.log' para detalhes completos.")

    except KeyboardInterrupt:
        print("\n❌ Migração interrompida pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        logger.error(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()