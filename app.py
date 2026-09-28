import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

# As credenciais e configurações do serviço de e-mail são lidas do .env.
# O arquivo .env não deve ser publicado no GitHub.
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{BASE_DIR / 'instance' / 'app.db'}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configuração da Web API do SendGrid.
app.config["API_KEY"] = os.environ.get("API_KEY", "").strip()
app.config["API_URL"] = os.environ.get(
    "API_URL",
    "https://api.sendgrid.com/v3/mail/send",
).strip()
app.config["API_FROM"] = os.environ.get("API_FROM", "").strip()
app.config["FLASKY_MAIL_SUBJECT_PREFIX"] = "[Flasky]"
app.config["FLASKY_ADMIN"] = os.environ.get(
    "FLASKY_ADMIN",
    "flaskaulasweb@zohomail.com",
).strip()

# Dados da aluna exigidos no corpo do e-mail.
app.config["STUDENT_ID"] = "PT3038084"
app.config["STUDENT_NAME"] = "Taissa Pieri"
app.config["STUDENT_EMAIL"] = "p.taissa@aluno.ifsp.edu.br"

db = SQLAlchemy(app)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    users = db.relationship(
        "User",
        back_populates="role",
        order_by="User.id",
    )


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

    role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id"),
        nullable=False,
    )

    role = db.relationship("Role", back_populates="users")


ROLE_NAMES = (
    "Administrator",
    "Moderator",
    "User",
)


class EmailConfigurationError(RuntimeError):
    """Configuração necessária para o serviço de e-mail não foi informada."""


class EmailDeliveryError(RuntimeError):
    """O serviço de e-mail não aceitou o envio."""


def create_default_roles():
    """Cria as três funções da atividade caso ainda não existam."""
    created = False

    for role_name in ROLE_NAMES:
        role = db.session.scalar(
            select(Role).where(Role.name == role_name)
        )
        if role is None:
            db.session.add(Role(name=role_name))
            created = True

    if created:
        db.session.commit()


def get_roles():
    """Retorna as funções na mesma ordem apresentada na atividade."""
    roles = db.session.scalars(select(Role)).all()
    role_order = {
        role_name: position
        for position, role_name in enumerate(ROLE_NAMES)
    }

    return sorted(
        roles,
        key=lambda role: role_order.get(role.name, len(ROLE_NAMES)),
    )


def validate_email_configuration():
    """Confere as variáveis de ambiente necessárias para a API."""
    required = {
        "API_KEY": app.config["API_KEY"],
        "API_URL": app.config["API_URL"],
        "API_FROM": app.config["API_FROM"],
    }

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise EmailConfigurationError(
            "Configuração de e-mail incompleta: " + ", ".join(missing)
        )


def send_email(to, subject, template, **kwargs):
    """Envia e-mail usando a API HTTP do SendGrid."""
    validate_email_configuration()

    if isinstance(to, str):
        recipients = [to]
    else:
        recipients = list(to)

    # Remove itens vazios e evita endereço repetido.
    recipients = list(
        dict.fromkeys(
            email.strip()
            for email in recipients
            if email and email.strip()
        )
    )

    if not recipients:
        raise EmailConfigurationError(
            "Nenhum destinatário foi informado para o e-mail."
        )

    html_body = render_template(template + ".html", **kwargs)
    payload = {
        "personalizations": [
            {
                "to": [
                    {"email": recipient}
                    for recipient in recipients
                ]
            }
        ],
        "from": {
            "email": app.config["API_FROM"],
            "name": "Flask - Semana 11.A",
        },
        "subject": app.config["FLASKY_MAIL_SUBJECT_PREFIX"] + subject,
        "content": [
            {
                "type": "text/html",
                "value": html_body,
            }
        ],
    }

    try:
        response = requests.post(
            app.config["API_URL"],
            headers={
                "Authorization": f"Bearer {app.config['API_KEY']}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise EmailDeliveryError(
            "Não foi possível conectar ao serviço de e-mail."
        ) from exc

    # A Web API do SendGrid retorna HTTP 202 quando aceita o envio.
    if response.status_code != 202:
        app.logger.error(
            "SendGrid recusou o envio. Status=%s Body=%s",
            response.status_code,
            response.text,
        )
        raise EmailDeliveryError(
            f"O serviço de e-mail recusou o envio (HTTP {response.status_code})."
        )


@app.route("/", methods=["GET", "POST"])
def index():
    name = None
    message = None
    message_type = "info"

    if request.method == "POST":
        name = request.form.get("username", "").strip()
        role_id = request.form.get("role_id", type=int)

        # Semana 11.A: checkbox opcional para também enviar a mensagem
        # ao endereço flaskaulasweb@zohomail.com.
        send_to_admin = request.form.get("send_to_admin") == "on"

        role = db.session.get(Role, role_id) if role_id else None

        if not name:
            message = "Informe o nome do usuário."
            message_type = "danger"

        elif role is None:
            message = "Selecione uma função válida."
            message_type = "danger"

        else:
            existing = db.session.scalar(
                select(User).where(User.username == name)
            )

            if existing is not None:
                message = "Esse usuário já está cadastrado."
                message_type = "warning"

            else:
                user = User(
                    username=name,
                    role=role,
                )
                db.session.add(user)

                try:
                    # O e-mail institucional é sempre obrigatório.
                    recipients = [app.config["STUDENT_EMAIL"]]

                    # O endereço da atividade só é incluído quando o usuário
                    # marca a opção correspondente no formulário.
                    if send_to_admin:
                        recipients.append(app.config["FLASKY_ADMIN"])

                    send_email(
                        recipients,
                        " Novo usuário cadastrado - Semana 11.A",
                        "mail/new_user",
                        student_id=app.config["STUDENT_ID"],
                        student_name=app.config["STUDENT_NAME"],
                        user=user,
                        sent_to_admin=send_to_admin,
                    )

                    db.session.commit()

                    if send_to_admin:
                        message = (
                            "Usuário cadastrado com sucesso. E-mail enviado "
                            "ao endereço institucional e também para "
                            "flaskaulasweb@zohomail.com."
                        )
                    else:
                        message = (
                            "Usuário cadastrado com sucesso. E-mail enviado "
                            "ao endereço institucional."
                        )

                    message_type = "success"

                except (EmailConfigurationError, EmailDeliveryError) as exc:
                    db.session.rollback()
                    app.logger.error("Falha no cadastro/e-mail: %s", exc)
                    message = (
                        "O usuário não foi cadastrado porque o e-mail "
                        "obrigatório para o endereço institucional não pôde "
                        "ser enviado. Verifique API_URL, API_KEY e API_FROM."
                    )
                    message_type = "danger"

    users = db.session.scalars(
        select(User).order_by(User.id.asc())
    ).all()

    roles = get_roles()

    user_count = db.session.scalar(
        select(func.count()).select_from(User)
    )

    role_count = db.session.scalar(
        select(func.count()).select_from(Role)
    )

    return render_template(
        "index.html",
        name=name,
        users=users,
        roles=roles,
        user_count=user_count,
        role_count=role_count,
        message=message,
        message_type=message_type,
    )


with app.app_context():
    db.create_all()
    create_default_roles()


if __name__ == "__main__":
    app.run(debug=True)
