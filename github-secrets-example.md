# 🔐 GitHub Secrets Configuration

## Como Configurar os Secrets

1. Vá para seu repositório no GitHub
2. Clique em **Settings**
3. Na barra lateral, clique em **Secrets and variables** → **Actions**
4. Clique em **New repository secret**

## 🔑 Secrets Obrigatórios

Configure cada um dos seguintes secrets:

### **SSH_HOST**
```
Name: SSH_HOST
Value: 31.97.171.230
```

### **SSH_USERNAME**
```
Name: SSH_USERNAME
Value: root
```

### **SSH_PASSWORD**
```
Name: SSH_PASSWORD
Value: sua_senha_da_vps_aqui
```

### **DISCORD_TOKEN**
```
Name: DISCORD_TOKEN
Value: seu_token_do_discord_bot
```

### **GUILD_ID** (opcional)
```
Name: GUILD_ID
Value: id_do_seu_servidor_discord
```

### **LOG_CHANNEL_ID**
```
Name: LOG_CHANNEL_ID
Value: 1402387427103998012
```

---

## 📋 Checklist de Configuração

- [ ] SSH_HOST configurado com IP da VPS
- [ ] SSH_USERNAME configurado (root)
- [ ] SSH_PASSWORD configurado com senha da VPS
- [ ] DISCORD_TOKEN configurado
- [ ] LOG_CHANNEL_ID configurado
- [ ] GUILD_ID configurado (opcional)
- [ ] Arquivo .env criado na VPS
- [ ] Docker e Docker Compose instalados na VPS
- [ ] Repositório clonado na VPS em `/root/discord-bot/`

## 🧪 Testar Configuração

Depois de configurar os secrets:

1. **Faça um push para main** para trigger o deploy automático
2. **Vá em Actions** no GitHub para acompanhar o progresso
3. **Verifique os logs** para identificar possíveis problemas

### Comando para testar SSH manualmente:
```bash
ssh root@31.97.171.230
```

### Estrutura esperada na VPS:
```
/root/discord-bot/
├── .env                    # Suas variáveis de ambiente
├── docker-compose.yml     # Configuração containers
├── bot.py                 # Código do bot
└── logs/                  # Diretório de logs
```

## 🆘 Troubleshooting

### ❌ "SSH Connection Failed"
- Verificar se SSH_HOST, SSH_USERNAME, SSH_PASSWORD estão corretos
- Testar conexão manual: `ssh root@31.97.171.230`

### ❌ "Permission denied"
- Verificar se a senha está correta
- Verificar se o usuário root tem acesso SSH

### ❌ "Directory not found"
- Verificar se o repositório foi clonado na VPS
- Criar diretório manualmente: `mkdir -p /root/discord-bot`

---

**Configuração completa! Agora o deploy automático funcionará a cada push para main! 🚀**