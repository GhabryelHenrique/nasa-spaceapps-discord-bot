# Bot Discord de Mentoria

Bot Discord para gerenciar solicitações de mentoria, conectando usuários com mentores experientes em diversas áreas técnicas.

## 🚀 Funcionalidades

- **Solicitação Interativa**: Sistema de perguntas sequenciais em canais privados
- **Validação de Dados**: Título, área, descrição e urgência validados automaticamente
- **Banco PostgreSQL**: Armazenamento seguro de todas as solicitações
- **Notificação de Mentores**: Mentores são automaticamente notificados sobre novas solicitações
- **Sistema de Canais**: Canal privado criado automaticamente para cada solicitação ou fallback para DM

## 📁 Estrutura do Projeto

```
mentoria-bot/
│
├── bot.py                      # Arquivo principal (roda o bot)
├── config.py                  # Configurações do projeto (token, banco)
├── init_db.py                 # Script para inicializar banco
├── database/
│   ├── __init__.py
│   ├── models.py              # Modelo SQLAlchemy de solicitações
│   ├── db.py                  # Conexão com o PostgreSQL
│   └── setup.py               # Setup do banco de dados
├── views/
│   └── mentoria_view.py       # View com botão de solicitação
├── handlers/
│   └── mentoria_handler.py    # Etapas de pergunta e coleta de dados
├── utils/
│   └── helpers.py             # Funções auxiliares
│   └── logger.py              # Sistema de logging
├── requirements.txt           # Dependências do projeto
├── .env                       # Variáveis de ambiente
└── README.md                  # Este arquivo
```

## 🛠️ Instalação

### 1. Pré-requisitos

- Python 3.8+
- PostgreSQL
- Bot Discord criado no Discord Developer Portal

### 2. Setup Automático (Recomendado)

```bash
git clone <seu-repositorio>
cd mentoria-bot

# Configurar arquivo .env
cp .env.example .env
# Edite o .env com suas configurações

# Setup completo (instala dependências + configura banco)
python setup.py
```

### 3. Setup Manual (Alternativo)

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar banco de dados apenas
python init_db.py

# Executar o bot
python bot.py
```

### 4. Configurar PostgreSQL (se necessário)

```sql
-- Criar banco de dados
CREATE DATABASE mentoria_db;

