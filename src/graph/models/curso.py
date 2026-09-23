class Curso:
    def __init__(self, id: str, nome: str, descricao: str = ""):
        self.id = id
        self.nome = nome
        self.descricao = descricao

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Curso":
        return cls(
            id=data.get("id", ""),
            nome=data.get("nome", ""),
            descricao=data.get("descricao", ""),
        )
