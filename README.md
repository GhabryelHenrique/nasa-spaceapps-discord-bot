# NASA Space Apps Bot - Sistema de Inscrições

Bot Discord para gerenciar inscrições no NASA Space Apps Challenge em Uberlândia, com sistema de formulário interativo e canais privados.

## 🚀 Funcionalidades

- **Inscrição Interativa**: Sistema de perguntas sequenciais em canais privados
- **Validação de Dados**: CPF, email, telefone e datas validados automaticamente
- **Banco PostgreSQL**: Armazenamento seguro de todas as inscrições
- **Painel Administrativo**: Comandos para estatísticas e exportação de dados
- **Sistema de Canais**: Canal privado criado automaticamente para cada usuário

## 📁 Estrutura do Projeto

```
nasa-spaceapps-bot/
│
├── bot.py                      # Arquivo principal (roda o bot)
├── config.py                  # Configurações do projeto (token, banco)
├── init_db.py                 # Script para inicializar banco
├── database/
│   ├── __init__.py
│   ├── models.py              # Modelo SQLAlchemy do participante
│   └── db.py                  # Conexão com o PostgreSQL
├── views/
│   └── register_view.py       # View com botão de inscrição
├── handlers/
│   └── registration_form.py   # Etapas de pergunta e coleta de dados
├── utils/
│   └── helpers.py             # Funções auxiliares (validação, etc)
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
cd nasa-spaceapps-bot

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
CREATE DATABASE nasa_spaceapps;

-- Criar usuário (opcional)
CREATE USER bot_user WITH PASSWORD 'senha_segura';
GRANT ALL PRIVILEGES ON DATABASE nasa_spaceapps TO bot_user;
```

## 🎮 Como Usar

### Para Administradores

#### Comandos Slash (Recomendado):
```
/setup     - Configurar painel de inscrições
/stats     - Ver estatísticas
/export    - Exportar lista de inscritos
/aplicacoes - Gerenciar aplicações para sua equipe
```

#### Comandos de Texto (Alternativos):
```
!setup, !stats, !export
```

### Para Usuários

#### Inscrição:
1. Clique no botão "🚀 Fazer Inscrição NASA Space Apps"
2. Um canal privado será criado automaticamente
3. Responda às perguntas uma por vez
4. Sua inscrição será salva no banco de dados

#### Sistema de Equipes:
1. Use `/equipes` ou clique em "🔍 Buscar Equipes"
2. Marque-se como disponível para outras equipes
3. Procure equipes que combinem com você
4. Envie aplicações para equipes de interesse
5. Use `/minhas_aplicacoes` para acompanhar o status

## 📋 Dados Coletados

O bot coleta as seguintes informações:

- **Dados Pessoais**:
  - Nome e Sobrenome
  - Email
  - Telefone
  - CPF
  - Cidade de residência
  - Data de nascimento

- **Dados Acadêmicos**:
  - Escolaridade (9 opções disponíveis)

- **Dados do Evento**:
  - Modalidade de participação (Presencial ou Remoto)

## 🔒 Validações Implementadas

- **Email**: Formato válido
- **CPF**: Validação completa com dígitos verificadores
- **Telefone**: Formato brasileiro com DDD
- **Data**: Formato DD/MM/AAAA com validação de idade
- **Campos obrigatórios**: Todos os campos são validados

## 🗄️ Banco de Dados

### Tabela `participantes`

```sql
CREATE TABLE participantes (
    id SERIAL PRIMARY KEY,
    discord_user_id BIGINT UNIQUE NOT NULL,
    discord_username VARCHAR(100) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    sobrenome VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    cpf VARCHAR(14) UNIQUE NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    data_nascimento VARCHAR(10) NOT NULL,
    escolaridade escolaridadeenum NOT NULL,
    modalidade modalidadeenum NOT NULL,
    data_inscricao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    canal_privado_id BIGINT
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

- **Inscrição Duplicada**: Impede múltiplas inscrições do mesmo usuário
- **Validação de Dados**: Mensagens de erro específicas para cada campo
- **Banco de Dados**: Tratamento de erros de conexão
- **Cancelamento**: Usuários podem cancelar digitando "cancelar"

## 🔧 Personalização

### Modificar perguntas:
Edite o array `questions` em `handlers/registration_form.py`

### Adicionar validações:
Implemente novos métodos `validate_*` na classe `RegistrationHandler`

### Customizar mensagens:
Modifique os embeds nos arquivos de views e handlers

## 📊 Monitoramento

O bot inclui logs para:
- Conexões com banco de dados
- Inscrições realizadas
- Erros de validação
- Comandos executados

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
2. Confirme se as variáveis de ambiente estão corretas
3. Verifique se o PostgreSQL está rodando
4. Consulte os logs para identificar erros específicos

---

**NASA Space Apps Challenge 2025 - Uberlândia** 🚀