"""Suite-wide guards.

The hosted language service is a paid, rate-limited, third-party dependency. A test
that reaches it is not a test: it spends credits, it fails when the network does, and
its result depends on a model that can change under it. Any test needing translation
or speech must supply its own stub.

This fixture makes an accidental call fail loudly rather than silently succeed, so the
suite cannot come to depend on the network without someone noticing.
"""
import pytest

from weathergpt_data import answer_language, providers, speech


@pytest.fixture(autouse=True)
def no_model_planner_by_default(monkeypatch):
    """The suite plans with the deterministic rules unless a test asks for a model and stubs it.

    The product default is the model (WEATHERGPT_PLANNER=model) and a live journey measures that.
    A component check that reaches a real provider is not a check: it costs credits, it fails when
    the network does, and its result depends on a model that can change under it. A test that wants
    the model path builds its router with policy='model' and its own stub client.
    """
    monkeypatch.setenv(providers.PLANNER_POLICY_ENV, 'rules')
    yield


@pytest.fixture(autouse=True)
def no_hosted_language_calls(monkeypatch):
    """Run the suite as a machine with no key configured, which is also the common state.

    A test that wants translation or speech passes its own stub. Reaching the real
    service raises rather than quietly succeeding, so the suite cannot drift into
    depending on it.
    """
    def refuse(*args, **kwargs):
        raise AssertionError(
            'A test attempted to call the hosted language service. Supply a stub translator '
            'or transcriber instead; the suite must not depend on a paid external service.')
    monkeypatch.setattr(speech, '_request', refuse)
    monkeypatch.setattr(answer_language, '_service_translator', lambda: None)
    yield
