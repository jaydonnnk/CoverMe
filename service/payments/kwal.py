"""Cover's Kwal client (3.1): catalogue, quotes, funding and checkout.

Imports the Kwal skill's own modules (`catalog`, `quotes`, `checkout`,
`vault`, `session`) instead of shelling out to `register.py`, so every
response still goes through the skill's parsers and checks. The skill lives
outside the repo (`KWAL_SKILL_DIR`, default
`~/.agents/skills/agent-payment/scripts`) and needs Linux (`fcntl`).

Three things are added on top of the skill:
- One global lock. Every Kwal call holds it, so one payment runs at a time.
- Retries. Provider-busy and no-answer errors are retried every 15-30 s for
  up to 5 minutes from the first failure (the skill's `references/debug.md`).
  A checkout whose outcome is unknown is read back before it is resent.
- Recording. The skill's single HTTP function is wrapped, so every raw
  response is written to `service/fixtures/kwal/<run>/`, with Ana's address
  redacted. `use_replay(dir)` serves such a run back without the network.

Never registers a participant. The saved session is the only identity.
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import itertools
import json
import os
import random
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

SKILL_DIR_ENV = "KWAL_SKILL_DIR"
DEFAULT_SKILL_DIR = Path.home() / ".agents" / "skills" / "agent-payment" / "scripts"
CREDENTIALS_ENV = "KWAL_CREDENTIALS"  # same path the skill's PWS_CREDENTIALS_FILE takes
FIXTURES_ENV = "KWAL_FIXTURES_DIR"
RECORD_ENV = "KWAL_RECORD"  # "0" turns recording off
DEFAULT_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "kwal"

SANDBOX_QUOTE_PREFIX = "sandbox_quote_"
USDC_DECIMALS = 6
RETRY_BUDGET_SECONDS = 300
RETRY_WAIT_SECONDS = (15, 30)
MAX_VARIANT_SEARCH = 50  # option combinations tried to place an unknown variant

LOCK = threading.RLock()  # one Kwal call, and so one payment, at a time

# Patched by tests.
_sleep: Callable[[float], None] = time.sleep
_clock: Callable[[], float] = time.monotonic


class KwalError(Exception):
    """A Kwal failure. The message is the skill's, which is safe to show."""


class QuoteNotPayable(KwalError):
    """The quote is expired, already used by a payment, or needs a choice."""


# ---------------------------------------------------------------- types (3.1)


_E164 = re.compile(r"^\+[1-9][0-9]{6,14}$")


@dataclass(frozen=True, kw_only=True)
class ShipTo:
    """Ana's saved address (`ANA_SHIP_TO_JSON`), never the agent's."""

    first_name: str
    last_name: str
    phone: str  # E.164, e.g. "+14155550123"
    line1: str
    line2: str = ""
    city: str
    region: str = ""  # state / province
    postal_code: str = ""
    country: str  # ISO-2, e.g. "US"
    email: str

    def __post_init__(self) -> None:
        for f in dataclasses.fields(self):
            object.__setattr__(self, f.name, str(getattr(self, f.name) or "").strip())
        object.__setattr__(self, "country", self.country.upper())
        object.__setattr__(self, "email", self.email.lower())
        missing = [
            name
            for name in ("first_name", "last_name", "phone", "line1", "city", "country", "email")
            if not getattr(self, name)
        ]
        if missing:
            raise ValueError(f"ShipTo needs {', '.join(missing)}")
        if not _E164.match(self.phone):
            raise ValueError("ShipTo phone must be E.164, e.g. +14155550123")
        if len(self.country) != 2:
            raise ValueError("ShipTo country must be ISO-2, e.g. US")

    @classmethod
    def from_json(cls, value: str | dict) -> "ShipTo":
        data = json.loads(value) if isinstance(value, str) else dict(value)
        known = {f.name for f in dataclasses.fields(cls)}
        extra = set(data) - known
        if extra:
            raise ValueError(f"ShipTo has unknown fields: {', '.join(sorted(extra))}")
        return cls(**data)

    def canonical_json(self) -> str:
        """J1 item 4: sorted keys, no spaces, every field present."""
        return json.dumps(dataclasses.asdict(self), sort_keys=True, separators=(",", ":"))

    def address_hash(self) -> str:
        """keccak256 of `canonical_json()`, for `setLimits` and the request."""
        from eth_utils import keccak

        return "0x" + keccak(text=self.canonical_json()).hex()

    def kwal_address(self) -> dict[str, str]:
        address = {
            "firstName": self.first_name,
            "lastName": self.last_name,
            "phone": self.phone,
            "line1": self.line1,
            "line2": self.line2,
            "city": self.city,
            "region": self.region,
            "postalCode": self.postal_code,
            "country": self.country,
        }
        return {key: value for key, value in address.items() if value}


