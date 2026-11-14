"""Command-line interface: ``bulbul <command>``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import replace

from dotenv import load_dotenv

from .agent import Agent, Channel, TextChannel, VoiceChannel
from .audio import PlayAudio
from .config import Settings
from .customer import AllCustomers, Customer
from .errors import BulbulError
from .product import Products
from .sarvam import Sarvam

logger = logging.getLogger("fintechagent")

DISCLAIMER = (
    "I'm BulBul, your fintech agent. Disclaimer: I'm a bot created only as a demo "
    "for a tech event, using a bank's publicly available credit card information. "
    "I can recommend a suitable credit card for your needs and answer any "
    "questions you have about it."
)


def greeting(customer: Customer, product_title: str) -> str:
    return (
        f"Hi {customer.name}, how are you doing? I'm from RBL Bank. After analysing "
        f"your spends and needs, I suggest you apply for the {product_title}. "
        "Here are the benefits."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bulbul",
        description=(
            "BulBul: pitch the best-matching credit card to each customer and "
            "answer their questions by voice (or text) using Sarvam AI."
        ),
        epilog=(
            "Examples:\n"
            "  bulbul customers                 list customers and their recommended card\n"
            "  bulbul products                  list the credit-card catalogue\n"
            "  bulbul talk --text               chat with the agent using the keyboard\n"
            "  bulbul talk --customer Bhushan   voice conversation with one customer\n"
            "  bulbul talk --all                talk to every customer in turn\n\n"
            "Say or type 'stop' (or bye/exit/quit) to end a conversation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logs")
    parser.add_argument("--env-file", help="dotenv file to load (default: ./.env)")
    parser.add_argument("--db", help="path to the SQLite customer DB (env: DB_URL)")
    parser.add_argument(
        "--products-dir", help="folder of product description files (env: PRODUCTS_DIR)"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("customers", help="list customers with their recommended product")
    sub.add_parser("products", help="list available credit-card products")

    talk = sub.add_parser("talk", help="start a sales conversation (needs SARVAM_AI_API)")
    who = talk.add_mutually_exclusive_group()
    who.add_argument("-c", "--customer", help="name of the customer to talk to")
    who.add_argument("--all", action="store_true", help="talk to every customer in turn")
    talk.add_argument(
        "--text",
        action="store_true",
        help="type questions and read answers instead of using mic/speakers",
    )
    talk.add_argument("--max-turns", type=int, default=None, help="stop after N customer questions")
    return parser


def _load_data(settings: Settings) -> tuple[AllCustomers, Products]:
    return AllCustomers.fetch_from_db(settings.db_path), Products.fetch_from_folder(
        settings.products_dir
    )


def cmd_customers(settings: Settings) -> int:
    customers, products = _load_data(settings)
    if not customers.customers:
        print("No customers found. Add rows to the 'customers' table.")
        return 0
    width = max(len(c.name) for c in customers.customers)
    print(f"{'NAME':<{width}}  {'SEGMENT':<8}  RECOMMENDED CARD")
    for c in customers.customers:
        print(f"{c.name:<{width}}  {c.segment:<8}  {products.for_segment(c.segment).title}")
    return 0


def cmd_products(settings: Settings) -> int:
    products = Products.fetch_from_folder(settings.products_dir)
    for p in products.products:
        marker = " (default)" if p is products.default_product else ""
        print(f"{p.segment:<8}  {p.title}{marker}")
    return 0


def cmd_talk(settings: Settings, args: argparse.Namespace) -> int:
    customers, products = _load_data(settings)
    if args.customer:
        match = customers.find(args.customer)
        if match is None:
            names = ", ".join(c.name for c in customers.customers) or "none"
            raise BulbulError(f"No customer named '{args.customer}'. Known: {names}.")
        targets = [match]
    elif args.all:
        targets = customers.customers
    else:
        targets = customers.customers[:1]
    if not targets:
        raise BulbulError("No customers found in the database.")

    sarvam = Sarvam.from_settings(settings)
    if not args.text:
        PlayAudio.ensure_available()  # fail fast before spending API calls
    channel: Channel = TextChannel() if args.text else VoiceChannel(sarvam)
    agent = Agent(sarvam, channel, max_turns=args.max_turns)

    channel.say(DISCLAIMER)
    for customer in targets:
        product = products.for_segment(customer.segment)
        logger.info("Conversation with %s about %s", customer.name, product.title)
        channel.say(greeting(customer, product.title))
        agent.converse(customer, product)
    logger.info("Conversations ended")
    return 0


def _log_level(args: argparse.Namespace) -> int:
    if args.verbose:
        return logging.DEBUG
    # Keep the keyboard chat clean; voice mode benefits from progress logs.
    return logging.WARNING if getattr(args, "text", False) else logging.INFO


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=_log_level(args),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    if args.command is None:
        parser.print_help()
        return 0
    # Values already exported in the shell take precedence over .env.
    load_dotenv(dotenv_path=args.env_file or ".env", override=False)
    try:
        settings = Settings.from_env()
        overrides = {
            k: v for k, v in {"db_path": args.db, "products_dir": args.products_dir}.items() if v
        }
        if overrides:
            settings = replace(settings, **overrides)
        if args.command == "customers":
            return cmd_customers(settings)
        if args.command == "products":
            return cmd_products(settings)
        return cmd_talk(settings, args)
    except BulbulError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
