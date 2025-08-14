# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Discord bot for managing mentorship requests. Users can request help from experienced mentors in various technical areas through an interactive form system.

**Key Features:**
- Interactive multi-step mentorship request form
- PostgreSQL database for storing mentorship requests
- Automatic mentor notifications in dedicated channel
- Request tracking with status management
- **Comprehensive logging system with Discord integration**
- Administrative commands for statistics and data export
- Real-time mentor response system

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
- `MentoriaBot` class extends `commands.Bot`
- Handles setup, command synchronization, and message routing
- Manages handler instance (`mentoria_handler`)
- Provides both prefix commands (`!setup`, `!stats`, `!export`) and slash commands

**Database Layer:**
- `database/setup.py` - Simplified database setup and configuration
- `database/db.py` - Compatibility layer for existing imports
- `database/models.py` - SQLAlchemy models with enums for mentorship system
- Dual engine approach: sync for table creation, async for bot operations

**Mentorship Request System:**
- `handlers/mentoria_handler.py` - Multi-step form handler with validation
- `views/mentoria_view.py` - Discord UI buttons for starting mentorship requests
- Creates private channels or uses DMs for each user's request process
- Comprehensive validation for title, area, description, and urgency

**Mentor Notification System:**
- Automatic notifications to mentors channel when new request is created
- Interactive buttons for mentors to claim requests
- Real-time status updates when mentors assume requests
- User notifications when their request is claimed by a mentor

**Administrative Features:**
- Statistics command shows request counts by status, area, and urgency
- Export command generates text file with all mentorship request data
- Both prefix and slash command versions available

**Mentorship Management:**
- `/setup` - Setup mentorship request panel
- `/stats` - View mentorship statistics (admin only)
- `/export` - Export mentorship data (admin only)
- `/solicitacoes` - View pending requests (mentors only)
- Status tracking: Pendente, Em Andamento, Concluída, Cancelada

### Data Flow

1. User clicks "Solicitar Ajuda" button → Private channel created or DM initiated
2. Step-by-step form collection with real-time validation
3. Request submission → Database storage with unique ID
4. Automatic mentor notification → Interactive response buttons
5. Mentor claims request → User notification and status update

### Key Design Patterns

**Async Session Management:**
- Uses `DatabaseManager.get_session()` for database operations
- Proper session cleanup with async context managers

**Multi-Step Form Handler:**
- State management via `user_sessions` dictionary in `mentoria_handler.py`
- Sequential validation with custom validators per field (title, area, description, urgency)
- Graceful cancellation and error handling

**Channel-Based or DM Communication:**
- Creates temporary private channels under "Solicitações Mentoria" category
- Falls back to DMs if channel creation fails
- Automatic cleanup after successful request submission

## Environment Configuration

Required `.env` variables:
```
DISCORD_TOKEN=your_bot_token
GUILD_ID=your_server_id_optional
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
LOG_CHANNEL_ID=1402387427103998012  # Discord channel for error/warning logs
```

## Database Schema

**solicitacoes_mentoria table:**
- Request identification: id (primary key), discord_user_id, discord_username
- Request content: titulo, descricao, area_conhecimento, nivel_urgencia
- Status tracking: status (enum), mentor_discord_id, mentor_username
- Timestamps: data_solicitacao, data_assumida, data_conclusao

**Enums:**
- **`StatusSolicitacaoEnum`: Pendente, Em Andamento, Concluída, Cancelada**

**Key Fields:**
- `titulo`: Short descriptive title (max 200 chars)
- `descricao`: Detailed description of the help needed (max 2000 chars)
- `area_conhecimento`: Technical area (e.g., "Python", "JavaScript", etc.)
- `nivel_urgencia`: Priority level ("Baixa", "Média", "Alta")
- `mentor_discord_id`: ID of mentor who claimed the request
- `status`: Current status of the mentorship request

## Common Debugging

**Channel Creation Issues:**
- Check bot permissions for Manage Channels
- Verify "Solicitações Mentoria" category exists or can be created
- Ensure unique channel naming for each user

**Database Connection:**
- Verify PostgreSQL is running and accessible
- Check DATABASE_URL format and credentials
- Ensure enums are created before table creation

**Mentor Notifications:**
- Verify "mentores" channel exists in the server
- Check bot has permission to send messages in mentor channel
- Ensure mentors have the "Mentor" role for `/solicitacoes` command

**Request Processing:**
- DM sending can fail if users have DMs disabled
- Channel creation falls back to DMs automatically
- User sessions are stored in memory (not persistent across restarts)

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
1. Mentorship request button interaction
2. Multi-step form completion (title → area → description → urgency)
3. Mentor notification and response
4. Request status tracking
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
- User mentorship request attempts and completions
- Database operations (success/failure)
- Command executions
- Mentor operations and request assignments
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
- Request channels are automatically deleted after successful submission
- Mentorship requests persist in database with full lifecycle tracking
- All validation ensures proper input formatting and length limits
- **All errors and warnings are automatically sent to the configured Discord channel**
- Mentor role is required to use `/solicitacoes` command
- System supports fallback from channel creation to direct messages