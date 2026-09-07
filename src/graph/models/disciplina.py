class Disciplina:
    def __init__(self, nome: str, carga_horaria: int, periodo: int):
        self.nome = nome
        self.carga_horaria = carga_horaria
        self.periodo = periodo

    def to_dict(self) -> dict:
        return {
            "nome": self.nome,
            "carga_horaria": self.carga_horaria,
            "periodo": self.periodo
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Disciplina":
        return cls(
            nome = data.get("nome", ""),
            carga_horaria = data.get("carga_horaria", 0),
            periodo = data.get("periodo", 0)
        )