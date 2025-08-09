# 🤖 Sistema de Matchmaking Automático
## NASA Space Apps Challenge - Uberlândia

### Índice
1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Algoritmo de Compatibilidade](#algoritmo-de-compatibilidade)
4. [Componentes Principais](#componentes-principais)
5. [Fluxo de Funcionamento](#fluxo-de-funcionamento)
6. [Interface do Usuário](#interface-do-usuário)
7. [Administração](#administração)
8. [Banco de Dados](#banco-de-dados)
9. [Configuração e Deploy](#configuração-e-deploy)
10. [Troubleshooting](#troubleshooting)

---

## Visão Geral

O Sistema de Matchmaking Automático é uma solução completa para formar equipes automaticamente no NASA Space Apps Challenge. O sistema analisa participantes disponíveis e cria equipes com alta compatibilidade baseada em habilidades, localização, modalidade e escolaridade.

### Características Principais
- **Formação Automática**: Algoritmo inteligente que forma equipes otimizadas
- **Interface Intuitiva**: Botões simples integrados ao sistema existente
- **Canais de Controle**: Líderes podem controlar matchmaking via canais privados
- **Notificações Inteligentes**: Sistema de aceitar/rejeitar equipes via DM
- **Alta Compatibilidade**: Score baseado em múltiplos fatores de compatibilidade

### Tecnologias Utilizadas
- **Discord.py**: Framework principal do bot
- **SQLAlchemy**: ORM para banco de dados
- **PostgreSQL**: Banco de dados principal
- **Python 3.8+**: Linguagem de programação
- **Asyncio**: Programação assíncrona

---

## Arquitetura do Sistema

```mermaid
graph TB
    A[Usuários Disponíveis] --> B[Auto Team Formation]
    B --> C[Algoritmo de Compatibilidade]
    C --> D[Formação de Equipes]
    D --> E[Notificação System]
    E --> F[Accept/Reject Interface]
    F --> G[Team Creation]
    
    H[Team Leaders] --> I[Team Channel Manager]
    I --> J[Control Channels]
    J --> K[Toggle Matchmaking]
    K --> L[Configuration]
    
    M[Administrators] --> N[Team Search View]
    N --> O[Execute Algorithm]
    O --> B
```

### Estrutura de Arquivos
```
matchmaking/
├── auto_team_formation.py      # Algoritmo principal de formação
├── team_channel_manager.py     # Gerenciamento de canais
├── auto_team_notifications.py  # Sistema de notificações
└── algorithm.py                # Algoritmos base de matchmaking

views/
└── team_search_view.py         # Interface principal integrada

database/
└── models.py                   # Modelos de dados (MatchSugestao, etc.)
```

---

## Algoritmo de Compatibilidade

### Fórmula de Score
O algoritmo calcula compatibilidade baseado em 4 fatores principais:

```python
Score Total = (Habilidades × 40%) + (Região × 30%) + (Modalidade × 20%) + (Escolaridade × 10%)
```

### Detalhamento dos Fatores

#### 1. Habilidades (40% do score)
- Extrai habilidades de texto livre usando NLP básico
- Calcula interseção entre habilidades dos membros
- Bonus para habilidades complementares
- Penalidade para sobreposição excessiva

#### 2. Região (30% do score)
- Agrupa por regiões geográficas do Brasil
- Bonus de +15 pontos para mesma região
- Mapeamento inteligente de cidades para regiões:
  ```python
  REGIOES = {
      'sudeste': ['são paulo', 'rio de janeiro', 'belo horizonte', 'uberlândia'],
      'sul': ['porto alegre', 'curitiba', 'florianópolis'],
      'nordeste': ['salvador', 'recife', 'fortaleza'],
      'centro_oeste': ['brasília', 'goiânia', 'campo grande'],
      'norte': ['manaus', 'belém', 'rio branco']
  }
  ```

#### 3. Modalidade (20% do score)
- Presencial vs Remoto
- Score 100 para modalidade idêntica
- Score 0 para modalidades diferentes

#### 4. Escolaridade (10% do score)
- Níveis próximos recebem scores maiores
- Diversidade controlada para equilíbrio
- Escala de compatibilidade entre níveis

### Parâmetros Configuráveis
```python
MIN_TEAM_SIZE = 3              # Tamanho mínimo de equipe
MAX_TEAM_SIZE = 5              # Tamanho máximo de equipe
MIN_COMPATIBILITY_SCORE = 55   # Score mínimo para formar equipe
REGION_BONUS = 15              # Bonus adicional para mesma região
```

---

## Componentes Principais

### 1. AutoTeamFormation (`auto_team_formation.py`)

#### Principais Métodos
- `executar_formacao_automatica()`: Método principal que executa todo o processo
- `agrupar_por_regiao_modalidade()`: Agrupa participantes por critérios geográficos
- `calcular_compatibilidade_grupo()`: Calcula score entre membros de um grupo
- `otimizar_distribuicao_equipes()`: Encontra melhor distribuição de equipes
- `gerar_nome_equipe()`: Cria nomes sugeridos baseados em habilidades

#### Exemplo de Uso
```python
from matchmaking.auto_team_formation import AutoTeamFormation

# Em contexto síncrono
auto_formation = AutoTeamFormation(sync_session)
resultados = auto_formation.executar_formacao_automatica()

print(f"Equipes formadas: {resultados['equipes_formadas']}")
print(f"Pessoas agrupadas: {resultados['participantes_agrupados']}")
```

### 2. TeamChannelManager (`team_channel_manager.py`)

#### Funcionalidades
- **Criação de Canais**: Cria canais privados para líderes
- **Painéis de Controle**: Interface com botões de ativar/desativar
- **Configuração**: Modais para definir preferências da equipe
- **Estatísticas**: Mostra métricas de aplicações e matchmaking

#### Estrutura de Canais
```
🎯 MATCHMAKING DE EQUIPES
├── 🤖matchmaking-equipe-alpha
├── 🤖matchmaking-equipe-beta
└── 🤖matchmaking-equipe-gamma
```

### 3. AutoTeamNotificationSystem (`auto_team_notifications.py`)

#### Características das Notificações
- **Rich Embeds**: Informações detalhadas sobre a equipe sugerida
- **Botões Interativos**: Aceitar/Rejeitar com feedback
- **Timeout Configurável**: 3 dias para decisão
- **Persistência**: Views mantêm estado após restart do bot

#### Exemplo de Embed de Notificação
```python
embed = discord.Embed(
    title="🚀 Nova Equipe Sugerida!",
    description="Encontramos uma equipe perfeita para você!",
    color=discord.Color.gold()
)
embed.add_field(name="🏆 Nome da Equipe", value="Python Squad #1")
embed.add_field(name="⭐ Compatibilidade", value="87.5%")
embed.add_field(name="👥 Tamanho", value="4 membros")
```

---

## Fluxo de Funcionamento

### 1. Execução Administrativa
```mermaid
sequenceDiagram
    participant A as Admin
    participant B as Bot
    participant C as Database
    participant D as Algorithm
    participant E as Users
    
    A->>B: Clica "🤖 Formar Equipes Automaticamente"
    B->>C: Busca participantes disponíveis
    C-->>B: Lista de participantes
    B->>D: Executa algoritmo de formação
    D-->>B: Equipes formadas com scores
    B->>E: Envia notificações via DM
    E-->>B: Aceita/Rejeita equipes
    B->>C: Atualiza status das equipes
```

### 2. Controle por Líderes
```mermaid
sequenceDiagram
    participant L as Leader
    participant B as Bot
    participant C as Channel
    participant D as Database
    
    L->>B: Clica "🏢 Criar Canal de Controle"
    B->>C: Cria canal privado
    C-->>L: Canal criado com painel
    L->>B: Clica "🟢 Ativar Matchmaking"
    B-->>L: Modal de configuração
    L->>B: Submete configurações
    B->>D: Registra equipe para matchmaking
    D-->>B: Confirmação
    B->>C: Atualiza painel (status ativo)
```

### 3. Processo de Aceitação
```mermaid
sequenceDiagram
    participant U as User
    participant B as Bot
    participant D as Database
    participant T as Team
    
    B->>U: Envia notificação de equipe sugerida
    U->>B: Clica "✅ Aceitar Equipe"
    B->>D: Marca usuário como indisponível
    D-->>B: Confirmação
    B-->>U: Feedback de aceitação
    
    Note over B,T: Quando todos membros aceitam:
    B->>T: Cria equipe no Discord
    B->>D: Atualiza banco de dados
    B->>U: Notifica criação da equipe
```

---

## Interface do Usuário

### 1. Painel Principal (`/equipes`)
Interface integrada com botões adicionais:

```
🔍 Sistema de Busca de Equipes

🔍 Ver Equipes Disponíveis     👥 Ver Pessoas Disponíveis
💼 Marcar Como Disponível      🤖 Formar Equipes Automaticamente*
                               🏢 Criar Canal de Controle
                               
* Apenas administradores
```

### 2. Canal de Controle de Equipe
Interface privada para líderes:

```
🤖 Painel de Matchmaking - [Nome da Equipe]

🎯 Status Atual: 🟢 Matchmaking Ativado
👑 Líder da Equipe: [Nome do Líder]
📍 Localização: [Cidade]
💻 Modalidade: [Presencial/Remoto]

⚙️ Configuração:
Habilidades: Python, React, Design
Tamanho Máximo: 6 membros

[🔴 Desativar Matchmaking] [⚙️ Configurar] [📊 Ver Estatísticas]
```

### 3. Notificação de Equipe Sugerida
DM enviada aos participantes:

```
🚀 Nova Equipe Sugerida!

🏆 Nome da Equipe: Python Squad #1
⭐ Compatibilidade: 87.5%
👥 Tamanho: 4 membros

👤 Seus Futuros Companheiros:
1. João Silva
   📍 São Paulo • 🎓 Superior Completo
2. Maria Santos  
   📍 São Paulo • 🎓 Superior em Andamento

🔧 Habilidades em Comum:
Python, React, Machine Learning

🌎 Localização: ✅ Todos da região: Sudeste
💻 Modalidade: Presencial

[✅ Aceitar Equipe] [❌ Rejeitar Equipe]
```

---

## Administração

### Comandos Administrativos

#### Execução do Algoritmo
- **Local**: Painel `/equipes`
- **Botão**: "🤖 Formar Equipes Automaticamente"
- **Permissão**: `administrator=True`
- **Resultado**: Relatório completo da execução

#### Monitoramento
```python
# Logs automáticos do sistema
logger.info(f"Algoritmo executado: {equipes_formadas} equipes criadas")
logger.info(f"Participantes agrupados: {participantes_agrupados}")
logger.warning(f"Notificações falharam: {notificacoes_falharam}")
```

### Métricas Importantes
- **Taxa de Sucesso**: % de equipes formadas vs. tentativas
- **Compatibilidade Média**: Score médio das equipes formadas
- **Taxa de Aceitação**: % de pessoas que aceitam sugestões
- **Distribuição Regional**: Equipes por região
- **Tempo de Resposta**: Tempo médio para decisões

### Relatório de Execução
```json
{
  "sucesso": true,
  "equipes_formadas": 8,
  "participantes_agrupados": 32,
  "participantes_restantes": 5,
  "notificacoes_enviadas": 32,
  "notificacoes_falharam": 1,
  "grupos_por_regiao": {
    "sudeste_presencial": 15,
    "nordeste_presencial": 12,
    "sul_remoto": 10
  },
  "equipes_detalhes": [...]
}
```

---

## Banco de Dados

### Modelos Principais

#### Participante
```sql
CREATE TABLE participantes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    sobrenome VARCHAR(100) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    modalidade modalidadeenum NOT NULL,
    escolaridade escolaridadeenum NOT NULL,
    disponivel_para_equipe BOOLEAN DEFAULT FALSE,
    descricao_habilidades TEXT,
    discord_user_id BIGINT UNIQUE NOT NULL,
    nome_equipe VARCHAR(100),
    -- outros campos...
);
```

#### MatchSugestao
```sql
CREATE TABLE match_sugestoes (
    id SERIAL PRIMARY KEY,
    participante_id INTEGER REFERENCES participantes(id),
    equipe_id INTEGER,
    score_compatibilidade INTEGER NOT NULL,
    razoes_match JSONB NOT NULL,
    status statusmatchenum DEFAULT 'PENDENTE',
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_expiracao TIMESTAMP NOT NULL,
    data_resposta TIMESTAMP
);
```

#### MatchmakingEquipe
```sql
CREATE TABLE matchmaking_equipes (
    id SERIAL PRIMARY KEY,
    nome_equipe VARCHAR(100) UNIQUE NOT NULL,
    lider_id INTEGER REFERENCES participantes(id),
    descricao TEXT,
    habilidades_desejadas TEXT NOT NULL,
    tamanho_maximo INTEGER DEFAULT 6,
    ativo BOOLEAN DEFAULT TRUE,
    preferencia_modalidade modalidadeenum NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Enums Utilizados
```python
class StatusMatchEnum(Enum):
    PENDENTE = "Pendente"
    ACEITO = "Aceito"
    REJEITADO = "Rejeitado"
    EXPIRADO = "Expirado"

class ModalidadeEnum(Enum):
    PRESENCIAL = "Presencial (Uberlândia)"
    REMOTO = "Remoto"

class EscolaridadeEnum(Enum):
    ENSINO_FUNDAMENTAL_INCOMPLETO = "Ensino Fundamental Incompleto"
    ENSINO_FUNDAMENTAL_COMPLETO = "Ensino Fundamental Completo"
    ENSINO_MEDIO_INCOMPLETO = "Ensino Médio Incompleto"
    ENSINO_MEDIO_COMPLETO = "Ensino Médio Completo"
    ENSINO_TECNICO_INCOMPLETO = "Ensino Técnico Incompleto"
    ENSINO_TECNICO_COMPLETO = "Ensino Técnico Completo"
    SUPERIOR_INCOMPLETO = "Superior Incompleto"
    SUPERIOR_COMPLETO = "Superior Completo"
    POS_GRADUACAO = "Pós-graduação"
    MESTRADO = "Mestrado"
    DOUTORADO = "Doutorado"
```

---

## Configuração e Deploy

### Variáveis de Ambiente
```env
# .env
DISCORD_TOKEN=seu_token_do_bot
GUILD_ID=id_do_servidor_opcional
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=seu_email
SMTP_PASSWORD=sua_senha_app
LOG_CHANNEL_ID=1402387427103998012
```

### Dependências
```txt
# requirements.txt
discord.py>=2.3.0
sqlalchemy>=2.0.0
asyncpg>=0.28.0
python-dotenv>=1.0.0
aiohttp>=3.8.0
```

### Instalação
```bash
# 1. Clone o repositório
git clone <repository_url>
cd disc

# 2. Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 3. Instale dependências
pip install -r requirements.txt

# 4. Configure .env
cp .env.example .env
# Edite .env com suas configurações

# 5. Initialize banco de dados
python setup.py

# 6. Execute o bot
python bot.py
```

### Estrutura de Deploy
```
production/
├── bot.py                    # Arquivo principal
├── matchmaking/             # Sistema de matchmaking
├── database/               # Modelos e configurações
├── views/                  # Interfaces Discord
├── handlers/              # Manipuladores de eventos
├── utils/                 # Utilitários
├── .env                   # Variáveis de ambiente
├── requirements.txt       # Dependências
└── logs/                  # Arquivos de log
```

---

## Troubleshooting

### Problemas Comuns

#### 1. Erro: "Nenhuma equipe foi formada"
**Causa**: Poucos participantes disponíveis ou scores baixos
**Solução**:
```python
# Verificar parâmetros do algoritmo
MIN_COMPATIBILITY_SCORE = 55  # Diminuir se necessário
MIN_TEAM_SIZE = 3             # Verificar se há pessoas suficientes
```

#### 2. Erro: "Não foi possível enviar DM"
**Causa**: Usuários com DMs desabilitadas
**Solução**: Sistema já trata isso graciosamente, verifica logs para estatísticas

#### 3. Views não respondem após restart
**Causa**: Views não são persistentes
**Solução**: Views já são adicionadas como persistentes no `setup_hook()`

#### 4. Erro de permissões no Discord
**Causa**: Bot sem permissões adequadas
**Solução**:
```
Permissões necessárias:
✅ Manage Channels
✅ Manage Roles  
✅ Send Messages
✅ Embed Links
✅ Add Reactions
✅ Read Message History
```

### Logs e Monitoramento

#### Localização dos Logs
- **Console**: Logs INFO e acima
- **Arquivo**: `nasa_spaceapps_bot.log` (todos os logs)
- **Discord**: Canal configurado (WARNING e ERROR)

#### Logs Importantes
```python
# Execução do algoritmo
logger.info("Iniciando formação automática de equipes")
logger.info(f"Encontrados {len(participantes)} participantes disponíveis")
logger.info(f"Formadas {equipes_formadas} equipes")

# Notificações
logger.info(f"Enviadas {notificacoes_enviadas} notificações")
logger.warning(f"Falharam {notificacoes_falharam} notificações")

# Erros críticos
logger.error("Erro ao executar algoritmo de formação", exc_info=True)
```

### Performance e Otimização

#### Métricas de Performance
- **Tempo de Execução**: ~2-5 segundos para 100 participantes
- **Uso de Memória**: ~50MB adicional durante execução
- **Queries de BD**: Otimizadas com eager loading

#### Otimizações Implementadas
```python
# Agrupamento por região reduz complexidade
grupos = self.agrupar_por_regiao_modalidade(participantes)

# Caching de habilidades extraídas
habilidades_cache = {}

# Batch processing de notificações
asyncio.gather(*[enviar_notificacao(p) for p in participantes])
```

### Backup e Recuperação

#### Backup Automático
```sql
-- Backup das sugestões de match
pg_dump -t match_sugestoes nasa_spaceapps > backup_matches.sql

-- Backup completo
pg_dump nasa_spaceapps > backup_completo.sql
```

#### Scripts de Recuperação
```python
# Reprocessar sugestões pendentes
async def reprocessar_sugestoes_pendentes():
    async with DatabaseManager.get_session() as session:
        sugestoes = await session.execute(
            select(MatchSugestao).where(
                MatchSugestao.status == StatusMatchEnum.PENDENTE,
                MatchSugestao.data_expiracao > datetime.utcnow()
            )
        )
        # Reenviar notificações...
```

---

## Roadmap e Melhorias Futuras

### Versão 2.0
- [ ] **Machine Learning**: Algoritmo de ML para melhor compatibilidade
- [ ] **Análise de Sentimentos**: Análise de descrições de habilidades
- [ ] **Matchmaking Contínuo**: Formação de equipes em tempo real
- [ ] **Dashboard Web**: Interface web para administradores

### Versão 2.1
- [ ] **API REST**: Endpoints para integração externa
- [ ] **Métricas Avançadas**: Grafana/Prometheus integration
- [ ] **Multi-idiomas**: Suporte a múltiplos idiomas
- [ ] **Notificações Push**: Integração com mobile

### Melhorias de UX
- [ ] **Wizard de Configuração**: Setup guiado para novos usuários
- [ ] **Preview de Equipes**: Visualizar equipe antes de aceitar
- [ ] **Histórico de Matches**: Ver histórico de sugestões
- [ ] **Feedback Loop**: Sistema de avaliação pós-formação

---

## Contribuição

### Padrões de Código
```python
# Docstrings obrigatórias
def calcular_compatibilidade(self, participante: Participante) -> Tuple[float, Dict]:
    """
    Calcula score de compatibilidade entre participante e equipe.
    
    Args:
        participante: Instância do participante
        
    Returns:
        Tuple com (score, detalhes_compatibilidade)
    """
    pass

# Type hints obrigatórias
async def processar_equipe(self, equipe_info: Dict[str, Any]) -> bool:
    pass

# Tratamento de erros
try:
    resultado = await operacao_arriscada()
except Exception as e:
    self.logger.error(f"Erro em operacao_arriscada: {e}", exc_info=True)
    return {"sucesso": False, "erro": str(e)}
```

### Testes
```python
# test_matchmaking.py
async def test_formacao_automatica():
    # Setup
    participantes = criar_participantes_teste()
    
    # Execução
    resultados = auto_formation.executar_formacao_automatica()
    
    # Verificação
    assert resultados["equipes_formadas"] > 0
    assert all(e["score_compatibilidade"] >= 55 for e in resultados["equipes_detalhes"])
```

### Pull Requests
1. Fork do repositório
2. Criar branch feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit das mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para branch (`git push origin feature/nova-funcionalidade`)
5. Criar Pull Request

---

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Suporte

Para suporte técnico, criar issue no GitHub ou contatar:
- **Email**: [contato@exemplo.com]
- **Discord**: [Server de Suporte]
- **Documentação**: [Link para docs]

---

*Documentação criada em: 2025-01-08*
*Versão: 1.0.0*
*Última atualização: 2025-01-08*