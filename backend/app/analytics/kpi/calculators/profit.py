from analytics.kpi.definitions import KPI, KPIDefinition

profit_def = KPIDefinition(
    name=KPI.PROFIT,
    formula="SUM(revenue) - SUM(cost)",
    unit="currency",
    description="Total profit after costs"
)