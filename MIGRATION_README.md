# 🔄 Scripts de Migração - Role Participante

Este documento explica como usar os scripts para adicionar a role "Participante" a todos os membros existentes do servidor.

## 📁 Arquivos Disponíveis

### 1. `add_participante_role.py` - Script Standalone
Script independente que pode ser executado diretamente para migrar todos os membros.

### 2. `migration_command.py` - Comando do Bot
Código para adicionar como comando dentro do bot existente.

---

## 🚀 Opção 1: Script Standalone

### Pré-requisitos
```bash
pip install discord.py python-dotenv
```

### Como usar:
1. **Configure o arquivo `.env`** (se ainda não tiver):
   ```env
   DISCORD_TOKEN=seu_token_aqui
   GUILD_ID=id_do_servidor (opcional)
   ```

2. **Execute o script**:
   ```bash
   python add_participante_role.py
   ```

3. **Confirme a execução** quando solicitado

### Características:
- ✅ Execução independente do bot
- ✅ Processamento em lotes para evitar rate limits
- ✅ Log detalhado em arquivo
- ✅ Estatísticas completas
- ✅ Tratamento de erros robusto
- ✅ Progresso em tempo real

---

## 🤖 Opção 2: Comando do Bot

### Como implementar:

1. **Abra o arquivo `migration_command.py`**

2. **Copie o código** e cole no final do seu `bot.py`, antes da linha `if __name__ == "__main__"`

3. **Adicione o comando aos error handlers**:
   ```python
   @migrate_participante_role.error
   async def command_error(ctx, error):
       if isinstance(error, commands.MissingPermissions):
           await ctx.send("Você não tem permissão para usar este comando.")
   ```

4. **Execute o bot normalmente** e use o comando:
   ```
   n!migrar_participantes
   ```

### Características:
- ✅ Integrado ao bot existente
- ✅ Interface visual com embeds
- ✅ Confirmação antes da execução
- ✅ Progresso em tempo real
- ✅ Apenas administradores podem usar

---

## 📊 O que os scripts fazem:

### Processo de Migração:
1. **Busca a role "Participante"** (ou cria se não existir)
2. **Lista todos os membros** do servidor
3. **Pula bots automaticamente**
4. **Verifica se já possuem a role** (evita duplicação)
5. **Adiciona a role** aos membros que não possuem
6. **Gera relatório completo** com estatísticas

### Role "Participante":
- **Nome:** "Participante"
- **Cor:** Azul claro (`#87CEEB`)
- **Permissões:** Padrão (mesmas que @everyone)
- **Posição:** Acima de @everyone

---

## 📈 Estatísticas Geradas:

Ambos os scripts fornecem estatísticas detalhadas:

```
🎉 MIGRAÇÃO CONCLUÍDA!
========================================
⏱️  Duração: 0:02:15
👥 Total de membros: 150
✅ Membros processados: 142
➕ Roles adicionadas: 128
🔄 Já possuíam a role: 14
🤖 Bots pulados: 8
❌ Erros: 0
📊 Taxa de sucesso: 100.0%
```

---

## ⚠️ Considerações Importantes:

### Permissões Necessárias:
- **Manage Roles** - Para criar e atribuir roles
- **View Members** - Para listar membros do servidor

### Limitações do Discord:
- **Rate Limits:** Scripts processam em lotes para evitar limites
- **Hierarquia:** O bot precisa estar acima da role "Participante"
- **Permissões:** Alguns membros podem ter permissões especiais que impedem a alteração

### Recomendações:
- ✅ Execute durante horários de baixo movimento
- ✅ Informe os membros sobre a nova role
- ✅ Teste primeiro em um servidor de desenvolvimento
- ✅ Mantenha backup das configurações atuais

---

## 🔧 Troubleshooting:

### Erro: "Missing Permissions"
- Verifique se o bot tem permissão **Manage Roles**
- Certifique-se que o bot está acima da role "Participante" na hierarquia

### Erro: "Rate Limited"
- Os scripts já incluem delays automáticos
- Se persistir, aumente o `delay_between_batches` no script standalone

### Erro: "Guild not found"
- Verifique o `GUILD_ID` no arquivo `.env`
- Certifique-se que o bot está no servidor correto

### Script não encontra membros:
- Verifique se o bot tem a intent **members** habilitada
- No Discord Developer Portal: Bot → Privileged Gateway Intents → Server Members Intent

---

## 📞 Suporte:

Se encontrar problemas:
1. Verifique os logs gerados
2. Confirme as permissões do bot
3. Teste em um servidor menor primeiro
4. Verifique se todas as dependências estão instaladas

---

## ✨ Após a Migração:

Todos os **novos membros** que entrarem no servidor receberão automaticamente a role "Participante" através do sistema já implementado no bot (`on_member_join`).

A migração é necessária apenas **uma vez** para os membros existentes!