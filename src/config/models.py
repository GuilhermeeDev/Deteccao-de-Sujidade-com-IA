from sqlalchemy import Column, Integer, String

def criar_tabela_resultados(Base):
    class ResultadoDB(Base):
        __tablename__ = "resultados"

        id = Column(Integer, primary_key=True, autoincrement=True)
        caracteristica = Column(String, nullable=False)
        data_processamento = Column(String, nullable=False)
        hora_processamento = Column(String, nullable=False)
        link_imagem = Column(String, nullable=False)
    
    return ResultadoDB

