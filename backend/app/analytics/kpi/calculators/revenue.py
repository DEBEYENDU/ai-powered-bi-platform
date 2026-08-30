from analytics.kpi.definitions import KPI, KPIDefinition

revenue_def = KPIDefinition(
    name=KPI.REVENUE,
    formula="SUM(amount)",
    unit="currency",
    description="Total revenue from sales"
)

profit_def = KPIDefinition(
    name=KPI.PROFIT,
    formula="SUM(revenue) - SUM(cost)",
    unit="currency",
    description="Total profit"
)