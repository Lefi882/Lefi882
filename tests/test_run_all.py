from argparse import Namespace

from scripts.run_all import build_steps


def test_build_steps_default() -> None:
    args = Namespace(
        python="python3",
        node="node",
        tipsport_sport="16",
        tipsport_json="tipsport_odds.json",
        betano_json="betano_odds.json",
        target="tipsport",
        min_edge=1.0,
        top=20,
        run_snapshot=False,
        providers_file="providers.json",
    )

    steps = build_steps(args)

    assert steps[0][:3] == ["node", "scripts/tipsport2.js", "--sport"]
    assert "--json" in steps[0]
    assert steps[1] == ["node", "scripts/betano.js", "--json"]
    assert steps[2][0] == "python3"
    assert "scripts/valuebets_tipsport_betano.py" in steps[2]


def test_build_steps_with_snapshot() -> None:
    args = Namespace(
        python="py",
        node="node",
        tipsport_sport="188",
        tipsport_json="tips.json",
        betano_json="bet.json",
        target="betano",
        min_edge=2.5,
        top=10,
        run_snapshot=True,
        providers_file="providers.custom.json",
    )

    steps = build_steps(args)

    assert len(steps) == 4
    assert steps[-1] == ["py", "main.py", "--iterations", "1", "--providers-file", "providers.custom.json"]
