CREATE TABLE processos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    unidade_conservacao VARCHAR(255) NOT NULL,
    eixo_tematico VARCHAR(255) NOT NULL,
    numero_sei VARCHAR(50),
    no_sei BOOLEAN NOT NULL DEFAULT FALSE
);

-- Inserir alguns dados de exemplo
INSERT INTO processos (nome, unidade_conservacao, eixo_tematico, numero_sei, no_sei) VALUES
('Processo 1', 'Parque Nacional', 'Educação Ambiental', '123456', TRUE),
('Processo 2', 'Reserva Biológica', 'Gestão de Recursos', NULL, FALSE);
