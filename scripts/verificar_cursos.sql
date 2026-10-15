-- Verifica os cursos persistidos pela rota POST /courses.
-- Execute a partir do diretório do repositório, por exemplo:
-- sqlite3 ../grade_horaria.db < scripts/verificar_cursos.sql

.headers on
.mode column

SELECT
    cur_id AS id,
    COALESCE(NULLIF(TRIM(cur_nome), ''), cur_descricao, '') AS nome,
    CASE
        WHEN NULLIF(TRIM(cur_nome), '') IS NULL THEN ''
        ELSE COALESCE(cur_descricao, '')
    END AS descricao
FROM cur_curso
ORDER BY cur_id DESC;

-- Esta consulta deve retornar zero linhas: todo curso precisa ter nome.
SELECT cur_id AS id, cur_nome AS nome
FROM cur_curso
WHERE COALESCE(
    NULLIF(TRIM(cur_nome), ''),
    NULLIF(TRIM(cur_descricao), '')
) IS NULL;
