# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Promotion tests for research/global_frontier_transfer. Offline, seeded, CPU."""

import dataclasses
import random

import pytest

from research.global_frontier_transfer import transfer as t


def _chain(rng: random.Random, length: int) -> list[t.Layer]:
    layers: list[t.Layer] = []
    state: set[str] = set()
    head = t.GENESIS
    for index in range(length):
        removals = tuple(
            rng.sample(sorted(state), k=min(len(state), rng.randint(0, 2)))
        )
        additions = tuple(f"r{index}-{n}" for n in range(rng.randint(1, 3)))
        layer = t.Layer(head, additions, removals)
        state = (state - set(removals)) | set(additions)
        layers.append(layer)
        head = layer.name
    return layers


@pytest.mark.parametrize("seed", range(25))
def test_replay_reproduces_head_and_state(seed):
    rng = random.Random(seed)
    layers = _chain(rng, rng.randint(1, 12))
    state, head = t.replay(layers)
    assert head == layers[-1].name
    expected: set[str] = set()
    for layer in layers:
        expected = (expected - set(layer.removals)) | set(layer.additions)
    assert state == expected
    assert t.replay(layers) == (state, head)


@pytest.mark.parametrize("seed", range(25))
def test_any_changed_layer_changes_the_head_or_breaks_the_chain(seed):
    rng = random.Random(seed)
    layers = _chain(rng, rng.randint(2, 12))
    _, head = t.replay(layers)
    index = rng.randrange(len(layers))
    victim = layers[index]
    forged = t.Layer(victim.parent, victim.additions + ("forged",), victim.removals)
    assert forged.name != victim.name
    tampered = layers[:index] + [forged] + layers[index + 1 :]
    if index == len(layers) - 1:
        assert t.replay(tampered)[1] != head
    else:
        with pytest.raises(ValueError, match="LAYER_CHAIN_BROKEN"):
            t.replay(tampered)


def test_layer_is_immutable_and_rejects_contradiction():
    layer = t.Layer(t.GENESIS, ("a",), ())
    with pytest.raises(dataclasses.FrozenInstanceError):
        layer.additions = ("b",)
    with pytest.raises(ValueError, match="LAYER_ADDS_AND_REMOVES_SAME_ITEM"):
        t.Layer(t.GENESIS, ("a",), ("a",))
    with pytest.raises(ValueError, match="LAYER_REMOVES_ABSENT_ITEM"):
        t.replay([t.Layer(t.GENESIS, ("a",), ("b",))])


def test_head_only_advances_to_a_descendant_at_the_current_version():
    a = t.Layer(t.GENESIS, ("a",), ())
    b = t.Layer(a.name, ("b",), ())
    fork = t.Layer(a.name, ("x",), ())
    branch = t.Branch()
    for layer in (a, b, fork):
        branch.register(layer)
    assert branch.set_head(a.name, 0)
    assert branch.set_head(b.name, 1)
    before = (branch.head, branch.version)
    assert not branch.set_head(fork.name, 2)  # sibling, not a descendant
    assert not branch.set_head(a.name, 2)  # ancestor: no rollback
    assert not branch.set_head(b.name, 2)  # no-op move
    assert not branch.set_head("f" * 64, 2)  # unknown layer
    c = t.Layer(b.name, ("c",), ())
    branch.register(c)
    assert not branch.set_head(c.name, 1)  # stale version
    assert (branch.head, branch.version) == before
    assert not hasattr(branch, "force_set_head")
    with pytest.raises(ValueError, match="LAYER_PARENT_UNKNOWN"):
        branch.register(t.Layer("e" * 64, ("z",), ()))


def _skewed_jobs(seed: int, jobs: int = 400) -> list[dict[str, float]]:
    rng = random.Random(seed)
    workers = [f"w{n}" for n in range(6)]
    return [
        {w: rng.random() + (0.5 if w == "w0" else 0.0) for w in workers}
        for _ in range(jobs)
    ]


@pytest.mark.parametrize("seed", range(10))
def test_bias_lowers_load_variance_and_never_touches_recorded_scores(seed):
    jobs = _skewed_jobs(seed)
    base_choice, base_scores, base_load = t.dispatch(jobs, 0.0)
    choice, scores, load = t.dispatch(jobs, 0.01)
    assert sum(load.values()) == sum(base_load.values()) == len(jobs)
    assert t.load_variance(load) < t.load_variance(base_load)
    # The recorded score is the unbiased affinity of whichever worker was chosen.
    assert scores == [job[w] for job, w in zip(jobs, choice)]
    assert base_scores == [job[w] for job, w in zip(jobs, base_choice)]
    assert t.dispatch(jobs, 0.01) == (choice, scores, load)


def test_dispatch_fails_closed_on_bad_input():
    with pytest.raises(ValueError, match="GAMMA_INVALID"):
        t.dispatch([{"a": 1.0}], -0.1)
    with pytest.raises(ValueError, match="GAMMA_INVALID"):
        t.dispatch([{"a": 1.0}], float("nan"))
    with pytest.raises(ValueError, match="AFFINITY_INVALID"):
        t.dispatch([{"a": float("inf")}], 0.0)
    with pytest.raises(ValueError, match="AFFINITY_INVALID"):
        t.dispatch([{"a": 1.0}, {}], 0.0)
