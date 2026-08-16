"""Outbound email, and what to do when there is none.

WHY THIS EXISTS
---------------
Two flows have to hand a secret to whoever owns an email address and to
nobody else: the password reset, and email verification. Until now the
app had no way to do that, and the password reset solved it by
**returning the reset token in the HTTP response** - which meant knowing
somebody's email address was enough to take their account. The code was
honest about it in a docstring; that did not make it any less of a full
account takeover.

The fix is not "add SMTP and hope it is configured". The fix is that the
token leaves through a channel only the address owner can read, and if
no such channel exists the token is **not issued to the caller at all**.
This module is that channel, plus an explicit, safe answer for the case
where it is unconfigured.

TRANSPORTS
----------
  * `smtp`    - a real server, from SMTP_HOST and friends.
  * `log`     - the default when nothing is configured. The message is
                written to the server log, where an operator with server
                access can read it. That is a deliberate downgrade: it
                keeps the flow usable for a local run or a judge's
                laptop WITHOUT putting the secret on the wire to an
                anonymous caller. Server-log access already implies
                total control of the deployment, so nothing is lost that
                was not already lost.
  * `memory`  - tests. Collects messages in a list.

`send()` never raises. A mail server that is down must not turn into a
500 on a registration, and it must never turn into "here is the token
instead" either - the caller is told delivery failed and that is all.

CONFIGURATION
-------------
    MAIL_TRANSPORT       smtp | log | memory      (default: smtp if
                                                   SMTP_HOST is set,
                                                   else log)
    SMTP_HOST            e.g. smtp.gmail.com
    SMTP_PORT            default 587
    SMTP_USERNAME        optional
    SMTP_PASSWORD        optional
    SMTP_FROM            default no-reply@digital-wellness-ai.local
    SMTP_STARTTLS        1 (default) | 0
    SMTP_TIMEOUT         seconds, default 10
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_FROM = "no-reply@digital-wellness-ai.local"
DEFAULT_PORT = 587
DEFAULT_TIMEOUT = 10.0


@dataclass(slots=True)
class Message:
    to: str
    subject: str
    body: str


@dataclass(slots=True)
class Delivery:
    """What actually happened, in terms the API can report honestly.

    `channel` is what the client is told: "email" when a real server
    accepted the message, "server_log" when it went to the log instead.
    The client must never be told "email" for a message that only
    reached a log file - a user waiting for an email that will never
    arrive is worse than being told where to look.
    """

    delivered: bool
    channel: str  # "email" | "server_log" | "none"
    detail: str = ""


class Transport:
    name = "none"

    def deliver(self, message: Message) -> Delivery:  # pragma: no cover - interface
        raise NotImplementedError


class LogTransport(Transport):
    """No mail server configured. The secret goes to the server log.

    Logged at WARNING, with the flow named, so it is obvious in the
    console that this deployment is running without email and that the
    operator is the delivery mechanism.
    """

    name = "log"

    def deliver(self, message: Message) -> Delivery:
        logger.warning(
            "No mail transport configured - delivering to the server log instead.\n"
            "  to:      %s\n  subject: %s\n  body:\n%s",
            message.to, message.subject, message.body,
        )
        return Delivery(True, "server_log", "written to the server log")


class MemoryTransport(Transport):
    """Tests. Nothing leaves the process."""

    name = "memory"

    def __init__(self) -> None:
        self.sent: list[Message] = []

    def deliver(self, message: Message) -> Delivery:
        self.sent.append(message)
        return Delivery(True, "email", "captured in memory")

    def clear(self) -> None:
        self.sent.clear()

    def last_to(self, address: str) -> Optional[Message]:
        for message in reversed(self.sent):
            if message.to.lower() == address.lower():
                return message
        return None


@dataclass(slots=True)
class SMTPTransport(Transport):
    host: str
    port: int = DEFAULT_PORT
    username: Optional[str] = None
    password: Optional[str] = None
    sender: str = DEFAULT_FROM
    starttls: bool = True
    timeout: float = DEFAULT_TIMEOUT
    name: str = field(default="smtp", init=False)

    def deliver(self, message: Message) -> Delivery:
        payload = EmailMessage()
        payload["From"] = self.sender
        payload["To"] = message.to
        payload["Subject"] = message.subject
        payload.set_content(message.body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                if self.starttls:
                    server.starttls(context=ssl.create_default_context())
                if self.username:
                    server.login(self.username, self.password or "")
                server.send_message(payload)
        except Exception as error:  # noqa: BLE001 - see the module docstring
            # Deliberately broad. smtplib raises a dozen unrelated types
            # and the socket layer raises more; none of them are a reason
            # to 500 a registration, and none of them may be allowed to
            # fall through to "return the token to the caller instead".
            logger.warning("Mail delivery to %s failed: %s", message.to, error)
            return Delivery(False, "none", str(error)[:200])
        return Delivery(True, "email", "accepted by the mail server")


# ------------------------------------------------------------------ service

class MailService:
    """One place that decides how - and whether - a secret gets out."""

    def __init__(self, transport: Optional[Transport] = None) -> None:
        self._transport = transport or _transport_from_environment()

    @property
    def transport_name(self) -> str:
        return self._transport.name

    @property
    def can_reach_the_user(self) -> bool:
        """True only when a real mail server is in play.

        The password-reset flow reads this to decide whether it may hand
        the token back over HTTP. With a real transport the answer is
        always no; without one, the token still does not go over HTTP -
        it goes to the log. Nothing about this property re-opens that.
        """
        return self._transport.name == "smtp" or self._transport.name == "memory"

    def send(self, to: str, subject: str, body: str) -> Delivery:
        if not to or "@" not in to:
            return Delivery(False, "none", "no usable address")
        try:
            return self._transport.deliver(Message(to, subject, body))
        except Exception as error:  # noqa: BLE001
            logger.exception("Mail transport raised unexpectedly")
            return Delivery(False, "none", str(error)[:200])


def _transport_from_environment() -> Transport:
    choice = (os.environ.get("MAIL_TRANSPORT") or "").strip().lower()
    host = (os.environ.get("SMTP_HOST") or "").strip()

    if not choice:
        choice = "smtp" if host else "log"

    if choice == "memory":
        return MemoryTransport()
    if choice == "smtp":
        if not host:
            logger.warning(
                "MAIL_TRANSPORT=smtp but SMTP_HOST is not set - falling back to the log "
                "transport. Password resets and verification codes will go to the server "
                "log, not to the user's inbox."
            )
            return LogTransport()
        return SMTPTransport(
            host=host,
            port=int(os.environ.get("SMTP_PORT") or DEFAULT_PORT),
            username=os.environ.get("SMTP_USERNAME") or None,
            password=os.environ.get("SMTP_PASSWORD") or None,
            sender=os.environ.get("SMTP_FROM") or DEFAULT_FROM,
            starttls=(os.environ.get("SMTP_STARTTLS", "1").strip() not in {"0", "false", "no"}),
            timeout=float(os.environ.get("SMTP_TIMEOUT") or DEFAULT_TIMEOUT),
        )
    return LogTransport()


# The app-wide instance. Built lazily so importing this module never
# touches the environment, and rebuildable so a test can swap in a
# MemoryTransport without monkeypatching every call site.
_service: Optional[MailService] = None


def get_mail_service() -> MailService:
    global _service
    if _service is None:
        _service = MailService()
    return _service


def set_mail_service(service: Optional[MailService]) -> None:
    """Install a specific service (tests), or None to rebuild from env."""
    global _service
    _service = service
