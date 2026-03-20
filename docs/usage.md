# Guia de Utilização

## Visão Geral

O `backup-codex` faz backup do diretório local do Codex e gera um pacote restaurável em pasta ou `.zip`.

Você pode usar a ferramenta de duas formas:

- sem instalar o comando no sistema, com `python -m codex_backup ...`
- com o comando curto `codex-backup ...`, após `python -m pip install -e .`

Os três comandos principais são:

- `inspect`: mostra o que seria incluído no backup.
- `backup`: cria o backup.
- `verify`: verifica a integridade do backup.
- `restore`: restaura um backup existente.

## Como a Ferramenta Descobre o Codex

Por padrão, a ferramenta procura o diretório do Codex nesta ordem:

1. valor da variável de ambiente `CODEX_HOME`;
2. diretório padrão `~/.codex`.

Se quiser apontar explicitamente para outro local, use `--codex-home`.

Exemplo:

```bash
python -m codex_backup inspect --codex-home C:\Users\jakso\.codex
codex-backup inspect --codex-home C:\Users\jakso\.codex
```

## Instalação e Execução

### Opção 1: usar sem instalar

Útil para desenvolvimento e testes rápidos no próprio repositório.

```bash
python -m codex_backup --help
python -m codex_backup inspect
```

### Opção 2: instalar o comando `codex-backup`

```bash
python -m pip install -e .
codex-backup --help
```

Se o comando `codex-backup` não for reconhecido, normalmente isso significa que o pacote ainda não foi instalado neste Python, ou que o terminal atual ainda não enxergou a instalação. Nesse caso:

```bash
python -m pip install -e .
python -m codex_backup --help
```

## Modos de Backup

### `portable`

É o modo padrão. Ele tenta gerar um backup mais portátil entre máquinas.

Normalmente exclui:

- `tmp/`
- `.sandbox/`
- `.sandbox-bin/`
- `.sandbox-secrets/`
- arquivos auxiliares de SQLite, como `*.sqlite-wal` e `*.sqlite-shm`

Mantém os arquivos principais, como:

- sessões em `sessions/`
- configuração, regras e skills
- bancos SQLite principais
- arquivos de estado e logs
- credenciais, a menos que `--without-secrets` seja usado

### `mirror`

Inclui praticamente todo o conteúdo do diretório do Codex, exceto os sidecars de SQLite.

Use esse modo quando a prioridade for fidelidade máxima ao ambiente original.

Exemplo:

```bash
codex-backup backup .\backups\codex-mirror.zip --mode mirror
```

## Comando `inspect`

Serve para revisar o inventário antes de criar o backup.

Uso básico:

```bash
python -m codex_backup inspect
codex-backup inspect
```

Opções principais:

- `--codex-home CAMINHO`: usa um diretório do Codex específico
- `--mode {portable,mirror}`: escolhe o modo de inventário
- `--without-secrets`: esconde arquivos sensíveis do inventário
- `--json`: retorna os dados em JSON

Exemplos:

```bash
python -m codex_backup inspect --without-secrets
python -m codex_backup inspect --mode mirror
python -m codex_backup inspect --json
codex-backup inspect --without-secrets
codex-backup inspect --mode mirror
codex-backup inspect --json
```

## Comando `backup`

Cria o backup restaurável.

Uso básico:

```bash
python -m codex_backup backup DESTINO
codex-backup backup DESTINO
```

Se `DESTINO` terminar com `.zip`, a saída será um arquivo compactado. Caso contrário, será criado um diretório.

Opções principais:

- `--codex-home CAMINHO`: usa um diretório do Codex específico
- `--mode {portable,mirror}`: define o modo do backup
- `--without-secrets`: não inclui `auth.json` nem `cap_sid`
- `--force`: sobrescreve o destino se ele já existir
- `--json`: retorna o resultado em JSON

Exemplos:

Criar backup em diretório:

```bash
python -m codex_backup backup .\backups\codex-2026-03-20
codex-backup backup .\backups\codex-2026-03-20
```

