class Disciplina:
    def __init__(self, id: str, nome: str, codigo: str = "", carga_horaria: int = 0, periodo: int = 0, eh_eletiva: bool = False, curso_id: str = ""):
        self.id = id
        self.nome = nome
        self.codigo = codigo
        self.carga_horaria = carga_horaria
        self.periodo = periodo
        self.eh_eletiva = eh_eletiva
        self.curso_id = curso_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "codigo": self.codigo,
            "carga_horaria": self.carga_horaria,
            "periodo": self.periodo,
            "eh_eletiva": self.eh_eletiva,
            "curso_id": self.curso_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Disciplina":
        return cls(
            id=data.get("id", ""),
            nome=data.get("nome", ""),
            codigo=data.get("codigo", ""),
            carga_horaria=data.get("carga_horaria", 0),
            periodo=data.get("periodo", 0),
            eh_eletiva=data.get("eh_eletiva", False),
            curso_id=data.get("curso_id", ""),
        )