@dataclass
class Quote:
    quote_id: str
    product_id: str
    variant_id: str
    shop: str  # Kwal's merchant name, lowercase, e.g. "divinikey" (Kwal gives no domain)
    title: str
    colour: str  # lowercase option label, "" if the product has none
    size: str
    model: str
    image_url: Optional[str]  # Kwal returns no image today, so None
    listed_usd_cents: int  # the item price; limits use this
    charge_usdc: int  # the quote total (item + shipping + tax), 6 decimals; what moves
    sandbox_pricing: bool  # quote_id starts with "sandbox_quote_"
    expires_at: int = 0  # unix seconds; Kwal quotes live 5 minutes


@dataclass(frozen=True)
class Product:
    product_id: str
    title: str
    shop: str
    listed_usd_cents: Optional[int]


# ------------------------------------------------------------- skill loading

_skill: Optional[SimpleNamespace] = None
_live_request_json: Optional[Callable[..., Any]] = None
_replay: Optional["Replay"] = None
_variants: dict[str, dict[str, Any]] = {}  # variant_id -> product_id, title, labels, price
_products: dict[str, Any] = {}  # product_id -> skill ProductDetail


def skill() -> SimpleNamespace:
    """Import the skill's modules once and route its HTTP through `_request_json`."""
    global _skill, _live_request_json
    if _skill is not None:
        return _skill
    directory = Path(os.environ.get(SKILL_DIR_ENV) or DEFAULT_SKILL_DIR).expanduser()
    if not (directory / "catalog.py").is_file():
        raise KwalError(f"Kwal skill not found at {directory}; set {SKILL_DIR_ENV}")
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    import catalog
    import checkout
    import cli_support
    import errors
    import quotes
    import session
    import transport
    import vault

    # `_participant_json` (catalog, quotes, checkout) looks `request_json` up in
    # transport's globals; vault imported it by name. Swap both.
    _live_request_json = transport.request_json
    transport.request_json = _request_json
    vault.request_json = _request_json
    _skill = SimpleNamespace(
        catalog=catalog,
        checkout=checkout,
        cli_support=cli_support,
        errors=errors,
        quotes=quotes,
        session=session,
        transport=transport,
        vault=vault,
    )
    return _skill


def _credentials():
    s = skill()
    if _replay is not None:
        return s.session.Credentials(
            service_url="https://replay.invalid", token="replay-token-not-real", expires_at=2**62
        )
    try:
        credentials = s.session.CredentialStore(_credentials_path()).load()
    except s.errors.AgentPaymentError as error:
        raise KwalError(str(error)) from error
    if credentials.is_expired(int(time.time())):
        raise KwalError("Kwal session expired. There is no renewal; never re-register.")
    return credentials


def _credentials_path() -> Path:
    return skill().session.resolve_credentials_path(os.environ.get(CREDENTIALS_ENV) or None)


# ------------------------------------------------------- recording and replay

_run_dir: Optional[Path] = None
_seq = itertools.count(1)
_private: set[str] = set()  # ShipTo values to redact from fixtures


def _remember_private(ship_to: ShipTo) -> None:
    for name, value in dataclasses.asdict(ship_to).items():
        if name != "country" and len(value) >= 3:
            _private.add(value)


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return "<redacted>" if any(secret in value for secret in _private) else value
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _slug(path: str) -> str:
    route = path.split("?", 1)[0].removeprefix("/kwal/participant/v1/")
    return re.sub(r"[^A-Za-z0-9]+", "-", route).strip("-")[:80] or "root"


def _record(method: str, path: str, payload: Any, body: Any = None, error: Optional[str] = None) -> None:
    global _run_dir
    if _replay is not None or os.environ.get(RECORD_ENV, "1") == "0":
        return
    if _run_dir is None:
        root = Path(os.environ.get(FIXTURES_ENV) or DEFAULT_FIXTURES)
        _run_dir = root / _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    _run_dir.mkdir(parents=True, exist_ok=True)
    document = {
        "recorded_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "method": method,
        "path": _redact(path),
        "request": _redact(payload),
        "response": _redact(body),
        "error": error,
    }
    name = f"{next(_seq):04d}_{method}_{_slug(path)}.json"
    (_run_dir / name).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _request_json(service_url: str, path: str, *, method: str = "GET", payload=None, token=None, deadline=None):
    if _replay is not None:
        return _replay(method, path, payload)
    if token:
        _private.add(token)  # never written to a fixture
    try:
        body = _live_request_json(
            service_url, path, method=method, payload=payload, token=token, deadline=deadline
        )
    except skill().errors.AgentPaymentError as error:
        _record(method, path, payload, error=str(error))
        raise
    _record(method, path, payload, body)
    return body


