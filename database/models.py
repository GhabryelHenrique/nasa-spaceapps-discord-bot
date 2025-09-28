from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Enum, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class StatusSolicitacaoEnum(enum.Enum):
    PENDENTE = "Pendente"
    EM_ANDAMENTO = "Em Andamento"
    CONCLUIDA = "Concluída"
    CANCELADA = "Cancelada"

class SolicitacaoMentoria(Base):
    __tablename__ = 'solicitacoes_mentoria'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_user_id = Column(BigInteger, nullable=False)
    discord_username = Column(String(100), nullable=False)
    team_name = Column(String(100), nullable=True)  # Nome da equipe (mentoria para equipes)
    
    # Dados da solicitação
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=False)
    area_conhecimento = Column(String(100), nullable=False)
    nivel_urgencia = Column(String(20), nullable=False)  # Baixa, Média, Alta
    
    # Status
    status = Column(Enum(StatusSolicitacaoEnum, values_callable=lambda x: [e.value for e in x]), default=StatusSolicitacaoEnum.PENDENTE)
    mentor_discord_id = Column(BigInteger, nullable=True)  # ID do mentor que assumiu
    mentor_username = Column(String(100), nullable=True)
    
    # Metadados
    data_solicitacao = Column(DateTime, default=datetime.utcnow)
    data_assumida = Column(DateTime, nullable=True)
    data_conclusao = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<SolicitacaoMentoria(titulo='{self.titulo}', area='{self.area_conhecimento}', status='{self.status.value}')>"