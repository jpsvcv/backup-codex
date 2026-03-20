# backup-codex

Ferramenta em Python para fazer o backup integral do estado local do Codex e restaurá-lo em outra máquina, ou na mesma máquina em caso de falha, migração ou reinstalação.

O projeto foi desenhado a partir da estrutura real observada em `~/.codex` no Windows, incluindo sessões (`sessions/`), estado local em SQLite (`state_*.sqlite`, `logs_*.sqlite`, `sqlite/`), configuração (`config.toml`), autenticação (`auth.json`, `cap_sid`), regras, skills e demais arquivos de suporte.

## Objetivo

Preservar, empacotar e restaurar tudo o que é necessário para reconstituir a experiência local de uso do Codex com o mínimo de perda possível.

## Requisitos Iniciais

Os requisitos iniciais detalhados estão em [docs/requirements.md](docs/requirements.md).

## Documentação

Documentos principais do projeto:

- `README.md`: visão geral, instalação e fluxo rápido
- `docs/usage.md`: uso detalhado da ferramenta
- `docs/architecture.md`: visão de arquitetura e pontos de extensão
- `CONTRIBUTING.md`: como evoluir o projeto com segurança
- `LICENSE`: licença de uso e redistribuição

Resumo:

- Detectar automaticamente o diretório do Codex, com suporte a sobrescrita via argumento.
- Fazer backup de sessões, bancos SQLite, configuração, skills, regras e credenciais.
- Gerar backup em diretório ou arquivo `.zip`.
- Criar manifesto com metadados, hashes e inventário dos arquivos.
- Restaurar o backup para outro diretório do Codex, com opção de sobrescrita.
- Tratar arquivos SQLite com snapshot consistente, evitando depender de `-wal` e `-shm`.
- Permitir um modo mais portátil e um modo espelho mais fiel ao ambiente original.

## Escopo Atual

O CLI implementado neste repositório oferece quatro comandos:

- `inspect`: mostra o inventário que seria incluído no backup.
- `backup`: cria um backup em diretório ou `.zip`.
- `verify`: valida a integridade do backup antes da restauração.
- `restore`: restaura um backup previamente criado.

Por padrão, o modo `portable` exclui artefatos transitórios de sandbox e diretórios temporários, mas mantém sessões, estado, configurações, regras, skills, bancos SQLite, logs e segredos. Para uma cópia ainda mais fiel do ambiente local, use `--mode mirror`.

## Requisitos Técnicos

- Python 3.11 ou superior
- Sem dependências externas para execução

## Instalação

Uso sem instalar no sistema:

```bash
python -m codex_backup --help
python -m codex_backup inspect
```

Para habilitar o comando curto `codex-backup`, instale o projeto em modo editável:

```bash
python -m pip install -e .
```

## Uso

O guia detalhado de utilização está em [docs/usage.md](docs/usage.md).

Fluxo rápido:

Inspecionar o que será incluído:

```bash
python -m codex_backup inspect
codex-backup inspect
```

Criar um backup em diretório:

```bash
python -m codex_backup backup .\backups\codex-2026-03-20
codex-backup backup .\backups\codex-2026-03-20
```

Criar um backup compactado:

```bash
python -m codex_backup backup .\backups\codex-2026-03-20.zip
codex-backup backup .\backups\codex-2026-03-20.zip
```

Criar um backup sem credenciais:

```bash
python -m codex_backup backup .\backups\codex-no-secrets.zip --without-secrets
codex-backup backup .\backups\codex-no-secrets.zip --without-secrets
```

Restaurar para o diretório padrão do Codex desta máquina:

```bash
python -m codex_backup verify .\backups\codex-2026-03-20.zip
python -m codex_backup restore .\backups\codex-2026-03-20.zip --force
codex-backup verify .\backups\codex-2026-03-20.zip
codex-backup restore .\backups\codex-2026-03-20.zip --force
```

Restaurar para outro diretório:

```bash
python -m codex_backup verify .\backups\codex-2026-03-20.zip
python -m codex_backup restore .\backups\codex-2026-03-20.zip C:\Users\outro\.codex --replace-destination
codex-backup verify .\backups\codex-2026-03-20.zip
codex-backup restore .\backups\codex-2026-03-20.zip C:\Users\outro\.codex --replace-destination
```

Ver ajuda da CLI:

```bash
python -m codex_backup --help
python -m codex_backup inspect --help
python -m codex_backup backup --help
python -m codex_backup verify --help
python -m codex_backup restore --help
```

Se `codex-backup` não for reconhecido no terminal, use `python -m codex_backup ...` ou execute novamente:

```bash
python -m pip install -e .
```

## Estrutura do Backup

Cada backup contém:

- `manifest.json`: metadados, resumo, hashes SHA-256 e lista de arquivos.
- `payload/`: árvore restaurável do backup.

## Observações de Segurança

- `auth.json` e `cap_sid` podem conter credenciais ativas. Use `--without-secrets` ao gerar um pacote sem autenticação.
- `verify` checa tamanho e hash SHA-256 de todos os arquivos do backup, e o `restore` executa essa verificação automaticamente antes de escrever no destino.
- `--force` sobrescreve apenas arquivos conflitantes; `--replace-destination` limpa a pasta destino antes de restaurar.
- Sem `--replace-destination`, a restauração sobrescreve apenas os arquivos presentes no backup e mantém arquivos extras já existentes no destino.
- Para restauração em produção, o ideal é fechar o Codex antes do processo.

## Desenvolvimento

Executar os testes:

```bash
python -m unittest discover -s tests -v
```

## Continuidade do Projeto

Para dar continuidade ao projeto, o ponto de entrada ideal é:

1. ler `docs/architecture.md`;
2. instalar com `python -m pip install -e .`;
3. executar os testes;
4. implementar a funcionalidade desejada no `core` e expor na `cli` se necessário;
5. atualizar a documentação e os testes.
