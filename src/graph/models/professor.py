class Professor:
    def __init__(self, id: str, nome: str, matricula: str = "", curso_id: str = ""):
        self.id = id
        self.nome = nome
        self.matricula = matricula
        self.curso_id = curso_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "matricula": self.matricula,
            "curso_id": self.curso_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Professor":
        return cls(
            id=data.get("id", ""),
            nome=data.get("nome", ""),
            matricula=data.get("matricula", ""),
            curso_id=data.get("curso_id", ""),
        )
