"""Financials service for financial ratios and key metrics."""

from typing import Optional

from boomberg.api.client import FMPClient
from boomberg.api.models import (
    BalanceSheet,
    CashFlowStatement,
    FinancialRatiosTTM,
    IncomeStatement,
    KeyMetricsTTM,
)


class FinancialsService:
    """Service for fetching and formatting financial data."""

    def __init__(self, client: FMPClient):
        self._client = client

    async def get_ratios(self, symbol: str) -> FinancialRatiosTTM:
        """Get financial ratios for a symbol."""
        return await self._client.get_financial_ratios_ttm(symbol)

    async def get_key_metrics(self, symbol: str) -> KeyMetricsTTM:
        """Get key metrics for a symbol."""
        return await self._client.get_key_metrics_ttm(symbol)

    async def get_income_statement(
        self, symbol: str, limit: int = 4, period: str = "annual"
    ) -> list[IncomeStatement]:
        """Get income statement data for a symbol."""
        return await self._client.get_income_statement(symbol, limit, period)

    async def get_balance_sheet(
        self, symbol: str, limit: int = 4, period: str = "annual"
    ) -> list[BalanceSheet]:
        """Get balance sheet data for a symbol."""
        return await self._client.get_balance_sheet(symbol, limit, period)

    async def get_cash_flow_statement(
        self, symbol: str, limit: int = 4, period: str = "annual"
    ) -> list[CashFlowStatement]:
        """Get cash flow statement data for a symbol."""
        return await self._client.get_cash_flow_statement(symbol, limit, period)

    @staticmethod
    def format_percent(value: Optional[float], decimals: int = 2) -> str:
        """Format a decimal value as a percentage."""
        if value is None:
            return "N/A"
        return f"{value * 100:.{decimals}f}%"

    @staticmethod
    def format_ratio(value: Optional[float], decimals: int = 2) -> str:
        """Format a ratio value."""
        if value is None:
            return "N/A"
        return f"{value:.{decimals}f}"

    @staticmethod
    def format_large_number(value: Optional[float], currency: str = "$") -> str:
        """Format a large number with appropriate suffix."""
        if value is None:
            return "N/A"
        abs_value = abs(value)
        sign = "-" if value < 0 else ""
        if abs_value >= 1_000_000_000_000:
            return f"{sign}{currency}{abs_value / 1_000_000_000_000:.2f}T"
        elif abs_value >= 1_000_000_000:
            return f"{sign}{currency}{abs_value / 1_000_000_000:.2f}B"
        elif abs_value >= 1_000_000:
            return f"{sign}{currency}{abs_value / 1_000_000:.2f}M"
        elif abs_value >= 1_000:
            return f"{sign}{currency}{abs_value / 1_000:.2f}K"
        else:
            return f"{sign}{currency}{abs_value:.2f}"

    @staticmethod
    def format_currency(value: Optional[float], currency: str = "$") -> str:
        """Format a currency value."""
        if value is None:
            return "N/A"
        return f"{currency}{value:.2f}"

    def get_ratios_summary(
        self, ratios: FinancialRatiosTTM, metrics: Optional[KeyMetricsTTM] = None
    ) -> dict[str, str]:
        """Get a formatted summary of key financial ratios."""
        # ROE and ROA come from key-metrics-ttm, not ratios-ttm
        roe = metrics.roe if metrics else ratios.return_on_equity
        roa = metrics.roa if metrics else ratios.return_on_assets

        return {
            # Profitability
            "Gross Margin": self.format_percent(ratios.gross_profit_margin),
            "Operating Margin": self.format_percent(ratios.operating_profit_margin),
            "Net Margin": self.format_percent(ratios.net_profit_margin),
            "ROE": self.format_percent(roe),
            "ROA": self.format_percent(roa),
            # Liquidity
            "Current Ratio": self.format_ratio(ratios.current_ratio),
            "Quick Ratio": self.format_ratio(ratios.quick_ratio),
            "Cash Ratio": self.format_ratio(ratios.cash_ratio),
            # Valuation
            "P/E Ratio": self.format_ratio(ratios.pe_ratio),
            "PEG Ratio": self.format_ratio(ratios.peg_ratio),
            "P/B Ratio": self.format_ratio(ratios.price_to_book),
            "P/S Ratio": self.format_ratio(ratios.price_to_sales),
            # Debt
            "Debt Ratio": self.format_ratio(ratios.debt_ratio),
            "D/E Ratio": self.format_ratio(ratios.debt_to_equity),
            "Interest Coverage": self.format_ratio(ratios.interest_coverage),
            # Dividend
            "Dividend Yield": self.format_percent(ratios.dividend_yield),
            "Payout Ratio": self.format_percent(ratios.payout_ratio),
        }

    def get_metrics_summary(self, metrics: KeyMetricsTTM, currency: str = "$") -> dict[str, str]:
        """Get a formatted summary of key metrics."""
        return {
            "Market Cap": self.format_large_number(metrics.market_cap, currency),
            "Enterprise Value": self.format_large_number(metrics.enterprise_value, currency),
            "EV/Sales": self.format_ratio(metrics.ev_to_sales),
            "EV/EBITDA": self.format_ratio(metrics.ev_to_ebitda),
            "EV/FCF": self.format_ratio(metrics.ev_to_free_cash_flow),
            "Net Debt/EBITDA": self.format_ratio(metrics.net_debt_to_ebitda),
            "ROIC": self.format_percent(metrics.roic),
            "Revenue/Share": self.format_currency(metrics.revenue_per_share, currency),
            "Book Value/Share": self.format_currency(metrics.book_value_per_share, currency),
            "FCF/Share": self.format_currency(metrics.free_cash_flow_per_share, currency),
            "Working Capital": self.format_large_number(metrics.working_capital, currency),
            "Graham Number": self.format_currency(metrics.graham_number, currency),
        }

    def get_income_summary(self, statement: IncomeStatement, currency: str = "$") -> dict[str, str]:
        """Get a formatted summary of income statement."""
        return {
            "Period": f"{statement.fiscal_year or statement.date} ({statement.period})",
            "Revenue": self.format_large_number(statement.revenue, currency),
            "Gross Profit": self.format_large_number(statement.gross_profit, currency),
            "Operating Income": self.format_large_number(statement.operating_income, currency),
            "Net Income": self.format_large_number(statement.net_income, currency),
            "EPS": self.format_currency(statement.eps, currency),
            "EPS (Diluted)": self.format_currency(statement.eps_diluted, currency),
            "EBITDA": self.format_large_number(statement.ebitda, currency),
        }

    def get_balance_sheet_summary(self, statement: BalanceSheet, currency: str = "$") -> dict[str, str]:
        """Get a formatted summary of balance sheet."""
        return {
            "Period": f"{statement.fiscal_year or statement.date} ({statement.period})",
            "Total Assets": self.format_large_number(statement.total_assets, currency),
            "Total Liabilities": self.format_large_number(statement.total_liabilities, currency),
            "Stockholders Equity": self.format_large_number(statement.total_stockholders_equity, currency),
            "Cash & Equivalents": self.format_large_number(statement.cash_and_equivalents, currency),
            "Total Current Assets": self.format_large_number(statement.total_current_assets, currency),
            "Total Current Liabilities": self.format_large_number(statement.total_current_liabilities, currency),
            "Total Debt": self.format_large_number(statement.total_debt, currency),
            "Net Debt": self.format_large_number(statement.net_debt, currency),
            "Retained Earnings": self.format_large_number(statement.retained_earnings, currency),
        }

    def get_cash_flow_summary(self, statement: CashFlowStatement, currency: str = "$") -> dict[str, str]:
        """Get a formatted summary of cash flow statement."""
        return {
            "Period": f"{statement.fiscal_year or statement.date} ({statement.period})",
            "Operating Cash Flow": self.format_large_number(statement.operating_cash_flow, currency),
            "Investing Cash Flow": self.format_large_number(statement.investing_cash_flow, currency),
            "Financing Cash Flow": self.format_large_number(statement.financing_cash_flow, currency),
            "Free Cash Flow": self.format_large_number(statement.free_cash_flow, currency),
            "CapEx": self.format_large_number(statement.capital_expenditure, currency),
            "Net Income": self.format_large_number(statement.net_income, currency),
            "D&A": self.format_large_number(statement.depreciation_amortization, currency),
            "Stock Compensation": self.format_large_number(statement.stock_based_compensation, currency),
            "Dividends Paid": self.format_large_number(statement.dividends_paid, currency),
            "Stock Repurchased": self.format_large_number(statement.stock_repurchased, currency),
        }

    def format_income_statement_table(self, statements: list[IncomeStatement], currency: str = "$") -> str:
        """Format income statements as a multi-year table."""
        if not statements:
            return "No data available."

        # Define rows to display
        rows = [
            ("Revenue", lambda s: self.format_large_number(s.revenue, currency)),
            ("Cost of Revenue", lambda s: self.format_large_number(s.cost_of_revenue, currency)),
            ("Gross Profit", lambda s: self.format_large_number(s.gross_profit, currency)),
            ("Operating Expenses", lambda s: self.format_large_number(s.operating_expenses, currency)),
            ("Operating Income", lambda s: self.format_large_number(s.operating_income, currency)),
            ("Income Before Tax", lambda s: self.format_large_number(s.income_before_tax, currency)),
            ("Net Income", lambda s: self.format_large_number(s.net_income, currency)),
            ("", lambda s: ""),  # Spacer
            ("EPS", lambda s: self.format_currency(s.eps, currency)),
            ("EPS (Diluted)", lambda s: self.format_currency(s.eps_diluted, currency)),
            ("EBITDA", lambda s: self.format_large_number(s.ebitda, currency)),
        ]

        return self._format_statement_table(statements, rows)

    def format_balance_sheet_table(self, statements: list[BalanceSheet], currency: str = "$") -> str:
        """Format balance sheets as a multi-year table."""
        if not statements:
            return "No data available."

        rows = [
            ("[cyan]ASSETS[/cyan]", lambda s: ""),
            ("Cash & Equivalents", lambda s: self.format_large_number(s.cash_and_equivalents, currency)),
            ("Short-Term Investments", lambda s: self.format_large_number(s.short_term_investments, currency)),
            ("Net Receivables", lambda s: self.format_large_number(s.net_receivables, currency)),
            ("Inventory", lambda s: self.format_large_number(s.inventory, currency)),
            ("Total Current Assets", lambda s: self.format_large_number(s.total_current_assets, currency)),
            ("Property & Equipment", lambda s: self.format_large_number(s.property_plant_equipment, currency)),
            ("Total Non-Current Assets", lambda s: self.format_large_number(s.total_non_current_assets, currency)),
            ("Total Assets", lambda s: self.format_large_number(s.total_assets, currency)),
            ("", lambda s: ""),
            ("[cyan]LIABILITIES[/cyan]", lambda s: ""),
            ("Accounts Payable", lambda s: self.format_large_number(s.accounts_payable, currency)),
            ("Short-Term Debt", lambda s: self.format_large_number(s.short_term_debt, currency)),
            ("Total Current Liabilities", lambda s: self.format_large_number(s.total_current_liabilities, currency)),
            ("Long-Term Debt", lambda s: self.format_large_number(s.long_term_debt, currency)),
            ("Total Non-Current Liab.", lambda s: self.format_large_number(s.total_non_current_liabilities, currency)),
            ("Total Liabilities", lambda s: self.format_large_number(s.total_liabilities, currency)),
            ("", lambda s: ""),
            ("[cyan]EQUITY[/cyan]", lambda s: ""),
            ("Retained Earnings", lambda s: self.format_large_number(s.retained_earnings, currency)),
            ("Stockholders Equity", lambda s: self.format_large_number(s.total_stockholders_equity, currency)),
            ("", lambda s: ""),
            ("Total Debt", lambda s: self.format_large_number(s.total_debt, currency)),
            ("Net Debt", lambda s: self.format_large_number(s.net_debt, currency)),
        ]

        return self._format_statement_table(statements, rows)

    def format_cash_flow_table(self, statements: list[CashFlowStatement], currency: str = "$") -> str:
        """Format cash flow statements as a multi-year table."""
        if not statements:
            return "No data available."

        rows = [
            ("[cyan]OPERATING[/cyan]", lambda s: ""),
            ("Net Income", lambda s: self.format_large_number(s.net_income, currency)),
            ("D&A", lambda s: self.format_large_number(s.depreciation_amortization, currency)),
            ("Stock Compensation", lambda s: self.format_large_number(s.stock_based_compensation, currency)),
            ("Working Capital Chg", lambda s: self.format_large_number(s.change_in_working_capital, currency)),
            ("Operating Cash Flow", lambda s: self.format_large_number(s.operating_cash_flow, currency)),
            ("", lambda s: ""),
            ("[cyan]INVESTING[/cyan]", lambda s: ""),
            ("CapEx", lambda s: self.format_large_number(s.capital_expenditure, currency)),
            ("Acquisitions", lambda s: self.format_large_number(s.acquisitions, currency)),
            ("Investment Purchases", lambda s: self.format_large_number(s.purchases_of_investments, currency)),
            ("Investment Sales", lambda s: self.format_large_number(s.sales_of_investments, currency)),
            ("Investing Cash Flow", lambda s: self.format_large_number(s.investing_cash_flow, currency)),
            ("", lambda s: ""),
            ("[cyan]FINANCING[/cyan]", lambda s: ""),
            ("Debt Repayment", lambda s: self.format_large_number(s.debt_repayment, currency)),
            ("Stock Repurchased", lambda s: self.format_large_number(s.stock_repurchased, currency)),
            ("Dividends Paid", lambda s: self.format_large_number(s.dividends_paid, currency)),
            ("Financing Cash Flow", lambda s: self.format_large_number(s.financing_cash_flow, currency)),
            ("", lambda s: ""),
            ("Net Change in Cash", lambda s: self.format_large_number(s.net_change_in_cash, currency)),
            ("Free Cash Flow", lambda s: self.format_large_number(s.free_cash_flow, currency)),
        ]

        return self._format_statement_table(statements, rows)

    def _format_statement_table(self, statements: list, rows: list) -> str:
        """Format a financial statement table with multiple periods."""
        # Get column headers (fiscal years)
        headers = [s.fiscal_year or s.date[:4] for s in statements]
        col_width = 12
        label_width = 28

        # Build header row
        table = f"{'':.<{label_width}}"
        for header in headers:
            table += f"{header:>{col_width}}"
        table += "\n" + "=" * (label_width + col_width * len(headers)) + "\n"

        # Build data rows
        for label, value_fn in rows:
            if not label:  # Spacer row
                table += "\n"
                continue
            table += f"{label:.<{label_width}}"
            for statement in statements:
                value = value_fn(statement)
                table += f"{value:>{col_width}}"
            table += "\n"

        return table
