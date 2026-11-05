-- Dados de desenvolvimento para conferir a geração de conflitos por docente.
-- Execute manualmente a partir da raiz do repositório:
-- sqlite3 ../grade_horaria.db < scripts/popular_professores_teste.sql
-- Requer ao menos um curso com três disciplinas. O script é idempotente e não
-- é executado automaticamente quando a aplicação inicia.

BEGIN IMMEDIATE;

INSERT INTO pro_professor (pro_nome, pro_matricula, cur_id)
SELECT 'Professor QA - conflito', 'QA-PROF-CONFLITO-01', c.cur_id
FROM cur_curso AS c
WHERE c.cur_id = (SELECT MIN(cur_id) FROM cur_curso)
  AND (
      SELECT COUNT(*) FROM dis_disciplina AS d WHERE d.cur_id = c.cur_id
  ) >= 3
  AND NOT EXISTS (
      SELECT 1 FROM pro_professor
      WHERE UPPER(TRIM(pro_matricula)) = 'QA-PROF-CONFLITO-01'
  );

INSERT INTO pro_professor (pro_nome, pro_matricula, cur_id)
SELECT 'Professora QA - alternativa', 'QA-PROF-CONFLITO-02', c.cur_id
FROM cur_curso AS c
WHERE c.cur_id = (SELECT MIN(cur_id) FROM cur_curso)
  AND (
      SELECT COUNT(*) FROM dis_disciplina AS d WHERE d.cur_id = c.cur_id
  ) >= 3
  AND NOT EXISTS (
      SELECT 1 FROM pro_professor
      WHERE UPPER(TRIM(pro_matricula)) = 'QA-PROF-CONFLITO-02'
  );

-- O primeiro docente fica associado às duas primeiras disciplinas do curso;
-- a segunda associação permite verificar um segundo docente no mesmo conjunto.
INSERT INTO alo_alocacao (pro_id, dis_id)
SELECT p.pro_id, d.dis_id
FROM pro_professor AS p
JOIN dis_disciplina AS d ON d.cur_id = p.cur_id
WHERE p.pro_matricula = 'QA-PROF-CONFLITO-01'
  AND d.dis_id IN (
      SELECT candidate.dis_id
      FROM dis_disciplina AS candidate
      WHERE candidate.cur_id = p.cur_id
      ORDER BY candidate.dis_id
      LIMIT 2
  )
  AND NOT EXISTS (
      SELECT 1 FROM alo_alocacao AS a
      WHERE a.pro_id = p.pro_id AND a.dis_id = d.dis_id
  );

INSERT INTO alo_alocacao (pro_id, dis_id)
SELECT p.pro_id, d.dis_id
FROM pro_professor AS p
JOIN dis_disciplina AS d ON d.cur_id = p.cur_id
WHERE p.pro_matricula = 'QA-PROF-CONFLITO-02'
  AND d.dis_id = (
      SELECT candidate.dis_id
      FROM dis_disciplina AS candidate
      WHERE candidate.cur_id = p.cur_id
      ORDER BY candidate.dis_id
      LIMIT 1 OFFSET 2
  )
  AND NOT EXISTS (
      SELECT 1 FROM alo_alocacao AS a
      WHERE a.pro_id = p.pro_id AND a.dis_id = d.dis_id
  );

COMMIT;

-- Verifica os docentes e suas alocações de teste.
SELECT p.pro_id, p.pro_nome, p.pro_matricula, COUNT(a.alo_id) AS disciplinas_alocadas
FROM pro_professor AS p
LEFT JOIN alo_alocacao AS a ON a.pro_id = p.pro_id
WHERE p.pro_matricula IN ('QA-PROF-CONFLITO-01', 'QA-PROF-CONFLITO-02')
GROUP BY p.pro_id, p.pro_nome, p.pro_matricula
ORDER BY p.pro_matricula;
