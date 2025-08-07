"""
Testes para funcionalidades do banco de dados
"""

import pytest
from database.models import Participante, AplicacaoEquipe, EscolaridadeEnum, ModalidadeEnum, StatusAplicacaoEnum
from sqlalchemy import select

class TestDatabaseModels:
    
    @pytest.mark.asyncio
    async def test_create_participant(self, db_session, sample_participant_data):
        """Testa criação de um participante"""
        participante = Participante(
            **sample_participant_data,
            escolaridade=EscolaridadeEnum.ENSINO_SUPERIOR,
            modalidade=ModalidadeEnum.PRESENCIAL
        )
        
        db_session.add(participante)
        await db_session.commit()
        
        # Verificar se foi salvo
        result = await db_session.execute(
            select(Participante).where(Participante.email == sample_participant_data['email'])
        )
        saved_participant = result.scalars().first()
        
        assert saved_participant is not None
        assert saved_participant.nome == sample_participant_data['nome']
        assert saved_participant.email == sample_participant_data['email']
        assert saved_participant.escolaridade == EscolaridadeEnum.ENSINO_SUPERIOR
    
    @pytest.mark.asyncio
    async def test_unique_constraints(self, db_session, sample_participant_data):
        """Testa constraints de unicidade"""
        # Criar primeiro participante
        participante1 = Participante(
            **sample_participant_data,
            escolaridade=EscolaridadeEnum.ENSINO_SUPERIOR,
            modalidade=ModalidadeEnum.PRESENCIAL
        )
        db_session.add(participante1)
        await db_session.commit()
        
        # Tentar criar segundo participante com mesmo email (deve falhar)
        participante2 = Participante(
            discord_user_id=987654321,
            discord_username='outro#5678',
            nome='Maria',
            sobrenome='Santos',
            email=sample_participant_data['email'],  # Mesmo email
            telefone='11988776655',
            cpf='98765432100',
            cidade='São Paulo',
            data_nascimento='20/05/1990',
            escolaridade=EscolaridadeEnum.MESTRADO_COMPLETO,
            modalidade=ModalidadeEnum.REMOTO,
            nome_equipe='Outra Equipe'
        )
        
        db_session.add(participante2)
        
        with pytest.raises(Exception):  # Deve gerar erro de constraint
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_team_application_workflow(self, db_session, sample_participant_data, sample_team_application_data):
        """Testa fluxo completo de aplicação para equipe"""
        # Criar líder da equipe
        lider = Participante(
            **sample_participant_data,
            escolaridade=EscolaridadeEnum.ENSINO_SUPERIOR,
            modalidade=ModalidadeEnum.PRESENCIAL,
            nome_equipe=sample_team_application_data['equipe_nome']
        )
        db_session.add(lider)
        await db_session.flush()  # Para obter o ID
        
        # Criar aplicante
        aplicante_data = sample_participant_data.copy()
        aplicante_data.update({
            'discord_user_id': 987654321,
            'email': 'aplicante@example.com',
            'cpf': '98765432100',
            'nome_equipe': 'Equipe Original',
            'disponivel_para_equipe': True,
            'descricao_habilidades': 'Python, Machine Learning'
        })
        
        aplicante = Participante(
            **aplicante_data,
            escolaridade=EscolaridadeEnum.GRADUANDO,
            modalidade=ModalidadeEnum.PRESENCIAL
        )
        db_session.add(aplicante)
        await db_session.flush()
        
        # Criar aplicação
        aplicacao = AplicacaoEquipe(
            aplicante_id=aplicante.id,
            equipe_nome=sample_team_application_data['equipe_nome'],
            lider_id=lider.id,
            mensagem_aplicacao=sample_team_application_data['mensagem_aplicacao']
        )
        db_session.add(aplicacao)
        await db_session.commit()
        
        # Verificar aplicação criada
        result = await db_session.execute(
            select(AplicacaoEquipe).where(AplicacaoEquipe.aplicante_id == aplicante.id)
        )
        saved_application = result.scalars().first()
        
        assert saved_application is not None
        assert saved_application.status == StatusAplicacaoEnum.PENDENTE
        assert saved_application.equipe_nome == sample_team_application_data['equipe_nome']
        assert saved_application.mensagem_aplicacao == sample_team_application_data['mensagem_aplicacao']
        
        # Simular aprovação
        saved_application.status = StatusAplicacaoEnum.APROVADA
        saved_application.resposta_lider = "Bem-vindo à equipe!"
        await db_session.commit()
        
        # Verificar aprovação
        await db_session.refresh(saved_application)
        assert saved_application.status == StatusAplicacaoEnum.APROVADA
        assert saved_application.resposta_lider == "Bem-vindo à equipe!"
    
    @pytest.mark.asyncio 
    async def test_availability_marking(self, db_session, sample_participant_data):
        """Testa marcação de disponibilidade para equipes"""
        participante = Participante(
            **sample_participant_data,
            escolaridade=EscolaridadeEnum.ENSINO_SUPERIOR,
            modalidade=ModalidadeEnum.PRESENCIAL,
            disponivel_para_equipe=True,
            descricao_habilidades="Python, React, Design UI/UX"
        )
        
        db_session.add(participante)
        await db_session.commit()
        
        # Buscar participantes disponíveis
        result = await db_session.execute(
            select(Participante).where(Participante.disponivel_para_equipe == True)
        )
        disponiveis = result.scalars().all()
        
        assert len(disponiveis) == 1
        assert disponiveis[0].descricao_habilidades == "Python, React, Design UI/UX"