Criar backup em `.zip`:

```bash
python -m codex_backup backup .\backups\codex-2026-03-20.zip
codex-backup backup .\backups\codex-2026-03-20.zip
```

Criar backup sem credenciais:

```bash
python -m codex_backup backup .\backups\codex-no-secrets.zip --without-secrets
codex-backup backup .\backups\codex-no-secrets.zip --without-secrets
```

Sobrescrever um destino existente:

```bash
python -m codex_backup backup .\backups\codex-2026-03-20.zip --force
codex-backup backup .\backups\codex-2026-03-20.zip --force
```

## Comando `verify`

Valida a integridade do backup antes da restauração.

Ele confere:

- presença do `manifest.json`
- presença de todos os arquivos em `payload/`
- tamanho dos arquivos
- hash SHA-256 de cada item do backup

Uso básico:

```bash
python -m codex_backup verify ORIGEM
codex-backup verify ORIGEM
```

Exemplos:

```bash
python -m codex_backup verify .\backups\codex-2026-03-20.zip
python -m codex_backup verify .\backups\codex-2026-03-20 --json
codex-backup verify .\backups\codex-2026-03-20.zip
```

Observação:

- o comando `restore` já executa a verificação automaticamente antes de restaurar

## Comando `restore`

Restaura um backup criado anteriormente.

Uso básico:

```bash
python -m codex_backup restore ORIGEM
codex-backup restore ORIGEM
```

Se o diretório de destino não for informado, a ferramenta usa o diretório do Codex detectado localmente.

Opções principais:

- `--force`: sobrescreve arquivos existentes
- `--skip-secrets`: não restaura `auth.json` nem `cap_sid`
- `--replace-destination`: limpa todo o conteúdo da pasta de destino antes da restauração
- `--json`: retorna o resultado em JSON

Diferença entre `--force` e `--replace-destination`:

- `--force`: sobrescreve apenas arquivos que entram em conflito
- `--replace-destination`: apaga o conteúdo atual da pasta de destino e restaura o backup por cima

Exemplos:

Restaurar para o diretório local padrão:

```bash
python -m codex_backup restore .\backups\codex-2026-03-20.zip --force
codex-backup restore .\backups\codex-2026-03-20.zip --force
```

Restaurar para outro diretório:

```bash
python -m codex_backup restore .\backups\codex-2026-03-20.zip C:\Users\outro\.codex --force
codex-backup restore .\backups\codex-2026-03-20.zip C:\Users\outro\.codex --force
```

Restaurar sem credenciais:

```bash
python -m codex_backup restore .\backups\codex-2026-03-20.zip C:\Users\outro\.codex --force --skip-secrets
codex-backup restore .\backups\codex-2026-03-20.zip C:\Users\outro\.codex --force --skip-secrets
```

Restaurar substituindo todo o conteúdo da pasta de destino:

```bash
python -m codex_backup restore .\backups\codex-2026-03-20.zip C:\Users\outro\.codex --replace-destination
codex-backup restore .\backups\codex-2026-03-20.zip C:\Users\outro\.codex --replace-destination
```

## Fluxos Recomendados

### 1. Backup para migrar de máquina

```bash
python -m codex_backup inspect --without-secrets
python -m codex_backup backup .\backups\codex-migracao.zip
python -m codex_backup verify .\backups\codex-migracao.zip
codex-backup inspect --without-secrets
codex-backup backup .\backups\codex-migracao.zip
codex-backup verify .\backups\codex-migracao.zip
```

Copie o `.zip` para a nova máquina e restaure:

```bash
python -m codex_backup restore .\backups\codex-migracao.zip --replace-destination
codex-backup restore .\backups\codex-migracao.zip --replace-destination
```

### 2. Backup sem credenciais

Indicado quando o pacote será armazenado em local compartilhado ou enviado para outra pessoa.

