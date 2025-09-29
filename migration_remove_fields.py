#!/usr/bin/env python3
"""
Migration script to remove area_conhecimento and nivel_urgencia fields from solicitacoes_mentoria table.
This script safely removes the columns that are no longer needed.
"""

import asyncio
import sys
from sqlalchemy import text
from database.setup import db_setup
from database.models import Base
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_database():
    """Remove area_conhecimento and nivel_urgencia columns from the database"""
    try:
        # Get async engine for migration operations
        async_engine = db_setup.async_engine

        async with async_engine.begin() as conn:
            logger.info("Starting migration to remove area_conhecimento and nivel_urgencia fields...")

            # Check if columns exist before trying to drop them
            check_area_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'solicitacoes_mentoria'
                AND column_name = 'area_conhecimento'
            """)

            check_urgencia_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'solicitacoes_mentoria'
                AND column_name = 'nivel_urgencia'
            """)

            # Check for area_conhecimento column
            area_result = await conn.execute(check_area_query)
            area_exists = area_result.fetchone() is not None

            # Check for nivel_urgencia column
            urgencia_result = await conn.execute(check_urgencia_query)
            urgencia_exists = urgencia_result.fetchone() is not None

            if area_exists:
                logger.info("Removing area_conhecimento column...")
                await conn.execute(text("ALTER TABLE solicitacoes_mentoria DROP COLUMN area_conhecimento"))
                logger.info("✅ area_conhecimento column removed successfully")
            else:
                logger.info("ℹ️  area_conhecimento column does not exist, skipping")

            if urgencia_exists:
                logger.info("Removing nivel_urgencia column...")
                await conn.execute(text("ALTER TABLE solicitacoes_mentoria DROP COLUMN nivel_urgencia"))
                logger.info("✅ nivel_urgencia column removed successfully")
            else:
                logger.info("ℹ️  nivel_urgencia column does not exist, skipping")

            logger.info("✅ Migration completed successfully!")

        await async_engine.dispose()

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise

def verify_migration():
    """Verify that the migration was successful by checking the table structure"""
    try:
        sync_engine = db_setup.sync_engine

        with sync_engine.begin() as conn:
            # Get current table structure
            result = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'solicitacoes_mentoria'
                ORDER BY ordinal_position
            """))

            columns = result.fetchall()

            logger.info("Current table structure:")
            for column_name, data_type in columns:
                logger.info(f"  - {column_name}: {data_type}")

            # Check that removed columns are not present
            column_names = [col[0] for col in columns]

            if 'area_conhecimento' not in column_names and 'nivel_urgencia' not in column_names:
                logger.info("✅ Verification successful - removed columns are not present")
                return True
            else:
                remaining_unwanted = []
                if 'area_conhecimento' in column_names:
                    remaining_unwanted.append('area_conhecimento')
                if 'nivel_urgencia' in column_names:
                    remaining_unwanted.append('nivel_urgencia')

                logger.error(f"❌ Verification failed - these columns still exist: {remaining_unwanted}")
                return False

    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        return False

async def main():
    """Main migration function"""
    logger.info("=== Database Migration: Remove area_conhecimento and nivel_urgencia ===")

    try:
        # Run migration
        await migrate_database()

        # Verify migration
        if verify_migration():
            logger.info("🎉 Migration completed and verified successfully!")
            return 0
        else:
            logger.error("❌ Migration verification failed!")
            return 1

    except Exception as e:
        logger.error(f"❌ Migration process failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)