from typing import Any

class ProfileStage(PipelineStage):
    name = "profile"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        raw = context.get("raw_bytes", b"")
        # crude placeholder profiling
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        rows = len(lines)
        cols = max(len(l.split(",")) for l in lines) if lines else 0
        context["profile"] = {
            "total_rows": rows,
            "total_columns": cols,
        }
        return context