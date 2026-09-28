import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "semana11-a-email-flask",
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{BASE_DIR / 'instance' / 'app.db'}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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

app.config["STUDENT_ID"] = os.environ.get(
    "STUDENT_ID",
    "PT3038084",
).strip()

app.config["STUDENT_NAME"] = os.environ.get(
    "STUDENT_NAME",
    "Taissa Pieri",
).strip()

app.config["STUDENT_EMAIL"] = os.environ.get(
    "STUDENT_EMAIL",
    "p.taissa@aluno.ifsp.edu.br",
).strip()

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

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
    )

    role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id"),
        nullable=False,
    )

    role = db.relationship(
        "Role",
        back_populates="users",
    )


ROLE_NAMES = (
    "Administrator",
    "Moderator",
    "User",
)


class EmailConfigurationError(RuntimeError):
    pass


class EmailDeliveryError(RuntimeError):
    pass


def create_default_roles():

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

    roles = db.session.scalars(
        select(Role)
    ).all()

    role_order = {
        role_name: position
        for position, role_name in enumerate(ROLE_NAMES)
    }

    return sorted(
        roles,
        key=lambda role: role_order.get(
            role.name,
            len(ROLE_NAMES),
        ),
    )


def validate_email_configuration():

    required = {
        "API_KEY": app.config["API_KEY"],
        "API_URL": app.config["API_URL"],
        "API_FROM": app.config["API_FROM"],
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    if missing:
        raise EmailConfigurationError(
            "Configuração de e-mail incompleta: "
            + ", ".join(missing)
        )


def send_email(to, subject, template, **kwargs):

    validate_email_configuration()

    if isinstance(to, str):
        recipients = [to]
    else:
        recipients = list(to)

    recipients = list(
        dict.fromkeys(
            email.strip()
            for email in recipients
            if email and email.strip()
        )
    )

    if not recipients:
        raise EmailConfigurationError(
            "Nenhum destinatário foi informado."
        )

    html_body = render_template(
        template + ".html",
        **kwargs
    )

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

        "subject": (
            app.config["FLASKY_MAIL_SUBJECT_PREFIX"]
            + subject
        ),

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
                "Authorization":
                    f"Bearer {app.config['API_KEY']}",

                "Content-Type":
                    "application/json",
            },

            json=payload,

            timeout=15,
        )

    except requests.RequestException as exc:

        raise EmailDeliveryError(
            "Não foi possível conectar ao serviço de e-mail."
        ) from exc

    if response.status_code != 202:

        app.logger.error(
            "SendGrid recusou o envio. Status=%s Body=%s",
            response.status_code,
            response.text,
        )

        raise EmailDeliveryError(
            f"O serviço de e-mail recusou o envio "
            f"(HTTP {response.status_code})."
        )


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        name = request.form.get(
            "username",
            "",
        ).strip()

        send_to_admin = (
            request.form.get("send_to_admin")
            == "on"
        )

        if not name:

            session["page_message"] = (
                "Informe o nome do usuário."
            )

            session["page_message_type"] = "danger"

            return redirect(
                url_for("index")
            )

        existing = db.session.scalar(
            select(User).where(
                User.username == name
            )
        )

        session["name"] = name

        if existing is not None:

            session["known"] = True

            session["email_notice"] = None

            session["page_message"] = None

            return redirect(
                url_for("index")
            )

        default_role = db.session.scalar(
            select(Role).where(
                Role.name == "User"
            )
        )

        if default_role is None:

            session["page_message"] = (
                "A função User não foi encontrada."
            )

            session["page_message_type"] = "danger"

            return redirect(
                url_for("index")
            )

        user = User(
            username=name,
            role=default_role,
        )

        db.session.add(user)

        try:

            recipients = [
                app.config["STUDENT_EMAIL"]
            ]

            if send_to_admin:
                recipients.append(
                    app.config["FLASKY_ADMIN"]
                )

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

            session["known"] = False

            session["page_message"] = None

            if send_to_admin:

                session["email_notice"] = (
                    "E-mail enviado para o "
                    "Administrador do sistema, "
                    "notificando o cadastro "
                    "de um novo usuário."
                )

            else:

                session["email_notice"] = (
                    "E-mail enviado para o "
                    "endereço institucional, "
                    "notificando o cadastro "
                    "de um novo usuário."
                )

        except (
            EmailConfigurationError,
            EmailDeliveryError,
        ) as exc:

            db.session.rollback()

            app.logger.error(
                "Falha no cadastro/e-mail: %s",
                exc,
            )

            session["page_message"] = (
                "O usuário não foi cadastrado "
                "porque o e-mail obrigatório "
                "não pôde ser enviado."
            )

            session["page_message_type"] = (
                "danger"
            )

            session["email_notice"] = None

        return redirect(
            url_for("index")
        )

    users = db.session.scalars(
        select(User).order_by(
            User.id.asc()
        )
    ).all()

    roles = get_roles()

    user_count = db.session.scalar(
        select(func.count()).select_from(User)
    )

    role_count = db.session.scalar(
        select(func.count()).select_from(Role)
    )

    display_name = (
        session.get("name")
        or app.config["STUDENT_NAME"].split()[0]
    )

    return render_template(
        "index.html",

        name=display_name,

        known=session.get(
            "known",
            False,
        ),

        email_notice=session.get(
            "email_notice"
        ),

        page_message=session.pop(
            "page_message",
            None,
        ),

        page_message_type=session.pop(
            "page_message_type",
            "info",
        ),

        users=users,
        roles=roles,

        user_count=user_count,
        role_count=role_count,
    )


with app.app_context():

    db.create_all()

    create_default_roles()


if __name__ == "__main__":

    app.run(debug=True)
