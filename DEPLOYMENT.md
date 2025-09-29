# 🚀 Deployment Setup Guide

Este guia explica como configurar o deploy automático do Discord Bot usando GitHub Actions.

## 📋 Pré-requisitos

### 1. VPS Setup
- **IP:** `31.97.171.230`
- **User:** `root`
- **Docker & Docker Compose** instalados
- **Git** instalado

### 2. GitHub Repository Secrets

Configure os seguintes secrets no seu repositório GitHub:

```
Settings → Secrets and variables → Actions → New repository secret
```

#### Secrets obrigatórios:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `SSH_HOST` | IP ou hostname da VPS | `31.97.171.230` |
| `SSH_USERNAME` | Usuário SSH da VPS | `root` |
| `SSH_PASSWORD` | Senha do usuário SSH | `sua_senha_aqui` |
| `DISCORD_TOKEN` | Token do bot Discord | `MTAxNjc5ODc5...` |
| `GUILD_ID` | ID do servidor Discord (opcional) | `123456789012345678` |
| `LOG_CHANNEL_ID` | ID do canal de logs | `987654321098765432` |

#### Configuração SSH:

**Opção 1: Usando senha (mais simples):**
```bash
# Configure os secrets no GitHub:
SSH_HOST=31.97.171.230
SSH_USERNAME=root
SSH_PASSWORD=sua_senha_vps
```

**Opção 2: Usando chave SSH (mais seguro):**
Se preferir usar chave SSH em vez de senha, substitua `SSH_PASSWORD` por `SSH_KEY`:
```bash
# Gerar chave SSH
ssh-keygen -t ed25519 -C "github-actions-deploy"

# Copiar chave pública para VPS
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@31.97.171.230

# Usar SSH_KEY em vez de SSH_PASSWORD nos secrets
SSH_KEY=conteúdo_da_chave_privada
```

### 3. VPS Environment File

Crie o arquivo `.env` na VPS no diretório do projeto:

```bash
# /root/discord-bot/.env
DISCORD_TOKEN=seu_token_aqui
GUILD_ID=id_do_servidor
DATABASE_URL=postgresql://nasa_user:nasa_password_123@postgres:5432/nasa_spaceapps_bot
LOG_CHANNEL_ID=id_do_canal_de_logs
POSTGRES_DB=nasa_spaceapps_bot
POSTGRES_USER=nasa_user
POSTGRES_PASSWORD=nasa_password_123
```

## 🔄 Como Funciona o Deploy

### Deploy Automático
Acontece automaticamente quando você faz push para a branch `main` ou `master`:

1. **Conecta na VPS** via SSH
2. **Para o container** do bot: `docker-compose down bot`
3. **Atualiza o código** com `git pull`
4. **Rebuilda a imagem** Docker: `docker-compose build --no-cache bot`
5. **Inicia o bot** novamente: `docker-compose up -d bot`
6. **Verifica o status** e mostra logs

### Deploy Manual
Você pode executar deploy manual com opções especiais:

1. Vá em **Actions** no GitHub
2. Selecione **"Manual Deploy with Options"**
3. Clique em **"Run workflow"**
4. Configure as opções:
   - ✅ **Skip Build:** Pula o rebuild (mais rápido)
   - ✅ **Restart PostgreSQL:** Reinicia o banco
   - ✅ **Clean Logs:** Limpa logs antigos
   - 📁 **Custom Path:** Caminho personalizado na VPS

## 📁 Estrutura de Diretórios na VPS

```
/root/discord-bot/           # Diretório principal
├── .env                     # Variáveis de ambiente
├── docker-compose.yml      # Configuração Docker
├── Dockerfile              # Build da aplicação
├── bot.py                   # Código principal
├── requirements.txt         # Dependências Python
├── logs/                    # Logs da aplicação
└── data/                    # Dados persistentes
```

## 🐛 Troubleshooting

### ❌ Erro de conexão SSH
```bash
# Verificar se a chave SSH está correta
ssh root@31.97.171.230

# Se necessário, regenerar e reconfigurar a chave
```

### ❌ Container não inicia
```bash
# Na VPS, verificar logs detalhados
docker-compose logs bot

# Verificar se as variáveis de ambiente estão corretas
cat .env
```

### ❌ Banco de dados não conecta
```bash
# Verificar se PostgreSQL está rodando
docker-compose ps postgres

# Reiniciar PostgreSQL
docker-compose restart postgres
```

### ❌ Bot não responde no Discord
```bash
# Verificar se o token está correto
docker-compose exec bot python -c "import config; print('Token OK' if config.DISCORD_TOKEN else 'Token Missing')"

# Verificar conexão com Discord
docker-compose logs bot | grep -i "logged in\|error\|exception"
```

## 📊 Monitoramento

### Verificar status dos containers:
```bash
docker-compose ps
```

### Ver logs em tempo real:
```bash
docker-compose logs -f bot
```

### Verificar uso de recursos:
```bash
docker stats
```

### Backup do banco de dados:
```bash
docker-compose exec postgres pg_dump -U nasa_user nasa_spaceapps_bot > backup.sql
```

## 🔧 Comandos Úteis na VPS

```bash
# Entrar no diretório do projeto
cd /root/discord-bot

# Ver status completo
docker-compose ps

# Restart completo (bot + banco)
docker-compose restart

# Ver logs específicos
docker-compose logs --tail=50 bot

# Rebuild completo
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Limpar recursos não utilizados
docker system prune -f
```

## 🚨 Comandos de Emergência

### Parar tudo imediatamente:
```bash
docker-compose down
```

### Restart forçado:
```bash
docker-compose kill
docker-compose up -d
```

### Rollback para versão anterior:
```bash
git log --oneline -5
git reset --hard <commit-hash>
docker-compose build --no-cache bot
docker-compose up -d bot
```

---

## 📞 Suporte

Em caso de problemas:

1. ✅ Verificar logs do GitHub Actions
2. ✅ Verificar logs do container na VPS
3. ✅ Verificar conectividade SSH
4. ✅ Verificar variáveis de ambiente
5. 🆘 Executar deploy manual com logs detalhados

**Deploy automático configurado e pronto para uso! 🎉**