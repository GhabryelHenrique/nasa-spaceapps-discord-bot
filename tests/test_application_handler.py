"""
Testes para o handler de aplicações
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.application_handler import ApplicationHandler
from database.models import Participante, AplicacaoEquipe, EscolaridadeEnum, ModalidadeEnum, StatusAplicacaoEnum

class TestApplicationHandler:
    
    @pytest.fixture
    def mock_bot(self):
        """Cria um bot mock para testes"""
        bot = MagicMock()
        bot.fetch_user = AsyncMock()
        bot.guilds = []
        return bot
    
    @pytest.fixture
    def application_handler(self, mock_bot):
        """Cria uma instância do ApplicationHandler para testes"""
        return ApplicationHandler(mock_bot)
    
    @pytest.mark.asyncio
    async def test_get_pending_applications_no_user(self, application_handler):
        """Testa busca de aplicações quando usuário não existe"""
        with patch('handlers.application_handler.DatabaseManager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.execute = AsyncMock()
            mock_session.execute.return_value.scalars.return_value.first.return_value = None
            mock_get_session.return_value = mock_session
            
            aplicacoes, erro = await application_handler.get_pending_applications(123456789)
            
            assert aplicacoes is None
            assert erro == "Você não está inscrito no evento."
    
    @pytest.mark.asyncio
    async def test_get_pending_applications_success(self, application_handler, sample_participant_data):
        """Testa busca de aplicações com sucesso"""
        # Mock do participante (líder)
        lider = Participante(
            id=1,
            **sample_participant_data,
            escolaridade=EscolaridadeEnum.ENSINO_SUPERIOR,
            modalidade=ModalidadeEnum.PRESENCIAL
        )
        
        # Mock de aplicação pendente
        aplicacao = AplicacaoEquipe(
            id=1,
            aplicante_id=2,
            equipe_nome=sample_participant_data['nome_equipe'],
            lider_id=1,
            mensagem_aplicacao="Quero me juntar à equipe",
            status=StatusAplicacaoEnum.PENDENTE
        )
        
        with patch('handlers.application_handler.DatabaseManager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            # Mock das consultas
            mock_session.execute = AsyncMock()
            
            # Primeira consulta: buscar líder
            mock_result_lider = AsyncMock()
            mock_result_lider.scalars.return_value.first.return_value = lider
            
            # Segunda consulta: buscar aplicações
            mock_result_apps = AsyncMock()
            mock_result_apps.scalars.return_value.all.return_value = [aplicacao]
            
            mock_session.execute.side_effect = [mock_result_lider, mock_result_apps]
            mock_get_session.return_value = mock_session
            
            aplicacoes, erro = await application_handler.get_pending_applications(123456789)
            
            assert erro is None
            assert len(aplicacoes) == 1
            assert aplicacoes[0].status == StatusAplicacaoEnum.PENDENTE
    
    @pytest.mark.asyncio
    async def test_respond_to_application_approve(self, application_handler, sample_participant_data):
        """Testa aprovação de aplicação"""
        # Mock do líder
        lider = Participante(
            id=1,
            **sample_participant_data,
            escolaridade=EscolaridadeEnum.ENSINO_SUPERIOR,
            modalidade=ModalidadeEnum.PRESENCIAL
        )
        
        # Mock do aplicante
        aplicante_data = sample_participant_data.copy()
        aplicante_data.update({
            'discord_user_id': 987654321,
            'email': 'aplicante@example.com',
            'nome_equipe': 'Equipe Original'
        })
        
        aplicante = Participante(
            id=2,
            **aplicante_data,
            escolaridade=EscolaridadeEnum.GRADUANDO,
            modalidade=ModalidadeEnum.PRESENCIAL
        )
        
        # Mock da aplicação
        aplicacao = AplicacaoEquipe(
            id=1,
            aplicante_id=2,
            equipe_nome=sample_participant_data['nome_equipe'],
            lider_id=1,
            status=StatusAplicacaoEnum.PENDENTE
        )
        aplicacao.aplicante = aplicante
        
        with patch('handlers.application_handler.DatabaseManager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.execute = AsyncMock()
            
            # Simular consultas sequenciais
            results = [
                # Buscar líder
                MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=lider)))),
                # Buscar aplicação
                MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=aplicacao)))),
                # Buscar aplicante
                MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=aplicante)))),
                # Buscar membros da equipe (para verificar limite)
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[lider]))))  # Só o líder
            ]
            
            mock_session.execute.side_effect = results
            mock_get_session.return_value = mock_session
            
            # Mock do bot para envio de DM
            application_handler.bot.fetch_user.return_value = AsyncMock(send=AsyncMock())
            
            sucesso, mensagem = await application_handler.respond_to_application(
                123456789, 1, True, "Bem-vindo!"
            )
            
            assert sucesso is True
            assert mensagem == "Resposta enviada com sucesso!"
    
    @pytest.mark.asyncio
    async def test_respond_to_application_team_full(self, application_handler, sample_participant_data):
        """Testa rejeição por equipe cheia"""
        # Criar mocks de 6 membros (equipe cheia)
        membros = []
        for i in range(6):
            membro_data = sample_participant_data.copy()
            membro_data.update({
                'discord_user_id': 100000000 + i,
                'email': f'membro{i}@example.com'
            })
            membro = Participante(
                id=i+1,
                **membro_data,
                escolaridade=EscolaridadeEnum.ENSINO_SUPERIOR,
                modalidade=ModalidadeEnum.PRESENCIAL
            )
            membros.append(membro)
        
        lider = membros[0]
        aplicante = Participante(
            id=7,
            discord_user_id=987654321,
            email='aplicante@example.com',
            nome_equipe='Equipe Original',
            **{k: v for k, v in sample_participant_data.items() if k not in ['discord_user_id', 'email', 'nome_equipe']},
            escolaridade=EscolaridadeEnum.GRADUANDO,
            modalidade=ModalidadeEnum.PRESENCIAL
        )
        
        aplicacao = AplicacaoEquipe(
            id=1,
            aplicante_id=7,
            equipe_nome=sample_participant_data['nome_equipe'],
            lider_id=1,
            status=StatusAplicacaoEnum.PENDENTE
        )
        aplicacao.aplicante = aplicante
        
        with patch('handlers.application_handler.DatabaseManager.get_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.execute = AsyncMock()
            
            # Simular consultas
            results = [
                # Buscar líder
                MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=lider)))),
                # Buscar aplicação
                MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=aplicacao)))),
                # Buscar aplicante
                MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=aplicante)))),
                # Buscar membros da equipe (equipe cheia)
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=membros))))  # 6 membros
            ]
            
            mock_session.execute.side_effect = results
            mock_get_session.return_value = mock_session
            
            sucesso, mensagem = await application_handler.respond_to_application(
                123456789, 1, True, "Bem-vindo!"
            )
            
            assert sucesso is False
            assert "já está completa" in mensagem