```bash
python -m codex_backup backup .\backups\codex-shareable.zip --without-secrets
python -m codex_backup verify .\backups\codex-shareable.zip
python -m codex_backup restore .\backups\codex-shareable.zip --force --skip-secrets
codex-backup backup .\backups\codex-shareable.zip --without-secrets
codex-backup verify .\backups\codex-shareable.zip
codex-backup restore .\backups\codex-shareable.zip --force --skip-secrets
```

### 3. Validação antes de sobrescrever

Primeiro veja o que existe:

```bash
python -m codex_backup inspect
codex-backup inspect
```

Depois gere o backup:

```bash
python -m codex_backup backup .\backups\codex-latest.zip
codex-backup backup .\backups\codex-latest.zip
```

E só então restaure com `--force` no destino desejado.

### 4. Restaurar no próprio computador

Exemplo prático:

1. gerar o backup da instalação atual do Codex;
2. validar a integridade do pacote;
3. restaurar por cima da pasta local do Codex.

```bash
python -m codex_backup backup .\backups\codex-local.zip --codex-home C:\Users\jakso\.codex
python -m codex_backup verify .\backups\codex-local.zip
python -m codex_backup restore .\backups\codex-local.zip C:\Users\jakso\.codex --replace-destination
```

Versão com comando instalado:

```bash
codex-backup backup .\backups\codex-local.zip --codex-home C:\Users\jakso\.codex
codex-backup verify .\backups\codex-local.zip
codex-backup restore .\backups\codex-local.zip C:\Users\jakso\.codex --replace-destination
```

### 5. Restaurar em outra máquina

Na máquina de origem:

```bash
python -m codex_backup backup .\backups\codex-migracao.zip --codex-home C:\Users\jakso\.codex
python -m codex_backup verify .\backups\codex-migracao.zip
```

Copie o arquivo `.zip` para a máquina de destino.

Na máquina de destino:

```bash
python -m codex_backup verify .\backups\codex-migracao.zip
python -m codex_backup restore .\backups\codex-migracao.zip C:\Users\outro\.codex --replace-destination
```

Se quiser evitar levar autenticação entre máquinas, crie o backup com `--without-secrets` e restaure com `--skip-secrets`.

## Estrutura do Backup Gerado

O backup contém:

- `manifest.json`: metadados, resumo e inventário com hash dos arquivos
- `payload/`: conteúdo restaurável do diretório do Codex

Exemplo simplificado:

```text
backup.zip
manifest.json
payload/
  config.toml
  history.jsonl
  sessions/
  skills/
  state_5.sqlite
```

## Saída JSON

Os comandos `inspect`, `backup` e `restore` aceitam `--json`.

Isso é útil para automação, scripts e integração com outras ferramentas.

Exemplo:

```bash
python -m codex_backup backup .\backups\codex.zip --json
codex-backup backup .\backups\codex.zip --json
```

## Boas Práticas

- Feche o Codex antes de restaurar um backup em uso.
- Use `--without-secrets` quando não quiser transportar autenticação.
- Use `portable` como padrão para migração entre máquinas.
- Use `mirror` quando quiser uma réplica mais fiel do ambiente local.
- Guarde pelo menos um backup `.zip` fora da máquina principal.

## Limitações Atuais

- Sem `--replace-destination`, a restauração faz merge com sobrescrita opcional e não remove arquivos extras já existentes no destino.
- O projeto ainda não oferece criptografia nativa do pacote de backup.
- Ainda não existe reparo automático para backups corrompidos; a ferramenta apenas detecta e interrompe a restauração.

## Ajuda da CLI

```bash
python -m codex_backup --help
python -m codex_backup inspect --help
python -m codex_backup backup --help
python -m codex_backup verify --help
python -m codex_backup restore --help
```

## Troubleshooting

### `codex-backup` não é reconhecido

Causa mais comum:

- o projeto ainda não foi instalado com `python -m pip install -e .`

Solução imediata:

```bash
python -m codex_backup inspect
```

Para habilitar o comando curto:

```bash
python -m pip install -e .
codex-backup --help
```
