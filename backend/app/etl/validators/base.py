from typing import Any


class ValidationRule:
    field: str

    def validate(self, row: dict[str, Any]) -> list[str]:
        return []


class RequiredRule(ValidationRule):
    def validate(self, row):
        errors = []
        if not row.get(self.field):
            errors.append(f"{self.field} required")
        return errors
