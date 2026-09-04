from enum import Enum


class KPI(str, Enum):
    REVENUE = "revenue"
    PROFIT = "profit"
    GROSS_MARGIN = "gross_margin"
    NET_MARGIN = "net_margin"
    ROI = "roi"
    ROAS = "roas"
    AVERAGE_ORDER_VALUE = "average_order_value"
    SALES_GROWTH = "sales_growth"
    CUSTOMER_GROWTH = "customer_growth"
    CUSTOMER_RETENTION = "customer_retention"
    CHURN = "churn"
    INVENTORY_TURNOVER = "inventory_turnover"
    CONVERSION_RATE = "conversion_rate"
    CUSTOMER_LIFETIME_VALUE = "customer_lifetime_value"
    EMPLOYEE_PRODUCTIVITY = "employee_productivity"


class KPIDefinition:
    def __init__(self, name: KPI, formula: str, unit: str, description: str):
        self.name = name
        self.formula = formula
        self.unit = unit
        self.description = description