-- Criar usuário (opcional)
CREATE USER bot_user WITH PASSWORD 'senha_segura';
GRANT ALL PRIVILEGES ON DATABASE mentoria_db TO bot_user;
```

## 🎮 Como Usar

### Para Administradores

#### Comandos Slash (Recomendado):
```
/setup        - Configurar painel de solicitação de mentoria
/stats        - Ver estatísticas das solicitações
/export       - Exportar relatório de solicitações
/solicitacoes - Ver solicitações pendentes (apenas mentores)
```

#### Comandos de Texto (Alternativos):
```
!setup, !stats, !export
```

### Para Usuários

#### Solicitar Mentoria:
1. Clique no botão "🆘 Solicitar Ajuda"
2. Um canal privado será criado automaticamente (ou DM como fallback)
3. Responda às perguntas sequencialmente:
   - Título da solicitação
   - Área de conhecimento
   - Descrição detalhada
   - Nível de urgência
4. Sua solicitação será salva e os mentores notificados

### Para Mentores

#### Assumir Solicitações:
1. Monitore o canal #mentores para novas notificações
2. Clique em "✋ Assumir Mentoria" na solicitação de interesse
3. O sistema atualizará automaticamente o status
4. Entre em contato com o solicitante através do Discord

## 📋 Dados Coletados

O bot coleta as seguintes informações para solicitações de mentoria:

- **Identificação**:
  - Discord User ID
  - Discord Username

- **Dados da Solicitação**:
  - Título (máx. 200 caracteres)
  - Área de conhecimento (ex: Python, JavaScript, etc.)
  - Descrição detalhada (máx. 2000 caracteres)
  - Nível de urgência (Baixa, Média, Alta)

- **Tracking**:
  - Status da solicitação (Pendente, Em Andamento, Concluída, Cancelada)
  - Mentor atribuído (quando aplicável)
  - Timestamps (criação, atribuição, conclusão)

## 🔒 Validações Implementadas

- **Título**: Mínimo 5 caracteres, máximo 200
- **Área**: Mínimo 3 caracteres, máximo 100
- **Descrição**: Mínimo 10 caracteres, máximo 2000
- **Urgência**: Seleção entre opções predefinidas
- **Campos obrigatórios**: Todos os campos são validados

## 🗄️ Banco de Dados

### Tabela `solicitacoes_mentoria`

```sql
CREATE TABLE solicitacoes_mentoria (
    id SERIAL PRIMARY KEY,
    discord_user_id BIGINT NOT NULL,
    discord_username VARCHAR(100) NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    descricao TEXT NOT NULL,
    area_conhecimento VARCHAR(100) NOT NULL,
    nivel_urgencia VARCHAR(20) NOT NULL,
    status statussolicitacaoenum DEFAULT 'Pendente',
    mentor_discord_id BIGINT,
    mentor_username VARCHAR(100),
    data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_assumida TIMESTAMP,
    data_conclusao TIMESTAMP
);
```

### Enum `StatusSolicitacaoEnum`

```sql
CREATE TYPE statussolicitacaoenum AS ENUM (
    'Pendente',
    'Em Andamento', 
    'Concluída',
    'Cancelada'
);
```

## 🛡️ Permissões do Bot

O bot precisa das seguintes permissões no Discord:

- **Permissões de Texto**:
  - Enviar Mensagens
  - Ler Histórico de Mensagens
  - Usar Comandos de Barra
  - Incorporar Links
  - Anexar Arquivos

- **Permissões de Canal**:
  - Gerenciar Canais
  - Ver Canais

## 🚨 Tratamento de Erros

- **Sessão Ativa**: Impede múltiplas solicitações simultâneas do mesmo usuário
- **Validação de Dados**: Mensagens de erro específicas para cada campo
- **Banco de Dados**: Tratamento de erros de conexão
- **Cancelamento**: Usuários podem cancelar digitando "cancelar"
- **Fallback de Canais**: Automaticamente usa DM se não conseguir criar canal privado

## 🔧 Personalização

### Modificar perguntas:
Edite os métodos de processamento em `handlers/mentoria_handler.py`

### Adicionar validações:
Implemente novos métodos `_process_*` na classe `MentoriaHandler`

### Customizar mensagens:
Modifique os embeds nos arquivos de views e handlers

### Configurar Mentores:
Crie um papel chamado "Mentor" no servidor para permitir acesso ao comando `/solicitacoes`

## 📊 Monitoramento

O bot inclui logs para:
- Conexões com banco de dados
- Solicitações de mentoria criadas
- Erros de validação
- Comandos executados
- Atribuições de mentores
- Status de solicitações

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature
3. Faça commit das mudanças
4. Faça push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

## 🆘 Suporte

Para dúvidas ou problemas:
1. Verifique se todas as dependências estão instaladas
2. Confirme se as variáveis de ambiente estão corretas no arquivo `.env`
3. Verifique se o PostgreSQL está rodando
4. Confirme se o canal #mentores existe no servidor
5. Verifique se o papel "Mentor" foi criado para mentores
6. Consulte os logs para identificar erros específicos

## 🔧 Configurações Importantes do Discord

### Canais necessários:
- `#mentores` - Canal onde mentores recebem notificações
- `#solicitar-mentoria` - Canal onde será postado o painel de solicitação (opcional)

### Papéis necessários:
- `Mentor` - Papel que permite acesso ao comando `/solicitacoes`

### Categorias criadas automaticamente:
- `Solicitações Mentoria` - Onde canais privados de solicitação são criados

---

**Sistema de Mentoria Discord** 🎓