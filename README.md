# Semana 11.A — E-mail opcional com Flask no PythonAnywhere

Aplicação desenvolvida como continuação direta da **Semana 10**, utilizando Flask, Flask-SQLAlchemy, SQLite e a Web API do SendGrid.

## O que mudou na Semana 11.A

Na Semana 10, todo novo cadastro enviava o mesmo e-mail para o endereço da atividade e para o e-mail institucional.

Na Semana 11.A:

- o e-mail institucional `p.taissa@aluno.ifsp.edu.br` recebe a mensagem **sempre**;
- o formulário possui um **checkbox** para optar pelo envio também para `flaskaulasweb@zohomail.com`;
- se o checkbox não for marcado, o endereço da atividade não é incluído entre os destinatários;
- se o checkbox for marcado, os dois endereços recebem a mensagem.

## Funcionalidades mantidas

- Associação do usuário a `Administrator`, `Moderator` ou `User`.
- Persistência em banco SQLite.
- Listagem de usuários e respectivas funções.
- Listagem de usuários agrupados por função.
- Contador de usuários.
- Contador de funções.
- Envio de e-mail pela Web API do SendGrid.

## Corpo do e-mail

A mensagem contém:

- Prontuário: `PT3038084`;
- Nome do aluno: `Taissa Pieri`;
- usuário cadastrado;
- função escolhida.

## Regra de destinatários

A lógica principal está em `app.py`:

```python
recipients = [app.config["STUDENT_EMAIL"]]

if send_to_admin:
    recipients.append(app.config["FLASKY_ADMIN"])
```

O valor de `send_to_admin` vem do checkbox do formulário:

```python
send_to_admin = request.form.get("send_to_admin") == "on"
```

## SendGrid e variáveis de ambiente

A aplicação usa:

```text
API_URL
API_KEY
API_FROM
FLASKY_ADMIN
```

O arquivo `.env` real não deve ser enviado ao GitHub.

Como a Semana 10 já está configurada no mesmo PythonAnywhere, é possível copiar o `.env` já existente:

```bash
cp ~/Semana-10---PythonAnywhere/.env ~/Semana-11-PythonAnywhere/.env
```

Ou criar um novo `.env` com:

```text
FLASKY_ADMIN=flaskaulasweb@zohomail.com
API_URL=https://api.sendgrid.com/v3/mail/send
API_KEY=SUA_CHAVE_DA_API_SENDGRID
API_FROM=SEU_REMETENTE_VERIFICADO_NO_SENDGRID
```

## Publicação no PythonAnywhere

### 1. Clonar o repositório

```bash
cd ~
git clone https://github.com/ptaissa-ai/Semana-11-PythonAnywhere.git
cd Semana-11-PythonAnywhere
```

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv ~/.virtualenvs/semana11
source ~/.virtualenvs/semana11/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar o `.env`

Se quiser reaproveitar as mesmas credenciais do SendGrid já utilizadas na Semana 10:

```bash
cp ~/Semana-10---PythonAnywhere/.env ~/Semana-11-PythonAnywhere/.env
```

### 5. Testar o carregamento

```bash
python -c "from app import app; print('APLICACAO SEMANA 11.A OK')"
```

### 6. Aba Web do PythonAnywhere

Use:

```text
Source code:       /home/taissapieri/Semana-11-PythonAnywhere
Working directory: /home/taissapieri/Semana-11-PythonAnywhere
Virtualenv:         /home/taissapieri/.virtualenvs/semana11
```

No WSGI real (`/var/www/taissapieri_pythonanywhere_com_wsgi.py`):

```python
import sys

project_home = "/home/taissapieri/Semana-11-PythonAnywhere"

if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application
```

Depois clique em **Reload**.

## Teste final da atividade

Faça dois cadastros com nomes diferentes:

1. **checkbox desmarcado:** a mensagem deve chegar apenas ao e-mail institucional;
2. **checkbox marcado:** a mensagem deve chegar ao e-mail institucional e também a `flaskaulasweb@zohomail.com`.

Em ambos os casos, o usuário deve ser persistido no banco e aparecer nas listagens e contadores.

## Segurança

O `.gitignore` impede o envio de `.env`, banco SQLite, ambientes virtuais e caches para o GitHub.

**Nunca publique a API Key do SendGrid no GitHub.**
