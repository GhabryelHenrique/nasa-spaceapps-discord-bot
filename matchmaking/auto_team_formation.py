import json
import itertools
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import sessionmaker

from database.models import Participante, MatchSugestao, StatusMatchEnum, ModalidadeEnum
from matchmaking.algorithm import MatchmakingAlgorithm


class AutoTeamFormation:
    def __init__(self, session):
        self.session = session
        self.algorithm = MatchmakingAlgorithm(session)
        
        # Configurações do algoritmo
        self.MIN_TEAM_SIZE = 3
        self.MAX_TEAM_SIZE = 5
        self.MIN_COMPATIBILITY_SCORE = 55  # Score mínimo para formar equipe
        self.REGION_BONUS = 15  # Bonus adicional para mesma região
        
    def agrupar_por_regiao_modalidade(self, participantes: List[Participante]) -> Dict:
        """
        Agrupa participantes por região e modalidade para otimizar matchmaking
        """
        grupos = defaultdict(list)
        
        for participante in participantes:
            regiao = self.algorithm.extrair_regiao(participante.cidade)
            modalidade = participante.modalidade.value
            key = f"{regiao}_{modalidade}"
            grupos[key].append(participante)
        
        return dict(grupos)
    
    def calcular_compatibilidade_grupo(self, grupo_participantes: List[Participante]) -> Tuple[float, Dict]:
        """
        Calcula compatibilidade média entre todos os membros de um grupo
        """
        if len(grupo_participantes) < 2:
            return 0, {}
        
        scores = []
        detalhes_combinados = {
            "habilidades_comum": set(),
            "regioes": set(),
            "modalidades": set(),
            "escolaridades": set(),
            "compatibilidades": []
        }
        
        # Calcular compatibilidade entre todos os pares
        for i in range(len(grupo_participantes)):
            for j in range(i + 1, len(grupo_participantes)):
                p1, p2 = grupo_participantes[i], grupo_participantes[j]
                
                # Criar "equipe virtual" para usar algoritmo existente
                from database.models import MatchmakingEquipe
                equipe_virtual = MatchmakingEquipe(
                    nome_equipe=f"Virtual_{p1.nome}",
                    lider_id=p1.id,
                    lider=p1,
                    habilidades_desejadas=p1.descricao_habilidades or "",
                    preferencia_modalidade=p1.modalidade
                )
                
                score, razoes = self.algorithm.calcular_score_compatibilidade(p2, equipe_virtual)
                
                # Bonus por mesma região
                regiao_p1 = self.algorithm.extrair_regiao(p1.cidade)
                regiao_p2 = self.algorithm.extrair_regiao(p2.cidade)
                if regiao_p1 == regiao_p2 and regiao_p1 != "desconhecida":
                    score += self.REGION_BONUS
                
                scores.append(min(score, 100))  # Cap em 100
                
                # Coletar detalhes
                detalhes = razoes.get("detalhes", {})
                if "habilidades_participante" in detalhes and "habilidades_equipe" in detalhes:
                    habilidades_p1 = set(detalhes.get("habilidades_equipe", []))
                    habilidades_p2 = set(detalhes.get("habilidades_participante", []))
                    detalhes_combinados["habilidades_comum"].update(
                        habilidades_p1.intersection(habilidades_p2)
                    )
                
                detalhes_combinados["regioes"].add(regiao_p1)
                detalhes_combinados["regioes"].add(regiao_p2)
                detalhes_combinados["modalidades"].add(p1.modalidade.value)
                detalhes_combinados["modalidades"].add(p2.modalidade.value)
                detalhes_combinados["escolaridades"].add(p1.escolaridade.value)
                detalhes_combinados["escolaridades"].add(p2.escolaridade.value)
                
                detalhes_combinados["compatibilidades"].append({
                    "p1": f"{p1.nome} {p1.sobrenome}",
                    "p2": f"{p2.nome} {p2.sobrenome}", 
                    "score": score
                })
        
        score_medio = sum(scores) / len(scores) if scores else 0
        
        # Converter sets para listas para serialização JSON
        for key, value in detalhes_combinados.items():
            if isinstance(value, set):
                detalhes_combinados[key] = list(value)
        
        return score_medio, detalhes_combinados
    
    def gerar_combinacoes_equipes(self, participantes: List[Participante]) -> List[Tuple[List[Participante], float, Dict]]:
        """
        Gera todas as combinações possíveis de equipes e calcula suas compatibilidades
        """
        equipes_candidatas = []
        
        # Gerar combinações de diferentes tamanhos
        for tamanho in range(self.MIN_TEAM_SIZE, min(self.MAX_TEAM_SIZE + 1, len(participantes) + 1)):
            for combinacao in itertools.combinations(participantes, tamanho):
                score, detalhes = self.calcular_compatibilidade_grupo(list(combinacao))
                
                if score >= self.MIN_COMPATIBILITY_SCORE:
                    equipes_candidatas.append((list(combinacao), score, detalhes))
        
        # Ordenar por score (maior primeiro)
        equipes_candidatas.sort(key=lambda x: x[1], reverse=True)
        
        return equipes_candidatas
    
    def otimizar_distribuicao_equipes(self, participantes: List[Participante]) -> List[Tuple[List[Participante], float, Dict]]:
        """
        Encontra a melhor distribuição de equipes que maximize a compatibilidade total
        """
        if len(participantes) < self.MIN_TEAM_SIZE:
            return []
        
        melhores_equipes = []
        participantes_restantes = participantes.copy()
        
        while len(participantes_restantes) >= self.MIN_TEAM_SIZE:
            # Gerar combinações apenas com participantes restantes
            combinacoes = self.gerar_combinacoes_equipes(participantes_restantes)
            
            if not combinacoes:
                break
            
            # Pegar a melhor combinação
            melhor_equipe, score, detalhes = combinacoes[0]
            
            # Verificar se vale a pena formar esta equipe
            if score >= self.MIN_COMPATIBILITY_SCORE:
                melhores_equipes.append((melhor_equipe, score, detalhes))
                
                # Remover participantes já alocados
                for participante in melhor_equipe:
                    if participante in participantes_restantes:
                        participantes_restantes.remove(participante)
            else:
                break
        
        return melhores_equipes
    
    def executar_formacao_automatica(self) -> Dict:
        """
        Executa o algoritmo completo de formação automática de equipes
        """
        resultados = {
            "equipes_formadas": 0,
            "participantes_agrupados": 0,
            "participantes_restantes": 0,
            "equipes_detalhes": [],
            "grupos_por_regiao": {}
        }
        
        # Buscar participantes disponíveis
        participantes_disponiveis = self.session.query(Participante).filter(
            Participante.disponivel_para_equipe == True
        ).all()
        
        if len(participantes_disponiveis) < self.MIN_TEAM_SIZE:
            resultados["erro"] = f"Apenas {len(participantes_disponiveis)} pessoas disponíveis. Mínimo: {self.MIN_TEAM_SIZE}"
            return resultados
        
        # Agrupar por região e modalidade
        grupos = self.agrupar_por_regiao_modalidade(participantes_disponiveis)
        resultados["grupos_por_regiao"] = {k: len(v) for k, v in grupos.items()}
        
        todas_equipes_formadas = []
        todos_participantes_alocados = []
        
        # Processar cada grupo separadamente
        for grupo_key, participantes_grupo in grupos.items():
            if len(participantes_grupo) >= self.MIN_TEAM_SIZE:
                equipes_grupo = self.otimizar_distribuicao_equipes(participantes_grupo)
                
                for equipe, score, detalhes in equipes_grupo:
                    todas_equipes_formadas.append((equipe, score, detalhes, grupo_key))
                    todos_participantes_alocados.extend(equipe)
        
        # Se ainda há muitas pessoas disponíveis, tentar formar equipes inter-regionais
        participantes_nao_alocados = [p for p in participantes_disponiveis if p not in todos_participantes_alocados]
        
        if len(participantes_nao_alocados) >= self.MIN_TEAM_SIZE:
            equipes_extras = self.otimizar_distribuicao_equipes(participantes_nao_alocados)
            
            for equipe, score, detalhes in equipes_extras:
                todas_equipes_formadas.append((equipe, score, detalhes, "inter_regional"))
                todos_participantes_alocados.extend(equipe)
        
        # Processar resultados finais
        resultados["equipes_formadas"] = len(todas_equipes_formadas)
        resultados["participantes_agrupados"] = len(todos_participantes_alocados)
        resultados["participantes_restantes"] = len(participantes_disponiveis) - len(todos_participantes_alocados)
        
        for i, (equipe, score, detalhes, grupo) in enumerate(todas_equipes_formadas, 1):
            nome_equipe_sugerido = self.gerar_nome_equipe(equipe, i)
            
            equipe_info = {
                "id": i,
                "nome_sugerido": nome_equipe_sugerido,
                "membros": [
                    {
                        "nome": f"{p.nome} {p.sobrenome}",
                        "cidade": p.cidade,
                        "escolaridade": p.escolaridade.value,
                        "habilidades": p.descricao_habilidades,
                        "user_id": p.discord_user_id
                    } for p in equipe
                ],
                "score_compatibilidade": round(score, 1),
                "detalhes_compatibilidade": detalhes,
                "grupo_origem": grupo,
                "tamanho": len(equipe)
            }
            
            resultados["equipes_detalhes"].append(equipe_info)
        
        return resultados
    
    def gerar_nome_equipe(self, equipe: List[Participante], numero: int) -> str:
        """
        Gera um nome sugerido para a equipe baseado nas habilidades dos membros
        """
        # Coletar todas as habilidades
        todas_habilidades = []
        for participante in equipe:
            if participante.descricao_habilidades:
                habilidades = self.algorithm.extrair_habilidades(participante.descricao_habilidades)
                todas_habilidades.extend(habilidades)
        
        # Encontrar habilidades mais comuns
        from collections import Counter
        habilidades_contador = Counter(todas_habilidades)
        
        if habilidades_contador:
            habilidade_principal = habilidades_contador.most_common(1)[0][0]
            
            # Mapear habilidades para nomes de equipe
            nomes_mapeados = {
                "python": "Python Squad",
                "javascript": "JS Innovators", 
                "react": "React Force",
                "design": "Design Masters",
                "machine learning": "ML Warriors",
                "data science": "Data Wizards",
                "ai": "AI Pioneers",
                "unity": "Game Creators",
                "figma": "Design Squad",
                "comunicação": "Communication Hub",
                "liderança": "Leadership Team"
            }
            
            nome_base = nomes_mapeados.get(habilidade_principal.lower(), f"Team {habilidade_principal.title()}")
        else:
            nome_base = "Dream Team"
        
        return f"{nome_base} #{numero}"
    
    def criar_sugestoes_equipe(self, equipe_info: Dict) -> List[MatchSugestao]:
        """
        Cria sugestões de match para cada membro da equipe sugerida
        """
        sugestoes = []
        
        for membro_info in equipe_info["membros"]:
            # Buscar participante
            participante = self.session.query(Participante).filter(
                Participante.discord_user_id == membro_info["user_id"]
            ).first()
            
            if participante:
                # Criar sugestão de equipe virtual
                razoes_match = {
                    "tipo": "formacao_automatica",
                    "score_equipe": equipe_info["score_compatibilidade"],
                    "detalhes": equipe_info["detalhes_compatibilidade"],
                    "equipe_sugerida": {
                        "nome": equipe_info["nome_sugerido"],
                        "membros": [m["nome"] for m in equipe_info["membros"] if m["user_id"] != membro_info["user_id"]],
                        "tamanho": equipe_info["tamanho"]
                    }
                }
                
                sugestao = MatchSugestao(
                    participante_id=participante.id,
                    equipe_id=None,  # Equipe ainda não existe
                    score_compatibilidade=int(equipe_info["score_compatibilidade"]),
                    razoes_match=json.dumps(razoes_match, ensure_ascii=False),
                    status=StatusMatchEnum.PENDENTE,
                    data_expiracao=datetime.utcnow() + timedelta(days=3)  # 3 dias para decidir
                )
                
                sugestoes.append((sugestao, participante, equipe_info))
        
        return sugestoes
    
    def processar_todas_sugestoes(self, resultados_formacao: Dict) -> Dict:
        """
        Processa todas as sugestões de equipes formadas automaticamente
        """
        sugestoes_criadas = 0
        sugestoes_por_equipe = {}
        
        for equipe_info in resultados_formacao["equipes_detalhes"]:
            sugestoes = self.criar_sugestoes_equipe(equipe_info)
            
            sugestoes_por_equipe[equipe_info["id"]] = []
            
            for sugestao, participante, info_equipe in sugestoes:
                self.session.add(sugestao)
                sugestoes_por_equipe[equipe_info["id"]].append({
                    "participante": f"{participante.nome} {participante.sobrenome}",
                    "sugestao_id": sugestao.id if hasattr(sugestao, 'id') else 'pending'
                })
                sugestoes_criadas += 1
        
        self.session.commit()
        
        return {
            "sugestoes_criadas": sugestoes_criadas,
            "equipes_processadas": len(sugestoes_por_equipe),
            "sugestoes_por_equipe": sugestoes_por_equipe
        }