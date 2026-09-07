class Horario: 
    def __init__(self, periodo: str, dia: str, hora_inicio: str, hora_fim: str):
        self.periodo = periodo
        self.dia = dia
        self.hora_inicio = hora_inicio
        self.hora_fim = hora_fim

    def to_dict(self) -> dict:
        return {
            "periodo": self.periodo,
            "dia": self.dia,
            "hora_inicio": self.hora_inicio,
            "hora_fim": self.hora_fim
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Horario":
        return cls(
            periodo = data.get("periodo", ""),
            dia = data.get("dia", ""),
            hora_inicio = data.get("hora_inicio", ""),
            hora_fim = data.get("hora_fim", "")
        )