class Replay:
    """Serves a recorded run: each request takes the next unused response
    recorded for the same method and path."""

    def __init__(self, directory: Path | str) -> None:
        self.records = [
            json.loads(file.read_text(encoding="utf-8"))
            for file in sorted(Path(directory).glob("*.json"))
        ]
        self.used: set[int] = set()

    def __call__(self, method: str, path: str, payload: Any) -> Any:
        for index, record in enumerate(self.records):
            if index not in self.used and record["method"] == method and record["path"] == path:
                self.used.add(index)
                if record.get("error"):
                    raise skill().errors.ServiceError(record["error"])
                return record["response"]
        raise skill().errors.ServiceError(f"{method} {path} has no recorded response.")


def use_replay(directory: Path | str | None) -> None:
    """Serve Kwal from a recorded run (None goes back to the network)."""
    global _replay
    skill()
    _replay = Replay(directory) if directory is not None else None
    _variants.clear()
    _products.clear()


def new_recording() -> None:
    """Start a new fixture directory on the next live call."""
    global _run_dir
    _run_dir = None


# ------------------------------------------------------------------ retries


def _retryable(message: str) -> bool:
    if "service_error=ParticipantUnavailable" in message or "HTTP 429" in message:
        return True
    if re.search(r"HTTP 50[234]\.", message) and "service_error=" not in message:
        return True
    return "did not complete" in message


def _wait_for(message: str) -> float:
    wait = random.uniform(*RETRY_WAIT_SECONDS)
    hint = re.search(r"retry_after=([0-9]+)s", message)
    return max(wait, float(hint.group(1))) if hint else wait


def _retry(operation: Callable[[], T], *, before_retry: Optional[Callable[[], Optional[T]]] = None) -> T:
    """Run `operation`, retrying busy/no-answer errors for up to 5 minutes from
    the first failure. `before_retry` may return a result that ends the retry
    (the read-back of an unknown checkout)."""
    errors = skill().errors
    first_failure: Optional[float] = None
    while True:
        try:
            return operation()
        except errors.AgentPaymentError as error:
            message = str(error)
            if not _retryable(message):
                raise KwalError(message) from error
            first_failure = _clock() if first_failure is None else first_failure
            wait = _wait_for(message)
            if _clock() - first_failure + wait > RETRY_BUDGET_SECONDS:
                raise KwalError(f"{message} (gave up after 5 minutes)") from error
            _sleep(wait)
            if before_retry is not None:
                settled = before_retry()
                if settled is not None:
                    return settled


def _call(operation: Callable[[], T]) -> T:
    with LOCK:
        return _retry(operation)


# ---------------------------------------------------------------- amounts


