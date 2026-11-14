"""The sales-pitch conversation loop and its input/output channels."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

from .audio import PlayAudio
from .customer import Customer
from .product import Product
from .sarvam import Answer, Question, Sarvam
from .text import DEFAULT_STOP_WORDS, chunk_text, is_stop_request

logger = logging.getLogger(__name__)

PITCH_QUESTION = (
    "Generate shortest sales pitch text for sales representative describing about "
    "the credit card information shared."
)
PITCH_DESCRIPTION = "prepare sales pitch as short as possible explaining about the benefits"
FOLLOW_UP_DESCRIPTION = "Answer customer's question with provided context."
GOODBYE = "Thank you! Hope I served you well."
DIDNT_CATCH = "Sorry, I didn't catch that. Could you please repeat your question?"


class LLM(Protocol):
    def answer(self, context: str, question: Question, description: str) -> Answer: ...


class Channel(Protocol):
    """How the agent talks to the customer."""

    def say(self, text: str) -> None: ...

    def listen(self) -> str: ...


class VoiceChannel:
    """Speaks via Sarvam TTS + speakers and listens via microphone + Sarvam STT."""

    def __init__(self, sarvam: Sarvam, player: PlayAudio | None = None):
        self.sarvam = sarvam
        self.player = player or PlayAudio()

    def say(self, text: str) -> None:
        chunks = chunk_text(text)
        for index, chunk in enumerate(chunks, start=1):
            logger.debug("Playing audio part %d/%d", index, len(chunks))
            self.player.play(self.sarvam.tts(chunk).audio)

    def listen(self) -> str:
        audio = self.player.record()
        logger.debug("Captured %d bytes of audio", len(audio))
        return self.sarvam.stt(audio).text


class TextChannel:
    """Prints replies and reads questions from the keyboard (no audio needed)."""

    def __init__(
        self,
        output: Callable[[str], None] | None = None,
        read: Callable[[str], str] | None = None,
    ):
        # Resolved lazily so builtins can be swapped (e.g. in tests or a REPL).
        self.output = output or (lambda text: print(text, flush=True))
        self.read = read or (lambda prompt: input(prompt))  # noqa: PLW0108

    def say(self, text: str) -> None:
        self.output(f"\nBulBul: {text}")

    def listen(self) -> str:
        try:
            return self.read("\nYou: ")
        except EOFError:
            return "stop"


class Agent:
    """Pitches ``product`` to ``customer`` and answers follow-up questions."""

    def __init__(
        self,
        llm: LLM,
        channel: Channel,
        stop_words: tuple[str, ...] = DEFAULT_STOP_WORDS,
        max_turns: int | None = None,
    ):
        self.llm = llm
        self.channel = channel
        self.stop_words = stop_words
        self.max_turns = max_turns

    def converse(self, customer: Customer, product: Product) -> int:
        """Run the conversation; returns the number of customer questions answered."""
        logger.info("Generating initial sales pitch of %s for %s", product.title, customer.name)
        pitch = self.llm.answer(product.content, Question(PITCH_QUESTION, 0), PITCH_DESCRIPTION)
        self.channel.say(pitch.response)

        turns = 0
        while self.max_turns is None or turns < self.max_turns:
            utterance = self.channel.listen().strip()
            if not utterance:
                self.channel.say(DIDNT_CATCH)
                continue
            if is_stop_request(utterance, self.stop_words):
                break
            turns += 1
            logger.info("Answering customer question #%d", turns)
            answer = self.llm.answer(
                product.content, Question(utterance, turns), FOLLOW_UP_DESCRIPTION
            )
            self.channel.say(answer.response)
        self.channel.say(GOODBYE)
        return turns
