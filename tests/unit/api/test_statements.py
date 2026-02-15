"""Unit tests for financial statement API methods."""

import pytest
import respx
from httpx import Response

from boomberg.api.client import FMPClient
from boomberg.api.models import (
    BalanceSheet,
    CashFlowStatement,
    IncomeStatement,
)


class TestFinancialStatements:
    """Tests for financial statement API methods."""

    @pytest.fixture
    def client(self, test_settings):
        """Create FMP client with test settings."""
        return FMPClient(settings=test_settings)

    @pytest.fixture
    def sample_income_statement_data(self) -> list[dict]:
        """Sample income statement API response."""
        return [
            {
                "date": "2024-09-30",
                "symbol": "AAPL",
                "period": "FY",
                "fiscalYear": "2024",
                "revenue": 400000000000,
                "costOfRevenue": 220000000000,
                "grossProfit": 180000000000,
                "operatingExpenses": 60000000000,
                "operatingIncome": 120000000000,
                "incomeBeforeTax": 125000000000,
                "netIncome": 100000000000,
                "eps": 6.50,
                "epsDiluted": 6.45,
                "ebitda": 130000000000,
            },
            {
                "date": "2023-09-30",
                "symbol": "AAPL",
                "period": "FY",
                "fiscalYear": "2023",
                "revenue": 380000000000,
                "costOfRevenue": 210000000000,
                "grossProfit": 170000000000,
                "operatingExpenses": 55000000000,
                "operatingIncome": 115000000000,
                "incomeBeforeTax": 118000000000,
                "netIncome": 95000000000,
                "eps": 6.10,
                "epsDiluted": 6.05,
                "ebitda": 125000000000,
            },
        ]

    @pytest.fixture
    def sample_balance_sheet_data(self) -> list[dict]:
        """Sample balance sheet API response."""
        return [
            {
                "date": "2024-09-30",
                "symbol": "AAPL",
                "period": "FY",
                "fiscalYear": "2024",
                "totalAssets": 350000000000,
                "totalCurrentAssets": 140000000000,
                "cashAndCashEquivalents": 30000000000,
                "shortTermInvestments": 35000000000,
                "netReceivables": 25000000000,
                "inventory": 5000000000,
                "totalNonCurrentAssets": 210000000000,
                "propertyPlantEquipmentNet": 45000000000,
                "goodwill": 0,
                "intangibleAssets": 0,
                "totalLiabilities": 280000000000,
                "totalCurrentLiabilities": 150000000000,
                "accountPayables": 60000000000,
                "shortTermDebt": 10000000000,
                "totalNonCurrentLiabilities": 130000000000,
                "longTermDebt": 100000000000,
                "totalStockholdersEquity": 70000000000,
                "retainedEarnings": 5000000000,
                "commonStock": 65000000000,
                "totalDebt": 110000000000,
                "netDebt": 80000000000,
            },
        ]

    @pytest.fixture
    def sample_cash_flow_data(self) -> list[dict]:
        """Sample cash flow statement API response."""
        return [
            {
                "date": "2024-09-30",
                "symbol": "AAPL",
                "period": "FY",
                "fiscalYear": "2024",
                "netIncome": 100000000000,
                "depreciationAndAmortization": 12000000000,
                "stockBasedCompensation": 10000000000,
                "changeInWorkingCapital": -5000000000,
                "operatingCashFlow": 115000000000,
                "capitalExpenditure": -10000000000,
                "investmentsInPropertyPlantAndEquipment": -10000000000,
                "acquisitionsNet": 0,
                "purchasesOfInvestments": -40000000000,
                "salesMaturitiesOfInvestments": 50000000000,
                "investingCashFlow": 0,
                "debtRepayment": -10000000000,
                "commonStockRepurchased": -80000000000,
                "dividendsPaid": -15000000000,
                "financingCashFlow": -105000000000,
                "netChangeInCash": 10000000000,
                "freeCashFlow": 105000000000,
            },
        ]

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_income_statement(self, client, sample_income_statement_data):
        """Test income statement retrieval."""
        respx.get(
            "https://financialmodelingprep.com/stable/income-statement"
        ).mock(return_value=Response(200, json=sample_income_statement_data))

        async with client:
            statements = await client.get_income_statement("AAPL", limit=2)

        assert len(statements) == 2
        assert all(isinstance(s, IncomeStatement) for s in statements)
        assert statements[0].revenue == 400000000000
        assert statements[0].net_income == 100000000000

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_income_statement_quarterly(self, client, sample_income_statement_data):
        """Test quarterly income statement retrieval."""
        quarterly_data = [{**sample_income_statement_data[0], "period": "Q4"}]
        respx.get(
            "https://financialmodelingprep.com/stable/income-statement"
        ).mock(return_value=Response(200, json=quarterly_data))

        async with client:
            statements = await client.get_income_statement("AAPL", limit=4, period="quarter")

        assert len(statements) == 1
        assert statements[0].period == "Q4"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_balance_sheet(self, client, sample_balance_sheet_data):
        """Test balance sheet retrieval."""
        respx.get(
            "https://financialmodelingprep.com/stable/balance-sheet-statement"
        ).mock(return_value=Response(200, json=sample_balance_sheet_data))

        async with client:
            statements = await client.get_balance_sheet("AAPL", limit=1)

        assert len(statements) == 1
        assert isinstance(statements[0], BalanceSheet)
        assert statements[0].total_assets == 350000000000
        assert statements[0].total_liabilities == 280000000000
        assert statements[0].total_stockholders_equity == 70000000000

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_balance_sheet_quarterly(self, client, sample_balance_sheet_data):
        """Test quarterly balance sheet retrieval."""
        quarterly_data = [{**sample_balance_sheet_data[0], "period": "Q4"}]
        respx.get(
            "https://financialmodelingprep.com/stable/balance-sheet-statement"
        ).mock(return_value=Response(200, json=quarterly_data))

        async with client:
            statements = await client.get_balance_sheet("AAPL", limit=4, period="quarter")

        assert len(statements) == 1
        assert statements[0].period == "Q4"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_cash_flow_statement(self, client, sample_cash_flow_data):
        """Test cash flow statement retrieval."""
        respx.get(
            "https://financialmodelingprep.com/stable/cash-flow-statement"
        ).mock(return_value=Response(200, json=sample_cash_flow_data))

        async with client:
            statements = await client.get_cash_flow_statement("AAPL", limit=1)

        assert len(statements) == 1
        assert isinstance(statements[0], CashFlowStatement)
        assert statements[0].operating_cash_flow == 115000000000
        assert statements[0].free_cash_flow == 105000000000

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_cash_flow_statement_quarterly(self, client, sample_cash_flow_data):
        """Test quarterly cash flow statement retrieval."""
        quarterly_data = [{**sample_cash_flow_data[0], "period": "Q4"}]
        respx.get(
            "https://financialmodelingprep.com/stable/cash-flow-statement"
        ).mock(return_value=Response(200, json=quarterly_data))

        async with client:
            statements = await client.get_cash_flow_statement("AAPL", limit=4, period="quarter")

        assert len(statements) == 1
        assert statements[0].period == "Q4"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_income_statement_empty(self, client):
        """Test income statement with no data."""
        respx.get(
            "https://financialmodelingprep.com/stable/income-statement"
        ).mock(return_value=Response(200, json=[]))

        async with client:
            statements = await client.get_income_statement("INVALID", limit=4)

        assert statements == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_balance_sheet_empty(self, client):
        """Test balance sheet with no data."""
        respx.get(
            "https://financialmodelingprep.com/stable/balance-sheet-statement"
        ).mock(return_value=Response(200, json=[]))

        async with client:
            statements = await client.get_balance_sheet("INVALID", limit=4)

        assert statements == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_cash_flow_statement_empty(self, client):
        """Test cash flow statement with no data."""
        respx.get(
            "https://financialmodelingprep.com/stable/cash-flow-statement"
        ).mock(return_value=Response(200, json=[]))

        async with client:
            statements = await client.get_cash_flow_statement("INVALID", limit=4)

        assert statements == []
