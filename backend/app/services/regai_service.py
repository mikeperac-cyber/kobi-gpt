"""Pure, deterministic KB matching. The LLM only ever sees what these functions return."""


def match_rules(rules: list[dict], *, country: str, hs6: str, sector: str,
                channel: str, structural_use: bool) -> list[dict]:
    def ok(r: dict) -> bool:
        return (
            (not r.get("country") or r["country"] == country)
            and (not r.get("hs_prefixes") or any(hs6.startswith(p) for p in r["hs_prefixes"]))
            and (not r.get("sectors") or sector in r["sectors"])
            and (r.get("channel") is None or r["channel"] == channel)
            and (r.get("structural_use") is None or structural_use)
        )

    return sorted((r for r in rules if ok(r)), key=lambda r: int(r["id"][1:]))


def filter_incentives(incentives: list[dict], sector: str) -> list[dict]:
    return [i for i in incentives if not i.get("sectors") or sector in i["sectors"]]
