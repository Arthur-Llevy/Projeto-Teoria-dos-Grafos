class Sala: 
    def __init__(self, nome: str):
        self.nome = nome
        

    def to_dict(self) -> dict:
        return {
            "nome": self.nome,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Sala":
        return cls(
            nome = data.get("nome", "")
        )