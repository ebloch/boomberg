"""Unit tests for financials service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import (
    BalanceSheet,
    CashFlowStatement,
    FinancialRatiosTTM,
    IncomeStatement,
    KeyMetricsTTM,
)
from boomberg.services.financials import FinancialsService


class TestFinancialsService:
    """Tests for FinancialsService."""

    @pytest.fixture
    def mock_client(self):
        """Create mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create financials service with mock client."""
        return FinancialsService(mock_client)

    @pytest.fixture
    def sample_ratios(self) -> FinancialRatiosTTM:
        """Sample financial ratios."""
        return FinancialRatiosTTM(
            symbol="AAPL",
            gross_profit_margin=0.45,
            operating_profit_margin=0.30,
            net_profit_margin=0.25,
            current_ratio=1.5,
            quick_ratio=1.2,
            cash_ratio=0.5,
            pe_ratio=25.0,
            peg_ratio=2.5,
            price_to_book=10.0,
            price_to_sales=5.0,
            debt_ratio=0.3,
            debt_to_equity=0.5,
            interest_coverage=15.0,
            dividend_yield=0.015,
            payout_ratio=0.25,
        )

    @pytest.fixture
    def sample_metrics(self) -> KeyMetricsTTM:
        """Sample key metrics."""
        return KeyMetricsTTM(
            symbol="AAPL",
            market_cap=2_500_000_000_000,
            enterprise_value=2_600_000_000_000,
            ev_to_sales=8.5,
            ev_to_ebitda=20.0,
            ev_to_free_cash_flow=25.0,
            net_debt_to_ebitda=0.5,
            roic=0.35,
            roe=1.5,
            roa=0.30,
            working_capital=-5_000_000_000,
            graham_number=50.0,
        )

    @pytest.fixture
    def sample_income(self) -> IncomeStatement:
        """Sample income statement."""
        return IncomeStatement(
            date="2024-09-30",
            symbol="AAPL",
            period="FY",
            fiscal_year="2024",
            revenue=400_000_000_000,
            gross_profit=180_000_000_000,
            operating_income=120_000_000_000,
            net_income=100_000_000_000,
            eps=6.50,
            eps_diluted=6.45,
            ebitda=130_000_000_000,
        )

    @pytest.mark.asyncio
    async def test_get_ratios(self, service, mock_client, sample_ratios):
        """Test getting financial ratios."""
        mock_client.get_financial_ratios_ttm = AsyncMock(return_value=sample_ratios)
        result = await service.get_ratios("AAPL")
        assert result.symbol == "AAPL"
        mock_client.get_financial_ratios_ttm.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_key_metrics(self, service, mock_client, sample_metrics):
        """Test getting key metrics."""
        mock_client.get_key_metrics_ttm = AsyncMock(return_value=sample_metrics)
        result = await service.get_key_metrics("AAPL")
        assert result.symbol == "AAPL"
        mock_client.get_key_metrics_ttm.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_income_statement(self, service, mock_client, sample_income):
        """Test getting income statement."""
        mock_client.get_income_statement = AsyncMock(return_value=[sample_income])
        result = await service.get_income_statement("AAPL", limit=1)
        assert len(result) == 1
        assert result[0].symbol == "AAPL"
        mock_client.get_income_statement.assert_called_once_with("AAPL", 1, "annual")

    def test_format_percent(self, service):
        """Test percentage formatting."""
        assert service.format_percent(0.25) == "25.00%"
        assert service.format_percent(0.123456) == "12.35%"
        assert service.format_percent(None) == "N/A"

    def test_format_ratio(self, service):
        """Test ratio formatting."""
        assert service.format_ratio(25.5) == "25.50"
        assert service.format_ratio(1.234567) == "1.23"
        assert service.format_ratio(None) == "N/A"

    def test_format_large_number_trillion(self, service):
        """Test formatting trillion values."""
        assert service.format_large_number(2_500_000_000_000) == "$2.50T"

    def test_format_large_number_billion(self, service):
        """Test formatting billion values."""
        assert service.format_large_number(150_000_000_000) == "$150.00B"

    def test_format_large_number_million(self, service):
        """Test formatting million values."""
        assert service.format_large_number(500_000_000) == "$500.00M"

    def test_format_large_number_thousand(self, service):
        """Test formatting thousand values."""
        assert service.format_large_number(50_000) == "$50.00K"

    def test_format_large_number_small(self, service):
        """Test formatting small values."""
        assert service.format_large_number(500) == "$500.00"

    def test_format_large_number_negative(self, service):
        """Test formatting negative values."""
        assert service.format_large_number(-5_000_000_000) == "-$5.00B"

    def test_format_large_number_none(self, service):
        """Test formatting None values."""
        assert service.format_large_number(None) == "N/A"

    def test_format_currency(self, service):
        """Test currency formatting."""
        assert service.format_currency(123.45) == "$123.45"
        assert service.format_currency(None) == "N/A"

    def test_format_large_number_with_yen(self, service):
        """Test formatting large numbers with yen symbol."""
        assert service.format_large_number(2_500_000_000_000, "¥") == "¥2.50T"
        assert service.format_large_number(150_000_000_000, "¥") == "¥150.00B"
        assert service.format_large_number(-5_000_000_000, "¥") == "-¥5.00B"

    def test_format_large_number_with_pound(self, service):
        """Test formatting large numbers with pound symbol."""
        assert service.format_large_number(500_000_000, "£") == "£500.00M"

    def test_format_large_number_with_euro(self, service):
        """Test formatting large numbers with euro symbol."""
        assert service.format_large_number(50_000, "€") == "€50.00K"

    def test_format_currency_with_yen(self, service):
        """Test currency formatting with yen symbol."""
        assert service.format_currency(3774.0, "¥") == "¥3774.00"

    def test_format_currency_with_pound(self, service):
        """Test currency formatting with pound symbol."""
        assert service.format_currency(114.15, "£") == "£114.15"

    def test_get_ratios_summary(self, service, sample_ratios):
        """Test getting ratios summary."""
        summary = service.get_ratios_summary(sample_ratios)
        assert summary["Gross Margin"] == "45.00%"
        assert summary["Operating Margin"] == "30.00%"
        assert summary["Net Margin"] == "25.00%"
        assert summary["Current Ratio"] == "1.50"
        assert summary["P/E Ratio"] == "25.00"

    def test_get_ratios_summary_with_metrics(self, service, sample_ratios, sample_metrics):
        """Test getting ratios summary with metrics for ROE/ROA."""
        summary = service.get_ratios_summary(sample_ratios, sample_metrics)
        # ROE and ROA should come from metrics
        assert summary["ROE"] == "150.00%"
        assert summary["ROA"] == "30.00%"

    def test_get_metrics_summary(self, service, sample_metrics):
        """Test getting metrics summary."""
        summary = service.get_metrics_summary(sample_metrics)
        assert summary["Market Cap"] == "$2.50T"
        assert summary["Enterprise Value"] == "$2.60T"
        assert summary["EV/Sales"] == "8.50"
        assert summary["EV/EBITDA"] == "20.00"
        assert summary["ROIC"] == "35.00%"

    def test_get_income_summary(self, service, sample_income):
        """Test getting income summary."""
        summary = service.get_income_summary(sample_income)
        assert summary["Period"] == "2024 (FY)"
        assert summary["Revenue"] == "$400.00B"
        assert summary["Net Income"] == "$100.00B"
        assert summary["EPS"] == "$6.50"

    @pytest.fixture
    def sample_balance_sheet(self) -> BalanceSheet:
        """Sample balance sheet."""
        return BalanceSheet(
            date="2024-09-30",
            symbol="AAPL",
            period="FY",
            fiscal_year="2024",
            total_assets=350_000_000_000,
            total_current_assets=140_000_000_000,
            cash_and_equivalents=30_000_000_000,
            short_term_investments=35_000_000_000,
            net_receivables=25_000_000_000,
            inventory=5_000_000_000,
            total_non_current_assets=210_000_000_000,
            property_plant_equipment=45_000_000_000,
            total_liabilities=280_000_000_000,
            total_current_liabilities=150_000_000_000,
            accounts_payable=60_000_000_000,
            short_term_debt=10_000_000_000,
            total_non_current_liabilities=130_000_000_000,
            long_term_debt=100_000_000_000,
            total_stockholders_equity=70_000_000_000,
            retained_earnings=5_000_000_000,
            total_debt=110_000_000_000,
            net_debt=80_000_000_000,
        )

    @pytest.fixture
    def sample_cash_flow(self) -> CashFlowStatement:
        """Sample cash flow statement."""
        return CashFlowStatement(
            date="2024-09-30",
            symbol="AAPL",
            period="FY",
            fiscal_year="2024",
            net_income=100_000_000_000,
            depreciation_amortization=12_000_000_000,
            stock_based_compensation=10_000_000_000,
            change_in_working_capital=-5_000_000_000,
            operating_cash_flow=115_000_000_000,
            capital_expenditure=-10_000_000_000,
            acquisitions=-500_000_000,
            purchases_of_investments=-40_000_000_000,
            sales_of_investments=50_000_000_000,
            investing_cash_flow=0,
            debt_repayment=-10_000_000_000,
            stock_repurchased=-80_000_000_000,
            dividends_paid=-15_000_000_000,
            financing_cash_flow=-105_000_000_000,
            net_change_in_cash=10_000_000_000,
            free_cash_flow=105_000_000_000,
        )

    @pytest.mark.asyncio
    async def test_get_balance_sheet(self, service, mock_client, sample_balance_sheet):
        """Test getting balance sheet."""
        mock_client.get_balance_sheet = AsyncMock(return_value=[sample_balance_sheet])
        result = await service.get_balance_sheet("AAPL", limit=1)
        assert len(result) == 1
        assert result[0].symbol == "AAPL"
        mock_client.get_balance_sheet.assert_called_once_with("AAPL", 1, "annual")

    @pytest.mark.asyncio
    async def test_get_cash_flow_statement(self, service, mock_client, sample_cash_flow):
        """Test getting cash flow statement."""
        mock_client.get_cash_flow_statement = AsyncMock(return_value=[sample_cash_flow])
        result = await service.get_cash_flow_statement("AAPL", limit=1)
        assert len(result) == 1
        assert result[0].symbol == "AAPL"
        mock_client.get_cash_flow_statement.assert_called_once_with("AAPL", 1, "annual")

    def test_get_balance_sheet_summary(self, service, sample_balance_sheet):
        """Test getting balance sheet summary."""
        summary = service.get_balance_sheet_summary(sample_balance_sheet)
        assert summary["Period"] == "2024 (FY)"
        assert summary["Total Assets"] == "$350.00B"
        assert summary["Total Liabilities"] == "$280.00B"
        assert summary["Stockholders Equity"] == "$70.00B"
        assert summary["Cash & Equivalents"] == "$30.00B"
        assert summary["Total Debt"] == "$110.00B"

    def test_get_cash_flow_summary(self, service, sample_cash_flow):
        """Test getting cash flow summary."""
        summary = service.get_cash_flow_summary(sample_cash_flow)
        assert summary["Period"] == "2024 (FY)"
        assert summary["Operating Cash Flow"] == "$115.00B"
        assert summary["Investing Cash Flow"] == "$0.00"
        assert summary["Financing Cash Flow"] == "-$105.00B"
        assert summary["Free Cash Flow"] == "$105.00B"
        assert summary["CapEx"] == "-$10.00B"

    def test_format_statement_table(self, service, sample_income):
        """Test formatting multiple statements as a table."""
        statements = [sample_income]
        table = service.format_income_statement_table(statements)
        assert "2024" in table
        assert "Revenue" in table
        assert "$400.00B" in table

    def test_format_balance_sheet_table(self, service, sample_balance_sheet):
        """Test formatting balance sheet as a table."""
        statements = [sample_balance_sheet]
        table = service.format_balance_sheet_table(statements)
        assert "2024" in table
        assert "Total Assets" in table
        assert "$350.00B" in table

    def test_format_cash_flow_table(self, service, sample_cash_flow):
        """Test formatting cash flow statement as a table."""
        statements = [sample_cash_flow]
        table = service.format_cash_flow_table(statements)
        assert "2024" in table
        assert "Operating Cash Flow" in table
        assert "$115.00B" in table
