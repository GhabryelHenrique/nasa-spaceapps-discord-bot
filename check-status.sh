#!/bin/bash

# Discord Bot Status Checker
# Use este script na VPS para verificar o status completo do bot

set -e

echo "🔍 DISCORD BOT STATUS CHECK"
echo "=========================="
echo "⏰ $(date)"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found. Are you in the correct directory?"
    echo "💡 Try: cd /root/discord-bot"
    exit 1
fi

echo "📊 Container Status:"
echo "==================="
docker-compose ps

echo ""
echo "💾 Resource Usage:"
echo "=================="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

echo ""
echo "🌐 Network Connectivity:"
echo "========================"
if docker-compose exec bot ping -c 2 discord.com > /dev/null 2>&1; then
    echo "✅ Discord connection: OK"
else
    echo "❌ Discord connection: FAILED"
fi

if docker-compose exec bot ping -c 2 postgres > /dev/null 2>&1; then
    echo "✅ Database connection: OK"
else
    echo "❌ Database connection: FAILED"
fi

echo ""
echo "💽 Disk Usage:"
echo "=============="
df -h /var/lib/docker | head -2

echo ""
echo "📋 Recent Bot Logs (last 20 lines):"
echo "===================================="
docker-compose logs --tail=20 bot

echo ""
echo "🔍 Bot Process Info:"
echo "==================="
docker-compose exec bot ps aux | head -5 || echo "Could not get process info"

echo ""
echo "⚙️  Environment Check:"
echo "====================="
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    echo "📄 Environment variables loaded: $(grep -c "=" .env 2>/dev/null || echo "0")"
else
    echo "❌ .env file missing"
fi

echo ""
echo "🏥 Health Status:"
echo "================"
if docker-compose ps bot | grep -q "Up (healthy)"; then
    echo "✅ Bot is healthy"
elif docker-compose ps bot | grep -q "Up"; then
    echo "⚠️  Bot is running but health status unknown"
else
    echo "❌ Bot is not running"
fi

echo ""
echo "📈 Uptime:"
echo "=========="
docker-compose exec bot uptime 2>/dev/null || echo "Uptime info not available"

echo ""
echo "🎯 Quick Actions:"
echo "================="
echo "Restart bot:           docker-compose restart bot"
echo "View live logs:        docker-compose logs -f bot"
echo "Rebuild and restart:   docker-compose down bot && docker-compose build bot && docker-compose up -d bot"
echo "Full restart:          docker-compose restart"
echo "Emergency stop:        docker-compose down"

echo ""
echo "✅ Status check completed!"