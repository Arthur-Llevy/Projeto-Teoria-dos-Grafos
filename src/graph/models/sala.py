class Sala:
    def __init__(self, id: str, nome: str, capacidade: int = 0):
        self.id = id
        self.nome = nome
        self.capacidade = capacidade

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "capacidade": self.capacidade,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Sala":
        return cls(
            id=data.get("id", ""),
            nome=data.get("nome", ""),
            capacidade=data.get("capacidade", 0),
        )
