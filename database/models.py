from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Enum, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class EscolaridadeEnum(enum.Enum):
    FUNDAMENTAL_I = "Fundamental I"
    FUNDAMENTAL_II = "Fundamental II"
    ENSINO_MEDIO = "Ensino Médio"
    GRADUANDO = "Graduando"
    ENSINO_SUPERIOR = "Ensino Superior"
    ENSINO_SUPERIOR_COMPLETO = "Ensino Superior Completo"
    MESTRANDO = "Mestrando"
    MESTRADO_COMPLETO = "Mestrado Completo"
    DOUTORANDO = "Doutorando"
    DOUTORADO_COMPLETO = "Doutorado Completo"
    PHD_OU_MAIS = "PHD ou +"

class ModalidadeEnum(enum.Enum):
    PRESENCIAL = "Presencialmente em Uberlândia"
    REMOTO = "Remotamente de qualquer lugar do mundo"

class StatusAplicacaoEnum(enum.Enum):
    PENDENTE = "Pendente"
    APROVADA = "Aprovada"
    REJEITADA = "Rejeitada"
    CANCELADA = "Cancelada"

class Participante(Base):
    __tablename__ = 'participantes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_user_id = Column(BigInteger, unique=True, nullable=False)
    discord_username = Column(String(100), nullable=False)
    
    # Dados pessoais
    nome = Column(String(100), nullable=False)
    sobrenome = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    telefone = Column(String(20), nullable=False)
    cpf = Column(String(14), nullable=False, unique=True)
    cidade = Column(String(100), nullable=False)
    data_nascimento = Column(String(10), nullable=False)  # formato DD/MM/AAAA
    
    # Dados do evento
    escolaridade = Column(Enum(EscolaridadeEnum, values_callable=lambda x: [e.value for e in x]), nullable=False)
    modalidade = Column(Enum(ModalidadeEnum, values_callable=lambda x: [e.value for e in x]), nullable=False)
    
    # Dados da equipe
    nome_equipe = Column(String(100), nullable=False, unique=True)
    membros_convidados = Column(String(500), nullable=True)  # IDs dos usuários separados por vírgula
    
    # Status de disponibilidade para outras equipes
    disponivel_para_equipe = Column(Boolean, default=False)
    descricao_habilidades = Column(Text, nullable=True)  # Descrição das habilidades oferecidas
    
    # Metadados
    data_inscricao = Column(DateTime, default=datetime.utcnow)
    canal_privado_id = Column(BigInteger, nullable=True)
    
    def __repr__(self):
        return f"<Participante(nome='{self.nome}', email='{self.email}', modalidade='{self.modalidade.value}')>"

class AplicacaoEquipe(Base):
    __tablename__ = 'aplicacoes_equipe'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Referências
    aplicante_id = Column(Integer, ForeignKey('participantes.id'), nullable=False)
    equipe_nome = Column(String(100), nullable=False)  # Nome da equipe alvo
    lider_id = Column(Integer, ForeignKey('participantes.id'), nullable=False)
    
    # Dados da aplicação
    mensagem_aplicacao = Column(Text, nullable=True)  # Mensagem do aplicante
    status = Column(Enum(StatusAplicacaoEnum, values_callable=lambda x: [e.value for e in x]), default=StatusAplicacaoEnum.PENDENTE)
    resposta_lider = Column(Text, nullable=True)  # Resposta do líder (motivo da aprovação/rejeição)
    
    # Metadados
    data_aplicacao = Column(DateTime, default=datetime.utcnow)
    data_resposta = Column(DateTime, nullable=True)
    
    # Relacionamentos
    aplicante = relationship("Participante", foreign_keys=[aplicante_id])
    lider = relationship("Participante", foreign_keys=[lider_id])
    
    def __repr__(self):
        return f"<AplicacaoEquipe(aplicante='{self.aplicante.nome if self.aplicante else 'N/A'}', equipe='{self.equipe_nome}', status='{self.status.value}')>"