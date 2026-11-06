-- Grade padrão da POLI/UPE: Segunda a Sexta, blocos A-L de 50 minutos,
-- das 07:10 às 17:10. Pode ser executado novamente sem duplicar os blocos.
CREATE TABLE IF NOT EXISTS hor_horario (
    hor_id INTEGER PRIMARY KEY,
    hor_codigo_slot VARCHAR(100),
    hor_dia_semana VARCHAR(20),
    hor_bloco VARCHAR(10),
    hor_hora_inicio TIME,
    hor_hora_fim TIME
);

WITH RECURSIVE
    dias(dia, prefixo) AS (
        VALUES
            ('Segunda', '2'),
            ('Terça', '3'),
            ('Quarta', '4'),
            ('Quinta', '5'),
            ('Sexta', '6')
    ),
    blocos(bloco, minuto_inicio) AS (
        VALUES ('A', 430)
        UNION ALL
        SELECT char(unicode(bloco) + 1), minuto_inicio + 50
        FROM blocos
        WHERE bloco < 'L'
    )
INSERT INTO hor_horario (
    hor_codigo_slot,
    hor_dia_semana,
    hor_bloco,
    hor_hora_inicio,
    hor_hora_fim
)
SELECT
    dias.prefixo || blocos.bloco,
    dias.dia,
    blocos.bloco,
    printf('%02d:%02d', blocos.minuto_inicio / 60, blocos.minuto_inicio % 60),
    printf(
        '%02d:%02d',
        (blocos.minuto_inicio + 50) / 60,
        (blocos.minuto_inicio + 50) % 60
    )
FROM dias
CROSS JOIN blocos
WHERE NOT EXISTS (
    SELECT 1
    FROM hor_horario AS existente
    WHERE existente.hor_dia_semana = dias.dia
      AND existente.hor_bloco = blocos.bloco
);
