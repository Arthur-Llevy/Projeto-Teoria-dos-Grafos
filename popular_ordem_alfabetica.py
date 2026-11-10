import sqlite3

# Conecta ao arquivo do banco (cria se não existir)
conn = sqlite3.connect("grade_horaria.db")
cursor = conn.cursor()

# Script SQL com a criação e carga dos dados
sql_script = """
PRAGMA foreign_keys = OFF;

-- =====================================================================
-- BLOCO 1: EXCLUSÃO E CRIAÇÃO DE OBJETOS (ORDEM ALFABÉTICA)
-- =====================================================================

DROP TABLE IF EXISTS alo_alocacao;
DROP TABLE IF EXISTS cur_curso;
DROP TABLE IF EXISTS dis_disciplina;
DROP TABLE IF EXISTS gra_grade_horaria;
DROP TABLE IF EXISTS hor_horario;
DROP TABLE IF EXISTS pro_professor;
DROP TABLE IF EXISTS sal_sala;

CREATE TABLE alo_alocacao (
    alo_id INTEGER PRIMARY KEY,
    pro_id INTEGER,
    dis_id INTEGER,
    FOREIGN KEY (pro_id) REFERENCES pro_professor(pro_id),
    FOREIGN KEY (dis_id) REFERENCES dis_disciplina(dis_id)
);

CREATE TABLE cur_curso (
    cur_id INTEGER PRIMARY KEY,
    cur_descricao VARCHAR(100)
);

CREATE TABLE dis_disciplina (
    dis_id INTEGER PRIMARY KEY,
    dis_codigo VARCHAR(20),
    dis_descricao VARCHAR(100),
    dis_periodo INTEGER,
    dis_carga_horaria INTEGER,
    dis_eh_eletiva BOOLEAN,
    cur_id INTEGER,
    FOREIGN KEY (cur_id) REFERENCES cur_curso(cur_id)
);

CREATE TABLE gra_grade_horaria (
    gra_id INTEGER PRIMARY KEY,
    gra_semestre VARCHAR(10),
    alo_id INTEGER,
    hor_id INTEGER,
    sal_id INTEGER,
    FOREIGN KEY (alo_id) REFERENCES alo_alocacao(alo_id),
    FOREIGN KEY (hor_id) REFERENCES hor_horario(hor_id),
    FOREIGN KEY (sal_id) REFERENCES sal_sala(sal_id)
);

CREATE TABLE hor_horario (
    hor_id INTEGER PRIMARY KEY,
    hor_codigo_slot VARCHAR(100),
    hor_dia_semana VARCHAR(20),
    hor_bloco VARCHAR(10),
    hor_hora_inicio TIME,
    hor_hora_fim TIME
);

CREATE TABLE pro_professor (
    pro_id INTEGER PRIMARY KEY,
    pro_nome VARCHAR(100),
    pro_matricula VARCHAR(20),
    cur_id INTEGER,
    FOREIGN KEY (cur_id) REFERENCES cur_curso(cur_id)
);

CREATE TABLE sal_sala (
    sal_id INTEGER PRIMARY KEY,
    sal_descricao VARCHAR(50),
    sal_capacidade INTEGER
);


-- =====================================================================
-- BLOCO 2: INCLUSÃO DE DADOS DE TESTE (ORDEM ALFABÉTICA)
-- =====================================================================

INSERT INTO alo_alocacao (alo_id, pro_id, dis_id) VALUES
(1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 4, 5), (6, 5, 6), (7, 5, 7),
(8, 6, 8), (9, 6, 9), (10, 7, 10), (11, 8, 11), (12, 8, 12), (13, 9, 13),
(14, 10, 14), (15, 10, 15), (16, 10, 16), (17, 10, 17), (18, 10, 18),
(19, 11, 19), (20, 11, 20), (21, 12, 21), (22, 13, 22), (23, 13, 23),
(24, 14, 24), (25, 14, 25), (26, 15, 26), (27, 16, 27), (28, 16, 28),
(29, 16, 29), (30, 17, 30), (31, 17, 31), (32, 18, 32), (33, 18, 33),
(34, 19, 34), (35, 19, 35), (36, 20, 36), (37, 20, 37), (38, 21, 38),
(39, 21, 39), (40, 22, 40), (41, 23, 41), (42, 24, 42), (43, 24, 43),
(44, 25, 44), (45, 25, 45), (46, 25, 46), (47, 26, 47);

INSERT INTO cur_curso (cur_id, cur_descricao) VALUES (1, 'Engenharia da Computação');

INSERT INTO dis_disciplina (dis_id, dis_codigo, dis_descricao, dis_periodo, dis_carga_horaria, dis_eh_eletiva, cur_id) VALUES
(1, 'CCMP0078', 'MINERAÇÃO DE DADOS', 9, 60, 1, 1),
(2, 'CCMP0123', 'APRENDIZAGEM DE MÁQUINA', 7, 60, 0, 1),
(3, 'CCMP0076', 'SISTEMAS DE COMUNICAÇÃO', 6, 60, 0, 1),
(4, 'CCMP0110', 'ALGORITMOS E ESTRUTURAS DE DADOS', 4, 60, 0, 1),
(5, 'CCMP0030', 'PROJETO DE FINAL DE CURSO', 8, 60, 0, 1),
(6, 'ELET0024', 'CONTROLE DE PROCESSOS', 8, 60, 0, 1),
(7, 'ELET0071', 'REDES DE COMPUTADORES 2', 8, 60, 0, 1),
(8, 'CCMP0125', 'ELEMENTOS DE ROBÓTICA', 8, 60, 0, 1),
(9, 'CCMP0071', 'SINAIS E SISTEMAS', 5, 60, 0, 1),
(10, 'ELET0070', 'REDES DE COMPUTADORES 1', 7, 60, 0, 1),
(11, 'CCMP0122', 'PESQUISA OPERACIONAL', 7, 60, 0, 1),
(12, 'CCMP0039', 'TEORIA DA COMPUTAÇÃO', 5, 60, 0, 1),
(13, 'CCMP0082', 'COMPUTAÇÃO NATURAL', 9, 60, 1, 1),
(14, 'CCMP0126', 'GESTÃO DE TIC E EMPREENDEDORISMO', 9, 60, 0, 1),
(15, 'CCMP0173', 'PROJETO EM ENGENHARIA DA COMPUTAÇÃO', 8, 60, 0, 1),
(16, 'CCMP0085', 'INFORMÁTICA, ECONOMIA E SOCIEDADE', 4, 60, 0, 1),
(17, 'ADMT0002', 'FORMAÇÃO DE EMPREENDEDORES', 10, 60, 1, 1),
(18, 'CCMP0116', 'TEORIA DOS GRAFOS', 5, 60, 0, 1),
(19, 'CCMP0084', 'DCEXT PROGRAMAÇÃO IMPERATIVA', 2, 60, 0, 1),
(20, 'CCMP0172', 'SISTEMAS MULTIMÍDIA', 5, 60, 0, 1),
(21, 'CCMP0074', 'ANÁLISE E PROJETO DE SOFTWARE', 6, 60, 0, 1),
(22, 'CCMP0015', 'INTELIGÊNCIA ARTIFICIAL', 6, 60, 0, 1),
(23, 'LETR0009', 'METODOLOGIA CIENTÍFICA', 5, 30, 0, 1),
(24, 'CCMP0124', 'DCEXT-SISTEMAS EMBARCADOS', 8, 60, 0, 1),
(25, 'CCMP0025', 'ORGANIZAÇÃO DE COMPUTADORES', 6, 60, 0, 1),
(26, 'ELET0025', 'CONVERSÃO ELETROMECÂNICA DE ENERGIA', 10, 60, 1, 1),
(27, 'CCMP0068', 'LINGUAGEM DE PROGRAMAÇÃO ORIENTADA A OBJETOS', 3, 60, 0, 1),
(28, 'CCMP0104', 'FUNDAMENTOS DE PROGRAMAÇÃO', 1, 60, 0, 1),
(29, 'CCMP0026', 'PROCESSAMENTO DIGITAL DE IMAGEM', 10, 60, 1, 1),
(30, 'CCMP0012', 'GERÊNCIA DE PROJETO', 9, 60, 1, 1),
(31, 'ENGE0002', 'INTRODUÇÃO À ENGENHARIA', 1, 30, 0, 1),
(32, 'CCMP0111', 'MATEMÁTICA DISCRETA', 4, 60, 0, 1),
(33, 'CCMP0006', 'COMPILADORES', 6, 60, 0, 1),
(34, 'CCMP0005', 'BANCO DE DADOS', 7, 60, 0, 1),
(35, 'CCMP0132', 'ENGENHARIA DE REQUISITOS', 10, 60, 1, 1),
(36, 'CCMP0081', 'MODELAGEM ANALÍTICA', 10, 60, 1, 1),
(37, 'CCMP0032', 'REDES NEURAIS', 10, 60, 1, 1),
(38, 'CCMP0073', 'ELETRÔNICA PARA COMPUTAÇÃO', 5, 60, 0, 1),
(39, 'CCMP0127', 'DCEXT-AUTOMAÇÃO INDUSTRIAL', 9, 60, 0, 1),
(40, 'CCMP0067', 'LÓGICA', 3, 60, 0, 1),
(41, 'CCMP0090', 'CIRCUITOS ELÉTRICOS', 4, 60, 0, 1),
(42, 'CCMP0003', 'ARQUITETURA DE COMPUTADORES', 7, 60, 0, 1),
(43, 'CCMP0119', 'ELETRÔNICA DIGITAL', 6, 60, 0, 1),
(44, 'CCMP0023', 'MÉTODOS FORMAIS', 9, 60, 1, 1),
(45, 'ELET0079', 'SISTEMAS OPERACIONAIS', 7, 60, 0, 1),
(46, 'CCMP0079', 'INTERFACE HUMANO-COMPUTADOR', 8, 60, 0, 1),
(47, 'CCMP0010', 'ENGENHARIA DE SOFTWARE', 5, 60, 0, 1);

INSERT INTO gra_grade_horaria (gra_semestre, alo_id, hor_id, sal_id) VALUES
('2026.1', 1, 39, 1), ('2026.1', 1, 40, 1), ('2026.1', 1, 41, 1), ('2026.1', 1, 42, 1),
('2026.1', 2, 15, 1), ('2026.1', 2, 16, 1), ('2026.1', 2, 17, 1), ('2026.1', 2, 18, 1),
('2026.1', 3, 51, 1), ('2026.1', 3, 52, 1), ('2026.1', 3, 53, 1), ('2026.1', 3, 54, 1),
('2026.1', 4, 37, 1), ('2026.1', 4, 38, 1), ('2026.1', 4, 39, 1), ('2026.1', 4, 40, 1),
('2026.1', 5, 43, 1), ('2026.1', 5, 44, 1), ('2026.1', 5, 45, 1), ('2026.1', 5, 46, 1),
('2026.1', 6, 3, 1), ('2026.1', 6, 4, 1), ('2026.1', 6, 5, 1), ('2026.1', 6, 6, 1),
('2026.1', 7, 51, 1), ('2026.1', 7, 52, 1), ('2026.1', 7, 53, 1), ('2026.1', 7, 54, 1),
('2026.1', 8, 25, 1), ('2026.1', 8, 26, 1), ('2026.1', 8, 39, 1), ('2026.1', 8, 40, 1),
('2026.1', 9, 41, 1), ('2026.1', 9, 42, 1), ('2026.1', 9, 51, 1), ('2026.1', 9, 52, 1),
('2026.1', 10, 27, 1), ('2026.1', 10, 28, 1), ('2026.1', 10, 29, 1), ('2026.1', 10, 30, 1),
('2026.1', 11, 25, 1), ('2026.1', 11, 26, 1), ('2026.1', 11, 49, 1), ('2026.1', 11, 50, 1),
('2026.1', 12, 37, 1), ('2026.1', 12, 38, 1), ('2026.1', 12, 39, 1), ('2026.1', 12, 40, 1),
('2026.1', 13, 3, 1), ('2026.1', 13, 4, 1), ('2026.1', 13, 5, 1), ('2026.1', 13, 6, 1),
('2026.1', 14, 25, 1), ('2026.1', 14, 26, 1),
('2026.1', 15, 27, 1), ('2026.1', 15, 28, 1),
('2026.1', 16, 29, 1), ('2026.1', 16, 30, 1),
('2026.1', 17, 33, 1), ('2026.1', 17, 34, 1), ('2026.1', 17, 35, 1), ('2026.1', 17, 36, 1),
('2026.1', 18, 41, 1), ('2026.1', 18, 42, 1),
('2026.1', 19, 39, 1), ('2026.1', 19, 40, 1), ('2026.1', 19, 41, 1), ('2026.1', 19, 42, 1),
('2026.1', 20, 16, 1), ('2026.1', 20, 17, 1), ('2026.1', 20, 18, 1), ('2026.1', 20, 19, 1),
('2026.1', 21, 1, 1), ('2026.1', 21, 2, 1), ('2026.1', 21, 3, 1), ('2026.1', 21, 4, 1),
('2026.1', 22, 13, 1), ('2026.1', 22, 14, 1), ('2026.1', 22, 15, 1), ('2026.1', 22, 16, 1),
('2026.1', 23, 5, 1), ('2026.1', 23, 6, 1),
('2026.1', 24, 1, 1), ('2026.1', 24, 2, 1), ('2026.1', 24, 25, 1), ('2026.1', 24, 26, 1),
('2026.1', 25, 5, 1), ('2026.1', 25, 6, 1), ('2026.1', 25, 29, 1), ('2026.1', 25, 30, 1),
('2026.1', 26, 13, 1), ('2026.1', 26, 14, 1), ('2026.1', 26, 37, 1), ('2026.1', 26, 38, 1),
('2026.1', 27, 3, 1), ('2026.1', 27, 4, 1), ('2026.1', 27, 27, 1), ('2026.1', 27, 28, 1),
('2026.1', 28, 5, 1), ('2026.1', 28, 6, 1), ('2026.1', 28, 29, 1), ('2026.1', 28, 30, 1),
('2026.1', 29, 31, 1), ('2026.1', 29, 32, 1), ('2026.1', 29, 33, 1), ('2026.1', 29, 34, 1),
('2026.1', 30, 53, 1), ('2026.1', 30, 54, 1), ('2026.1', 30, 55, 1), ('2026.1', 30, 56, 1),
('2026.1', 31, 21, 1), ('2026.1', 31, 22, 1),
('2026.1', 32, 15, 1), ('2026.1', 32, 16, 1), ('2026.1', 32, 51, 1), ('2026.1', 32, 52, 1),
('2026.1', 33, 17, 1), ('2026.1', 33, 18, 1), ('2026.1', 33, 41, 1), ('2026.1', 33, 42, 1),
('2026.1', 34, 3, 1), ('2026.1', 34, 4, 1), ('2026.1', 34, 39, 1), ('2026.1', 34, 40, 1),
('2026.1', 35, 5, 1), ('2026.1', 35, 6, 1), ('2026.1', 35, 41, 1), ('2026.1', 35, 42, 1),
('2026.1', 36, 25, 1), ('2026.1', 36, 26, 1), ('2026.1', 36, 39, 1), ('2026.1', 36, 40, 1),
('2026.1', 37, 27, 1), ('2026.1', 37, 28, 1), ('2026.1', 37, 37, 1), ('2026.1', 37, 38, 1),
('2026.1', 38, 3, 1), ('2026.1', 38, 4, 1), ('2026.1', 38, 27, 1), ('2026.1', 38, 28, 1),
('2026.1', 39, 15, 1), ('2026.1', 39, 16, 1), ('2026.1', 39, 17, 1), ('2026.1', 39, 18, 1),
('2026.1', 40, 15, 1), ('2026.1', 40, 16, 1), ('2026.1', 40, 17, 1), ('2026.1', 40, 18, 1),
('2026.1', 41, 25, 1), ('2026.1', 41, 26, 1), ('2026.1', 41, 27, 1), ('2026.1', 41, 28, 1),
('2026.1', 42, 13, 1), ('2026.1', 42, 14, 1), ('2026.1', 42, 51, 1), ('2026.1', 42, 52, 1),
('2026.1', 43, 25, 1), ('2026.1', 43, 26, 1), ('2026.1', 43, 27, 1), ('2026.1', 43, 28, 1),
('2026.1', 44, 1, 1), ('2026.1', 44, 2, 1), ('2026.1', 44, 3, 1), ('2026.1', 44, 4, 1),
('2026.1', 45, 5, 1), ('2026.1', 45, 6, 1), ('2026.1', 45, 25, 1), ('2026.1', 45, 26, 1),
('2026.1', 46, 39, 1), ('2026.1', 46, 40, 1), ('2026.1', 46, 41, 1), ('2026.1', 46, 42, 1),
('2026.1', 47, 13, 1), ('2026.1', 47, 14, 1), ('2026.1', 47, 15, 1), ('2026.1', 47, 16, 1);

INSERT INTO hor_horario (hor_id, hor_codigo_slot, hor_dia_semana, hor_bloco, hor_hora_inicio, hor_hora_fim) VALUES
(1, '2A', 'Segunda', 'A', '07:10', '08:00'), (2, '2B', 'Segunda', 'B', '08:00', '08:50'),
(3, '2C', 'Segunda', 'C', '08:50', '09:40'), (4, '2D', 'Segunda', 'D', '09:40', '10:30'),
(5, '2E', 'Segunda', 'E', '10:30', '11:20'), (6, '2F', 'Segunda', 'F', '11:20', '12:10'),
(7, '2G', 'Segunda', 'G', '12:10', '13:00'), (8, '2H', 'Segunda', 'H', '13:00', '13:50'),
(9, '2I', 'Segunda', 'I', '13:50', '14:40'), (10, '2J', 'Segunda', 'J', '14:40', '15:30'),
(11, '2K', 'Segunda', 'K', '15:30', '16:20'), (12, '2L', 'Segunda', 'L', '16:20', '17:10'),
(13, '3A', 'Terça', 'A', '07:10', '08:00'), (14, '3B', 'Terça', 'B', '08:00', '08:50'),
(15, '3C', 'Terça', 'C', '08:50', '09:40'), (16, '3D', 'Terça', 'D', '09:40', '10:30'),
(17, '3E', 'Terça', 'E', '10:30', '11:20'), (18, '3F', 'Terça', 'F', '11:20', '12:10'),
(19, '3G', 'Terça', 'G', '12:10', '13:00'), (20, '3H', 'Terça', 'H', '13:00', '13:50'),
(21, '3I', 'Terça', 'I', '13:50', '14:40'), (22, '3J', 'Terça', 'J', '14:40', '15:30'),
(23, '3K', 'Terça', 'K', '15:30', '16:20'), (24, '3L', 'Terça', 'L', '16:20', '17:10'),
(25, '4A', 'Quarta', 'A', '07:10', '08:00'), (26, '4B', 'Quarta', 'B', '08:00', '08:50'),
(27, '4C', 'Quarta', 'C', '08:50', '09:40'), (28, '4D', 'Quarta', 'D', '09:40', '10:30'),
(29, '4E', 'Quarta', 'E', '10:30', '11:20'), (30, '4F', 'Quarta', 'F', '11:20', '12:10'),
(31, '4G', 'Quarta', 'G', '12:10', '13:00'), (32, '4H', 'Quarta', 'H', '13:00', '13:50'),
(33, '4I', 'Quarta', 'I', '13:50', '14:40'), (34, '4J', 'Quarta', 'J', '14:40', '15:30'),
(35, '4K', 'Quarta', 'K', '15:30', '16:20'), (36, '4L', 'Quarta', 'L', '16:20', '17:10'),
(37, '5A', 'Quinta', 'A', '07:10', '08:00'), (38, '5B', 'Quinta', 'B', '08:00', '08:50'),
(39, '5C', 'Quinta', 'C', '08:50', '09:40'), (40, '5D', 'Quinta', 'D', '09:40', '10:30'),
(41, '5E', 'Quinta', 'E', '10:30', '11:20'), (42, '5F', 'Quinta', 'F', '11:20', '12:10'),
(43, '5G', 'Quinta', 'G', '12:10', '13:00'), (44, '5H', 'Quinta', 'H', '13:00', '13:50'),
(45, '5I', 'Quinta', 'I', '13:50', '14:40'), (46, '5J', 'Quinta', 'J', '14:40', '15:30'),
(47, '5K', 'Quinta', 'K', '15:30', '16:20'), (48, '5L', 'Quinta', 'L', '16:20', '17:10'),
(49, '6A', 'Sexta', 'A', '07:10', '08:00'), (50, '6B', 'Sexta', 'B', '08:00', '08:50'),
(51, '6C', 'Sexta', 'C', '08:50', '09:40'), (52, '6D', 'Sexta', 'D', '09:40', '10:30'),
(53, '6E', 'Sexta', 'E', '10:30', '11:20'), (54, '6F', 'Sexta', 'F', '11:20', '12:10'),
(55, '6G', 'Sexta', 'G', '12:10', '13:00'), (56, '6H', 'Sexta', 'H', '13:00', '13:50'),
(57, '6I', 'Sexta', 'I', '13:50', '14:40'), (58, '6J', 'Sexta', 'J', '14:40', '15:30'),
(59, '6K', 'Sexta', 'K', '15:30', '16:20'), (60, '6L', 'Sexta', 'L', '16:20', '17:10');

INSERT INTO pro_professor (pro_id, pro_nome, pro_matricula, cur_id) VALUES
(1, 'ALEXANDRE MAGNO ANDRADE MACIEL', 'PROF001', 1),
(2, 'BYRON LEITE DANTAS BEZERRA', 'PROF002', 1),
(3, 'CARMELO JOSE ALBANEZ BASTOS FILHO', 'PROF003', 1),
(4, 'CLEYTON MARIO DE OLIVEIRA RODRIGUES', 'PROF004', 1),
(5, 'DANIEL AUGUSTO RIBEIRO CHAVES', 'PROF005', 1),
(6, 'DIEGO JOSÉ RÁTIVA MILLÁN', 'PROF006', 1),
(7, 'EDISON DE QUEIROZ ALBUQUERQUE', 'PROF007', 1),
(8, 'ELIANE LOYOLA', 'PROF008', 1),
(9, 'FERNANDO BUARQUE DE LIMA NETO', 'PROF009', 1),
(10, 'GENÉSIO GOMES DA CRUZ NETO', 'PROF010', 1),
(11, 'HEMIR DA CUNHA SANTIAGO', 'PROF011', 1),
(12, 'JOABE BEZERRA DE JESUS JUNIOR', 'PROF012', 1),
(13, 'JOAO FAUSTO LORENZATO DE OLIVEIRA', 'PROF013', 1),
(14, 'JOSE PAULO GONÇALVES DE OLIVEIRA', 'PROF014', 1),
(15, 'JOSE RAIMUNDO LIMA JUNIOR', 'PROF015', 1),
(16, 'LEANDRO HONORATO DE SOUZA SILVA', 'PROF016', 1),
(17, 'LILIANE SHEYLA DA SILVA FONSECA', 'PROF017', 1),
(18, 'LUIS CARLOS DE SOUSA MENEZES', 'PROF018', 1),
(19, 'MARIA LENCASTRE PINHEIRO DE MENEZES E CRUZ', 'PROF019', 1),
(20, 'MEUSER JORGE SILVA VALENCA', 'PROF020', 1),
(21, 'RICARDO ATAIDE DE LIMA', 'PROF021', 1),
(22, 'ROBERTA ANDRADE DE ARAÚJO FAGUNDES', 'PROF022', 1),
(23, 'SERGIO CAMPELLO OLIVEIRA', 'PROF023', 1),
(24, 'SERGIO MURILO MACIEL FERNANDES', 'PROF024', 1),
(25, 'TARCIANA DIAS DA SILVA', 'PROF025', 1),
(26, 'WYLLIAMS BARBOSA SANTOS', 'PROF026', 1);

INSERT INTO sal_sala (sal_id, sal_descricao, sal_capacidade) VALUES
(1, 'Sala I-01', 45), (2, 'Sala I-02', 45), (3, 'Sala I-03', 45), (4, 'Laboratório de Informática', 35);


-- =====================================================================
-- BLOCO 3: ATUALIZAÇÃO DOS OBJETOS COM AS CONSTRAINTS DE REFERÊNCIA
-- =====================================================================

-- Nota: O SQLite não suporta a instrução 'ALTER TABLE ... ADD CONSTRAINT'
-- nativamente. Para manter o script 100% funcional sem quebrar, as chaves
-- estrangeiras foram vinculadas na criação da tabela (Bloco 1) e agora 
-- ativamos a sua validação global:
PRAGMA foreign_keys = ON;

/*
-- Comandos equivalentes para bancos como PostgreSQL, MySQL ou SQL Server:
ALTER TABLE alo_alocacao ADD CONSTRAINT fk_alo_pro FOREIGN KEY (pro_id) REFERENCES pro_professor(pro_id);
ALTER TABLE alo_alocacao ADD CONSTRAINT fk_alo_dis FOREIGN KEY (dis_id) REFERENCES dis_disciplina(dis_id);
ALTER TABLE dis_disciplina ADD CONSTRAINT fk_dis_cur FOREIGN KEY (cur_id) REFERENCES cur_curso(cur_id);
ALTER TABLE gra_grade_horaria ADD CONSTRAINT fk_gra_alo FOREIGN KEY (alo_id) REFERENCES alo_alocacao(alo_id);
ALTER TABLE gra_grade_horaria ADD CONSTRAINT fk_gra_hor FOREIGN KEY (hor_id) REFERENCES hor_horario(hor_id);
ALTER TABLE gra_grade_horaria ADD CONSTRAINT fk_gra_sal FOREIGN KEY (sal_id) REFERENCES sal_sala(sal_id);
ALTER TABLE pro_professor ADD CONSTRAINT fk_pro_cur FOREIGN KEY (cur_id) REFERENCES cur_curso(cur_id);
*/
"""

cursor.executescript(sql_script)
conn.commit()
conn.close()

print("Banco 'grade_horaria.db' criado e populado com sucesso em 3 blocos!")