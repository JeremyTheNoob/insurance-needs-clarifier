from __future__ import annotations

from pathlib import Path

from evals.run_evals import load_scenarios


def test_twelve_scenarios_are_valid():
    scenarios = load_scenarios(Path("evals/scenarios.json"))

    assert len(scenarios) == 12
    ids = [scenario["id"] for scenario in scenarios]
    assert len(set(ids)) == 12

    for scenario in scenarios:
        inputs = [item.strip() for item in scenario["inputs"]]
        assert inputs, scenario["id"]
        assert any(
            item in {"/confirm", "/quit"} for item in inputs
        ), scenario["id"]

        if "/quit" in inputs:
            quit_index = inputs.index("/quit")
            assert quit_index + 1 < len(inputs), scenario["id"]

        if "/confirm" in inputs and "/revise" not in inputs:
            confirm_index = inputs.index("/confirm")
            assert confirm_index + 1 < len(inputs), scenario["id"]
