# Arquitetura do Projeto

## Visão Geral

O `backup-codex` é um projeto pequeno, focado em uma única responsabilidade: capturar o estado local do Codex de forma restaurável.

Ele está dividido em três partes principais:

- CLI: recebe comandos e argumentos do usuário
- Core: implementa backup, verificação e restauração
- Modelos: definem o formato do manifesto

## Módulos

### `codex_backup/cli.py`

Responsável por:

- declarar os comandos `inspect`, `backup`, `verify` e `restore`
- traduzir argumentos em chamadas para o core
- exibir saída humana ou JSON

### `codex_backup/core.py`

Responsável por:

- localizar o diretório do Codex
- montar o inventário do backup
- copiar arquivos comuns
- gerar snapshot consistente de bancos SQLite
- construir e ler o `manifest.json`
- verificar a integridade do backup
- restaurar com merge ou substituição do destino

### `codex_backup/models.py`

Responsável por:

- representar entradas individuais do backup
- representar o manifesto completo
- serializar e desserializar os metadados

## Fluxo de Backup

1. Resolver o diretório do Codex.
2. Coletar os arquivos elegíveis conforme o modo (`portable` ou `mirror`).
3. Copiar arquivos normais e gerar snapshot para SQLite.
4. Calcular hash SHA-256 dos arquivos no payload.
5. Gerar `manifest.json`.

## Fluxo de Verificação

1. Abrir o backup em diretório ou `.zip`.
2. Ler o `manifest.json`.
3. Validar o resumo do manifesto.
4. Confirmar existência, tamanho e SHA-256 de cada item do payload.

## Fluxo de Restauração

1. Abrir o backup.
2. Verificar a integridade completa antes de tocar no destino.
3. Resolver o diretório de restauração.
4. Escolher entre:
   - merge com `--force`
   - substituição completa com `--replace-destination`
5. Restaurar os arquivos.
6. Limpar sidecars de SQLite restaurados.

## Decisões de Segurança

- `restore` verifica a integridade antes de gravar no destino.
- `--replace-destination` recusa caminhos claramente perigosos, como raiz do disco ou diretório home.
- sidecars `-wal` e `-shm` não são usados como fonte de verdade; o snapshot do `.sqlite` é o artefato restaurável.

## Pontos Naturais de Extensão

- criptografia do backup logo após `materialize_backup`
- formatos alternativos de saída além de `.zip`
- relatórios de verificação mais detalhados
- política de retenção e rotação de backups
- compatibilidade com novos layouts internos do Codex

