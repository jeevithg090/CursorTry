from collections import deque

from fintechagent import Agent, Customer, Product, TextChannel, VoiceChannel
from fintechagent.agent import DIDNT_CATCH, GOODBYE
from fintechagent.sarvam import STT, TTS, Answer, Question

CUSTOMER = Customer("Akhil", "+91 9876543210", "travel")
PRODUCT = Product("World Safari Credit Card", "Zero forex markup.", "travel")


class FakeLLM:
    def __init__(self):
        self.questions: list[Question] = []

    def answer(self, context, question, description):
        assert context == PRODUCT.content
        self.questions.append(question)
        return Answer(question, f"answer-{question.id}", "", "")


class ScriptedChannel:
    def __init__(self, *inputs: str):
        self.inputs = deque(inputs)
        self.said: list[str] = []

    def say(self, text):
        self.said.append(text)

    def listen(self):
        return self.inputs.popleft()


def test_pitch_then_answers_until_stop():
    llm, channel = FakeLLM(), ScriptedChannel("What is the fee?", "Any lounge access?", "stop")
    turns = Agent(llm, channel).converse(CUSTOMER, PRODUCT)
    assert turns == 2
    assert channel.said == ["answer-0", "answer-1", "answer-2", GOODBYE]
    assert [q.question for q in llm.questions[1:]] == ["What is the fee?", "Any lounge access?"]


def test_empty_utterance_asks_to_repeat():
    llm, channel = FakeLLM(), ScriptedChannel("  ", "Thanks, bye")
    assert Agent(llm, channel).converse(CUSTOMER, PRODUCT) == 0
    assert channel.said == ["answer-0", DIDNT_CATCH, GOODBYE]


def test_max_turns():
    llm, channel = FakeLLM(), ScriptedChannel("q1", "q2", "q3")
    assert Agent(llm, channel, max_turns=2).converse(CUSTOMER, PRODUCT) == 2
    assert channel.said[-1] == GOODBYE


def test_text_channel_eof_means_stop():
    out: list[str] = []

    def raise_eof(_prompt):
        raise EOFError

    channel = TextChannel(output=out.append, read=raise_eof)
    assert channel.listen() == "stop"
    channel.say("hi")
    assert out == ["\nBulBul: hi"]


class FakeSarvam:
    def __init__(self):
        self.tts_inputs: list[str] = []

    def tts(self, text):
        self.tts_inputs.append(text)
        return TTS(audio=b"wav:" + text.encode(), text=text)

    def stt(self, audio):
        return STT(text=f"heard {len(audio)} bytes", lang_code="en-IN")


class FakePlayer:
    def __init__(self):
        self.played: list[bytes] = []

    def play(self, audio):
        self.played.append(audio)

    def record(self):
        return b"1234"


def test_voice_channel_chunks_long_text_for_tts():
    sarvam, player = FakeSarvam(), FakePlayer()
    channel = VoiceChannel(sarvam, player)  # type: ignore[arg-type]
    channel.say("Sentence number one. " * 60)
    assert len(sarvam.tts_inputs) >= 3
    assert all(0 < len(t) <= 500 for t in sarvam.tts_inputs)
    assert len(player.played) == len(sarvam.tts_inputs)
    assert channel.listen() == "heard 4 bytes"
