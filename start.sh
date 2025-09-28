#!/bin/bash

# NASA SpaceApps Discord Bot Startup Script
# This script ensures proper initialization before starting the bot

set -e  # Exit on any error

echo "🚀 Starting NASA SpaceApps Discord Bot..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -p 5432 -U nasa_user; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done

echo "✅ PostgreSQL is ready!"

# Initialize database if needed
echo "🔧 Initializing database..."
python setup.py

# Start the bot
echo "🤖 Starting Discord bot..."
exec python bot.py