class QualityEngine:
    def score(self, profile: dict) -> dict:
        completeness = 1 - profile.get("null_pct",0)
        uniqueness = 1 - profile.get("duplicate_pct",0)
        overall = (completeness + uniqueness)/2
        return {"overall": overall, "completeness": completeness, "uniqueness": uniqueness}