def _cents(amount) -> int:
    """A USD amount in cents, rounded up."""
    if amount is None:
        raise KwalError("Kwal reported no price.")
    if amount.currency != "USD":
        raise KwalError(f"Kwal priced in {amount.currency}; Cover handles USD only.")
    scale = 10 ** amount.decimals
    return -(-amount.minor_units * 100 // scale)


def _usdc(amount) -> int:
    """A USD total in 6-decimal USDC units (Kwal converts 1:1), rounded up."""
    if amount is None:
        raise KwalError("Kwal reported no total.")
    if amount.currency not in ("USD", "USDC"):
        raise KwalError(f"Kwal priced in {amount.currency}; Cover handles USD only.")
    if amount.decimals <= USDC_DECIMALS:
        return amount.minor_units * 10 ** (USDC_DECIMALS - amount.decimals)
    return -(-amount.minor_units // 10 ** (amount.decimals - USDC_DECIMALS))


# ----------------------------------------------------- catalogue and options

_SIGNED = {"color": "colour", "colour": "colour", "size": "size", "model": "model"}


def _field_names(option_names: list[str]) -> dict[str, str]:
    """Kwal option name -> the key Cover uses. Color/Size/Model map to the
    signed fields; the first other option becomes `model` if Model is absent;
    anything else keeps its lowercased name (shown, never signed)."""
    names = {name: _SIGNED.get(name.strip().lower(), "") for name in option_names}
    taken = set(names.values())
    for name in option_names:
        if names[name]:
            continue
        if "model" not in taken:
            names[name] = "model"
            taken.add("model")
        else:
            names[name] = name.strip().lower()
    return names


def _shop(merchant: Optional[str]) -> str:
    return (merchant or "").strip().lower()


def search(query: str, limit: int = 10) -> list[Product]:
    s = skill()
    credentials = _credentials()
    found = _call(lambda: s.catalog.search_products(credentials.service_url, credentials.token, query, limit=limit))
    return [
        Product(
            product_id=p.product_id,
            title=p.title,
            shop=_shop(p.merchant),
            listed_usd_cents=_cents(p.price) if p.price is not None else None,
        )
        for p in found
    ]


def _product(product_id: str):
    if product_id not in _products:
        s = skill()
        credentials = _credentials()
        _products[product_id] = _call(
            lambda: s.catalog.read_product(credentials.service_url, credentials.token, product_id)
        )
    return _products[product_id]


def options(product_id: str) -> dict[str, list[str]]:
    """The sign card's dropdowns: {"colour": ["snow white", ...], ...}, lowercased."""
    detail = _product(product_id)
    names = _field_names([option.name for option in detail.options])
    return {names[o.name]: [v.label.strip().lower() for v in o.values] for o in detail.options}


def variant(product_id: str, choices: dict[str, str]) -> str:
    """Resolve Cover choices ({"colour": "snow white"}) to a purchasable
    variant id. Labels match case-insensitively; every option needs a choice."""
    detail = _product(product_id)
    names = _field_names([option.name for option in detail.options])
    wanted = {key.strip().lower(): value.strip().lower() for key, value in choices.items()}
    unknown = set(wanted) - set(names.values())
    if unknown:
        raise KwalError(f"{detail.product.title} has no option {', '.join(sorted(unknown))}")
    selected = []
    for option in detail.options:
        key = names[option.name]
        if key not in wanted:
            raise KwalError(f"Choose a {key}: {', '.join(v.label for v in option.values)}")
        match = [v.label for v in option.values if v.label.strip().lower() == wanted[key]]
        if len(match) != 1:
            raise KwalError(f"{wanted[key]!r} is not a {key} of {detail.product.title}")
        selected.append((option.name, match[0]))
    return _resolve(product_id, tuple(selected))


def _resolve(product_id: str, selected: tuple[tuple[str, str], ...]) -> str:
    s = skill()
    credentials = _credentials()
    detail = _product(product_id)
    found = _call(
        lambda: s.catalog.resolve_variant(credentials.service_url, credentials.token, product_id, selected)
    )
    if not found.purchasable:
        raise KwalError(f"{detail.product.title} ({found.title}) is not purchasable")
    names = _field_names([option.name for option in detail.options])
    _variants[found.variant_id] = {
        "product_id": product_id,
        "title": detail.product.title,
        "shop": _shop(detail.product.merchant),
        "labels": {names[name]: label.strip().lower() for name, label in selected},
        "price": found.price,
    }
    return found.variant_id


def _variant_info(variant_id: str, product_id: Optional[str]) -> dict[str, Any]:
    """Kwal has no variant -> product route, so a variant is known from
    `variant()` or found by trying its product's option combinations."""
    if variant_id in _variants:
        return _variants[variant_id]
    if product_id is None:
        raise KwalError(
            f"Unknown variant {variant_id}: resolve it with variant(product_id, choices) or pass product_id"
        )
    detail = _product(product_id)
    combos = itertools.product(*[[(o.name, v.label) for v in o.values] for o in detail.options])
    for selected in itertools.islice(combos, MAX_VARIANT_SEARCH):
        try:
            if _resolve(product_id, tuple(selected)) == variant_id:
                return _variants[variant_id]
        except KwalError:
            continue
    raise KwalError(f"Variant {variant_id} is not an option of product {product_id}")


# ------------------------------------------------------------------ quotes


def _cheapest(options) -> str:
    return min(options, key=lambda o: _usdc(o.price) if o.price is not None else 0).shipping_option_id


def quote(variant_id: str, quantity: int, ship_to: ShipTo, product_id: Optional[str] = None) -> Quote:
    """Price one item to Ana's address. `listed_usd_cents` is the item price,
    `charge_usdc` the quote total. Quantity must be 1 (no signed field for it)."""
    if quantity != 1:
        raise ValueError("Cover buys exactly one item per request (quantity must be 1)")
    s = skill()
    _remember_private(ship_to)
    info = _variant_info(variant_id, product_id)
    credentials = _credentials()
    line = s.quotes.QuoteLine(variant_id=variant_id, quantity=1)
    with LOCK:
        priced = _retry(
            lambda: s.quotes.create_quote(
                credentials.service_url,
                credentials.token,
                (line,),
                email=ship_to.email,
                shipping_address=ship_to.kwal_address(),
            )
        )
        if priced.payment_id is not None:
            raise QuoteNotPayable(
                f"Quote {priced.quote_id} already belongs to payment {priced.payment_id}"
                " (Reap reuses a basket's quote for ~15 minutes)"
            )
        if priced.needs_shipping_selection():
            option = _cheapest(priced.shipping_options)
            priced = _retry(
                lambda: s.quotes.select_shipping(credentials.service_url, credentials.token, priced.quote_id, option)
            )
    if priced.is_expired(int(time.time())) and _replay is None:
        raise QuoteNotPayable(f"Quote {priced.quote_id} expired")
    labels = info["labels"]
    return Quote(
        quote_id=priced.quote_id,
        product_id=info["product_id"],
        variant_id=variant_id,
        shop=info["shop"],
        title=info["title"],
        colour=labels.get("colour", ""),
        size=labels.get("size", ""),
        model=labels.get("model", ""),
        image_url=None,
        listed_usd_cents=_cents(info["price"]),
        charge_usdc=_usdc(priced.total),
        sandbox_pricing=priced.quote_id.startswith(SANDBOX_QUOTE_PREFIX),
        expires_at=priced.expires_at,
    )


def read_quote(quote_id: str):
    """The skill's quote record (total, shipping, tax, expiry, payment)."""
    s = skill()
    credentials = _credentials()
    return _call(lambda: s.quotes.read_quote(credentials.service_url, credentials.token, quote_id))


# ----------------------------------------------------------------- funding


def funding(quote_id: str):
    """The vault's readiness for this quote (skill `Funding`). Reserves nothing."""
    s = skill()
    credentials = _credentials()
    return _call(lambda: s.vault.read_funding(credentials.service_url, credentials.token, quote_id=quote_id))


def wait_for_funding(quote_id: str, timeout: float = 300, interval: float = 3) -> Any:
    """Poll until the vault is `ready` for the quote, or `timeout` seconds pass.
    Returns the last `Funding`; the caller decides what a non-ready state means."""
    deadline = _clock() + timeout
    while True:
        state = funding(quote_id)
        if state.state == "ready" or _clock() + interval > deadline:
            return state
        _sleep(interval)


# ---------------------------------------------------------------- checkout


def _attempts():
    return skill().checkout.AttemptStore(_credentials_path())


def checkout(quote_id: str, *, payment_id: Optional[str] = None):
    """Submit the checkout for one priced quote and return the skill `Payment`.

    SPENDS TEST USDC from the vault. The payment id is saved beside the Kwal
    credentials before sending, so a lost answer resumes the same payment and
    never pays twice. Never call this without the shopper's authorization."""
    s = skill()
    credentials = _credentials()
    with LOCK:
        current = _retry(lambda: s.quotes.read_quote(credentials.service_url, credentials.token, quote_id))
        if current.payment_id is not None and current.payment_id != payment_id:
            raise QuoteNotPayable(f"Quote {quote_id} already belongs to payment {current.payment_id}")
        if current.is_expired(int(time.time())) and _replay is None:
            raise QuoteNotPayable(f"Quote {quote_id} expired")
        if current.needs_shipping_selection():
            raise QuoteNotPayable(f"Quote {quote_id} needs a shipping choice")
        if payment_id is None:
            attempt = _attempts().record(
                s.checkout.Attempt(payment_id=s.checkout.new_payment_id(), quote_id=quote_id)
            )
            payment_id = attempt.payment_id

        def read_back():
            # An unknown outcome may have saved the payment: read it first.
            try:
                return s.checkout.read_payment(
                    credentials.service_url, credentials.token, payment_id, quote_id=quote_id
                )
            except s.errors.AgentPaymentError as error:
                if "ParticipantNotFound" in str(error):
                    return None  # nothing saved: resend under the same id
                raise KwalError(str(error)) from error

        return _retry(
            lambda: s.checkout.create_checkout(credentials.service_url, credentials.token, payment_id, quote_id),
            before_retry=read_back,
        )


def payment(payment_id: str, *, quote_id: Optional[str] = None):
    s = skill()
    credentials = _credentials()
    return _call(
        lambda: s.checkout.read_payment(credentials.service_url, credentials.token, payment_id, quote_id=quote_id)
    )


def wait_for_payment(payment_id: str, timeout: float = 300, interval: float = 3, *, quote_id: Optional[str] = None):
    """Poll a payment until it leaves `pending`, or `timeout` seconds pass."""
    deadline = _clock() + timeout
    while True:
        state = payment(payment_id, quote_id=quote_id)
        if state.state != "pending" or _clock() + interval > deadline:
            return state
        _sleep(interval)
