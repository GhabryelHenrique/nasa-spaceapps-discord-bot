# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Discord bot for managing NASA Space Apps Challenge registrations in Uberlândia. The bot creates interactive registration forms through private channels and manages team creation with roles, categories, and channels.

**Key Features:**
- Interactive multi-step registration form in private channels
- PostgreSQL database with comprehensive participant data
- Automatic team infrastructure creation (roles, categories, channels)
- Team invitation system via DM
- **Team search and application system**
- **Availability marking for team-less participants**
- **Application approval/rejection workflow for team leaders**
- **Comprehensive logging system with Discord integration**
- Administrative commands for statistics and data export
- Email verification system for existing registrations

## Development Commands

### Setup and Installation
```bash
# Complete setup (recommended for first time)
python setup.py

# Quick database initialization only
python init_db.py
```

### Running the Bot
```bash
# Main bot execution
python bot.py

# Simple initialization (minimal setup)
python simple_init.py
```

### Testing
```bash
# Run all tests
python tests/run_tests.py

# Run tests with pytest directly
pytest

# Run specific test file
pytest tests/test_database.py -v
```

### Dependencies
```bash
# Install all required packages (includes testing dependencies)
pip install -r requirements.txt
```

## Architecture Overview

### Core Components

**Bot Structure (bot.py):**
- `NASASpaceAppsBot` class extends `commands.Bot`
- Handles setup, command synchronization, and message routing
- Manages handler instances (`registration_handler`, `email_verification_handler`)
- Provides both prefix commands (`!setup`, `!stats`, `!export`) and slash commands

**Database Layer:**
- `database/setup.py` - Simplified database setup and configuration
- `database/db.py` - Compatibility layer for existing imports
- `database/models.py` - SQLAlchemy models with enums for all tables
- Dual engine approach: sync for table creation, async for bot operations

**Registration System:**
- `handlers/registration_form.py` - Multi-step form handler with validation
- `views/register_view.py` - Discord UI buttons for starting registration
- Creates private channels for each user's registration process
- Comprehensive validation for CPF, email, phone, dates

**Team Management:**
- Automatic role creation for each team
- Category and channel creation (chat-geral, desenvolvimento, voice)
- Team invitation system via DM with accept/decline buttons
- Maximum team size enforcement (6 members including leader)

**Administrative Features:**
- Statistics command shows registration counts by modality and education
- Export command generates text file with all participant data
- Both prefix and slash command versions available

**Team Search System:**
- `/equipes` - Main panel for team search functionality
- `/aplicacoes` - Team leaders manage incoming applications
- `/minhas_aplicacoes` - Users track their submitted applications
- Availability marking system for team-less participants
- Application workflow with approval/rejection and automatic role management

### Data Flow

1. User clicks registration button → Private channel created
2. Step-by-step form collection with real-time validation
3. Team name uniqueness check → Team infrastructure creation
4. Role assignment → Invitation system activated
5. Welcome messages → Cleanup of registration channel

### Key Design Patterns

**Async Session Management:**
- Uses `DatabaseManager.get_session()` for database operations
- Proper session cleanup with async context managers

**Multi-Step Form Handler:**
- State management via `user_sessions` dictionary
- Sequential validation with custom validators per field
- Graceful cancellation and error handling

**Permission-Based Channel Creation:**
- Category-based organization for registration and verification channels
- Role-specific overwrites for team channels
- Automatic cleanup after successful registration

## Environment Configuration

Required `.env` variables:
```
DISCORD_TOKEN=your_bot_token
GUILD_ID=your_server_id_optional
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_app_password
LOG_CHANNEL_ID=1402387427103998012  # Discord channel for error/warning logs
```

## Database Schema

**participantes table:**
- Personal data: name, email, phone, CPF, city, birth date
- Event data: education level (enum), participation mode (enum)
- Team data: team name (unique), invited members (comma-separated IDs)
- **Availability data: disponivel_para_equipe (boolean), descricao_habilidades (text)**
- Discord metadata: user ID, username, private channel ID
- Timestamps: registration date

**aplicacoes_equipe table:**
- Application data: aplicante_id, equipe_nome, lider_id
- Content: mensagem_aplicacao, status (enum), resposta_lider
- Timestamps: data_aplicacao, data_resposta
- Foreign key relationships to participantes table

**Enums:**
- `EscolaridadeEnum`: 11 education levels from elementary to PhD
- `ModalidadeEnum`: Presencial (Uberlândia) or Remote participation
- **`StatusAplicacaoEnum`: Pendente, Aprovada, Rejeitada, Cancelada**

## Common Debugging

**Channel Creation Issues:**
- Check bot permissions for Manage Channels
- Verify category exists or can be created
- Ensure unique channel naming

**Database Connection:**
- Verify PostgreSQL is running and accessible
- Check DATABASE_URL format and credentials
- Ensure enums are created before table creation

**Team Infrastructure:**
- Role creation requires Manage Roles permission
- Category permissions need careful overwrite setup
- DM sending can fail if users have DMs disabled

## Testing

### Automated Tests
The project includes comprehensive unit tests:

```bash
# Run all tests
python tests/run_tests.py

# Run specific test categories
pytest tests/test_database.py      # Database model tests
pytest tests/test_utils.py         # Validation function tests
pytest tests/test_application_handler.py  # Application handler tests
```

### Test Coverage
- **Database Models**: Creation, constraints, relationships
- **Validation Functions**: CPF, email, phone, date validation
- **Application Handler**: Team application workflow
- **Utility Functions**: Formatting and helper functions

### Manual Testing
Test the complete Discord integration flow:
1. Registration button interaction
2. Multi-step form completion  
3. Team creation and role assignment
4. Team search and application system
5. Administrative command execution

## Logging System

The bot includes a comprehensive logging system that:

**Log Levels:**
- **INFO**: General operations, successful actions
- **WARNING**: Non-critical issues, failed operations
- **ERROR**: Critical errors, exceptions

**Log Destinations:**
- **Console**: All logs (INFO and above)
- **File**: All logs including DEBUG (`nasa_spaceapps_bot.log`)
- **Discord Channel**: Only WARNING and ERROR logs sent as embeds

**Key Logged Events:**
- User registration attempts and completions
- Database operations (success/failure)
- Command executions
- Team operations and applications
- Bot startup/shutdown events
- All errors with full stack traces

**Discord Log Format:**
- Colored embeds based on log level
- Module, function, and line number information
- Full error messages and stack traces
- Timestamps and metadata

## Development Notes

- Bot maintains persistent views for buttons across restarts
- User sessions are stored in memory (not persistent across restarts)
- Registration channels are automatically deleted after successful completion
- Team infrastructure persists until manually removed
- All validation follows Brazilian standards (CPF format, phone with DDD)
- **All errors and warnings are automatically sent to the configured Discord channel**