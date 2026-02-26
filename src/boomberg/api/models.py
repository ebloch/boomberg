"""Pydantic models for FMP API responses."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Quote(BaseModel):
    """Real-time stock quote."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    name: str = ""
    price: float
    change: float = Field(default=0.0, alias="change")
    change_percent: float = Field(default=0.0, alias="changePercentage")
    day_low: float = Field(default=0.0, alias="dayLow")
    day_high: float = Field(default=0.0, alias="dayHigh")
    year_low: float = Field(default=0.0, alias="yearLow")
    year_high: float = Field(default=0.0, alias="yearHigh")
    market_cap: Optional[float] = Field(default=None, alias="marketCap")
    volume: float = Field(default=0.0)
    avg_volume: int = Field(default=0, alias="avgVolume")
    open: float = Field(default=0.0, alias="open")
    previous_close: float = Field(default=0.0, alias="previousClose")
    eps: Optional[float] = Field(default=None)
    pe: Optional[float] = Field(default=None)
    exchange: str = Field(default="")
    timestamp: Optional[datetime] = None


class HistoricalPrice(BaseModel):
    """Historical price data point."""

    model_config = ConfigDict(populate_by_name=True)

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    adj_close: Optional[float] = Field(default=None, alias="adjClose")


class CompanyProfile(BaseModel):
    """Company profile and fundamentals."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    company_name: str = Field(default="", alias="companyName")
    exchange: str = Field(default="")
    industry: str = Field(default="")
    sector: str = Field(default="")
    description: str = Field(default="")
    ceo: str = Field(default="")
    website: str = Field(default="")
    market_cap: Optional[float] = Field(default=None, alias="marketCap")
    price: float = Field(default=0.0)
    beta: Optional[float] = Field(default=None)
    vol_avg: Optional[int] = Field(default=None, alias="averageVolume")
    last_dividend: Optional[float] = Field(default=None, alias="lastDividend")
    dcf: Optional[float] = Field(default=None)
    country: str = Field(default="")
    city: str = Field(default="")
    employees: Optional[int] = Field(default=None, alias="fullTimeEmployees")
    ipo_date: Optional[str] = Field(default=None, alias="ipoDate")


class NewsArticle(BaseModel):
    """News article."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: Optional[str] = Field(default="")
    title: str
    text: Optional[str] = Field(default="")
    published_date: datetime = Field(alias="publishedDate")
    site: Optional[str] = Field(default="")
    url: Optional[str] = Field(default="")
    image: Optional[str] = Field(default="")


class SearchResult(BaseModel):
    """Symbol search result."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    name: str
    currency: str = Field(default="")
    exchange: str = Field(default="")  # Short exchange code
    exchange_full: str = Field(default="", alias="exchangeFullName")


class FinancialRatiosTTM(BaseModel):
    """Trailing twelve month financial ratios."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    # Profitability ratios
    gross_profit_margin: Optional[float] = Field(default=None, alias="grossProfitMarginTTM")
    operating_profit_margin: Optional[float] = Field(default=None, alias="operatingProfitMarginTTM")
    net_profit_margin: Optional[float] = Field(default=None, alias="netProfitMarginTTM")
    return_on_assets: Optional[float] = Field(default=None, alias="returnOnAssetsTTM")
    return_on_equity: Optional[float] = Field(default=None, alias="returnOnEquityTTM")
    # Liquidity ratios
    current_ratio: Optional[float] = Field(default=None, alias="currentRatioTTM")
    quick_ratio: Optional[float] = Field(default=None, alias="quickRatioTTM")
    cash_ratio: Optional[float] = Field(default=None, alias="cashRatioTTM")
    # Efficiency ratios
    inventory_turnover: Optional[float] = Field(default=None, alias="inventoryTurnoverTTM")
    receivables_turnover: Optional[float] = Field(default=None, alias="receivablesTurnoverTTM")
    asset_turnover: Optional[float] = Field(default=None, alias="assetTurnoverTTM")
    # Valuation ratios
    pe_ratio: Optional[float] = Field(default=None, alias="priceToEarningsRatioTTM")
    peg_ratio: Optional[float] = Field(default=None, alias="priceToEarningsGrowthRatioTTM")
    price_to_book: Optional[float] = Field(default=None, alias="priceToBookRatioTTM")
    price_to_sales: Optional[float] = Field(default=None, alias="priceToSalesRatioTTM")
    # Debt ratios
    debt_ratio: Optional[float] = Field(default=None, alias="debtRatioTTM")
    debt_to_equity: Optional[float] = Field(default=None, alias="debtEquityRatioTTM")
    interest_coverage: Optional[float] = Field(default=None, alias="interestCoverageTTM")
    # Dividend
    dividend_yield: Optional[float] = Field(default=None, alias="dividendYieldTTM")
    payout_ratio: Optional[float] = Field(default=None, alias="payoutRatioTTM")


class KeyMetricsTTM(BaseModel):
    """Trailing twelve month key metrics."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    market_cap: Optional[float] = Field(default=None, alias="marketCap")
    enterprise_value: Optional[float] = Field(default=None, alias="enterpriseValueTTM")
    ev_to_sales: Optional[float] = Field(default=None, alias="evToSalesTTM")
    ev_to_ebitda: Optional[float] = Field(default=None, alias="evToEBITDATTM")
    ev_to_operating_cash_flow: Optional[float] = Field(default=None, alias="evToOperatingCashFlowTTM")
    ev_to_free_cash_flow: Optional[float] = Field(default=None, alias="evToFreeCashFlowTTM")
    net_debt_to_ebitda: Optional[float] = Field(default=None, alias="netDebtToEBITDATTM")
    current_ratio: Optional[float] = Field(default=None, alias="currentRatioTTM")
    roe: Optional[float] = Field(default=None, alias="returnOnEquityTTM")
    roa: Optional[float] = Field(default=None, alias="returnOnAssetsTTM")
    roic: Optional[float] = Field(default=None, alias="returnOnInvestedCapitalTTM")
    revenue_per_share: Optional[float] = Field(default=None, alias="revenuePerShareTTM")
    book_value_per_share: Optional[float] = Field(default=None, alias="bookValuePerShareTTM")
    tangible_book_value_per_share: Optional[float] = Field(default=None, alias="tangibleBookValuePerShareTTM")
    free_cash_flow_per_share: Optional[float] = Field(default=None, alias="freeCashFlowPerShareTTM")
    working_capital: Optional[float] = Field(default=None, alias="workingCapitalTTM")
    invested_capital: Optional[float] = Field(default=None, alias="investedCapitalTTM")
    graham_number: Optional[float] = Field(default=None, alias="grahamNumberTTM")


class IncomeStatement(BaseModel):
    """Income statement data."""

    model_config = ConfigDict(populate_by_name=True)

    date: str
    symbol: str
    period: str = Field(default="")
    fiscal_year: Optional[str] = Field(default=None, alias="fiscalYear")
    revenue: Optional[float] = Field(default=None)
    cost_of_revenue: Optional[float] = Field(default=None, alias="costOfRevenue")
    gross_profit: Optional[float] = Field(default=None, alias="grossProfit")
    operating_expenses: Optional[float] = Field(default=None, alias="operatingExpenses")
    operating_income: Optional[float] = Field(default=None, alias="operatingIncome")
    income_before_tax: Optional[float] = Field(default=None, alias="incomeBeforeTax")
    net_income: Optional[float] = Field(default=None, alias="netIncome")
    eps: Optional[float] = Field(default=None)
    eps_diluted: Optional[float] = Field(default=None, alias="epsDiluted")
    ebitda: Optional[float] = Field(default=None)


class BalanceSheet(BaseModel):
    """Balance sheet data."""

    model_config = ConfigDict(populate_by_name=True)

    date: str
    symbol: str
    period: str = Field(default="")
    fiscal_year: Optional[str] = Field(default=None, alias="fiscalYear")
    # Assets
    total_assets: Optional[float] = Field(default=None, alias="totalAssets")
    total_current_assets: Optional[float] = Field(default=None, alias="totalCurrentAssets")
    cash_and_equivalents: Optional[float] = Field(default=None, alias="cashAndCashEquivalents")
    short_term_investments: Optional[float] = Field(default=None, alias="shortTermInvestments")
    net_receivables: Optional[float] = Field(default=None, alias="netReceivables")
    inventory: Optional[float] = Field(default=None)
    total_non_current_assets: Optional[float] = Field(default=None, alias="totalNonCurrentAssets")
    property_plant_equipment: Optional[float] = Field(default=None, alias="propertyPlantEquipmentNet")
    goodwill: Optional[float] = Field(default=None)
    intangible_assets: Optional[float] = Field(default=None, alias="intangibleAssets")
    # Liabilities
    total_liabilities: Optional[float] = Field(default=None, alias="totalLiabilities")
    total_current_liabilities: Optional[float] = Field(default=None, alias="totalCurrentLiabilities")
    accounts_payable: Optional[float] = Field(default=None, alias="accountPayables")
    short_term_debt: Optional[float] = Field(default=None, alias="shortTermDebt")
    total_non_current_liabilities: Optional[float] = Field(default=None, alias="totalNonCurrentLiabilities")
    long_term_debt: Optional[float] = Field(default=None, alias="longTermDebt")
    # Equity
    total_stockholders_equity: Optional[float] = Field(default=None, alias="totalStockholdersEquity")
    retained_earnings: Optional[float] = Field(default=None, alias="retainedEarnings")
    common_stock: Optional[float] = Field(default=None, alias="commonStock")
    # Calculated
    total_debt: Optional[float] = Field(default=None, alias="totalDebt")
    net_debt: Optional[float] = Field(default=None, alias="netDebt")


class CashFlowStatement(BaseModel):
    """Cash flow statement data."""

    model_config = ConfigDict(populate_by_name=True)

    date: str
    symbol: str
    period: str = Field(default="")
    fiscal_year: Optional[str] = Field(default=None, alias="fiscalYear")
    # Operating activities
    net_income: Optional[float] = Field(default=None, alias="netIncome")
    depreciation_amortization: Optional[float] = Field(default=None, alias="depreciationAndAmortization")
    stock_based_compensation: Optional[float] = Field(default=None, alias="stockBasedCompensation")
    change_in_working_capital: Optional[float] = Field(default=None, alias="changeInWorkingCapital")
    operating_cash_flow: Optional[float] = Field(default=None, alias="operatingCashFlow")
    # Investing activities
    capital_expenditure: Optional[float] = Field(default=None, alias="capitalExpenditure")
    acquisitions: Optional[float] = Field(default=None, alias="acquisitionsNet")
    purchases_of_investments: Optional[float] = Field(default=None, alias="purchasesOfInvestments")
    sales_of_investments: Optional[float] = Field(default=None, alias="salesMaturitiesOfInvestments")
    investing_cash_flow: Optional[float] = Field(default=None, alias="netCashProvidedByInvestingActivities")
    # Financing activities
    debt_repayment: Optional[float] = Field(default=None, alias="netDebtIssuance")
    stock_repurchased: Optional[float] = Field(default=None, alias="commonStockRepurchased")
    dividends_paid: Optional[float] = Field(default=None, alias="netDividendsPaid")
    financing_cash_flow: Optional[float] = Field(default=None, alias="netCashProvidedByFinancingActivities")
    # Net change
    net_change_in_cash: Optional[float] = Field(default=None, alias="netChangeInCash")
    free_cash_flow: Optional[float] = Field(default=None, alias="freeCashFlow")


class TreasuryRates(BaseModel):
    """Treasury rates for all maturities."""

    model_config = ConfigDict(populate_by_name=True)

    date: str
    month1: Optional[float] = Field(default=None, alias="month1")
    month3: Optional[float] = Field(default=None, alias="month3")
    month6: Optional[float] = Field(default=None, alias="month6")
    year1: Optional[float] = Field(default=None, alias="year1")
    year2: Optional[float] = Field(default=None, alias="year2")
    year5: Optional[float] = Field(default=None, alias="year5")
    year10: Optional[float] = Field(default=None, alias="year10")
    year30: Optional[float] = Field(default=None, alias="year30")


class ForexQuote(BaseModel):
    """Forex currency pair quote."""

    model_config = ConfigDict(populate_by_name=True)

    ticker: str
    bid: float = Field(default=0.0)
    ask: float = Field(default=0.0)
    open: float = Field(default=0.0)
    low: float = Field(default=0.0)
    high: float = Field(default=0.0)
    changes: float = Field(default=0.0)
    date: str = Field(default="")


class StockPriceChange(BaseModel):
    """Stock price change percentages over various time periods."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    one_day: Optional[float] = Field(default=None, alias="1D")
    five_day: Optional[float] = Field(default=None, alias="5D")
    one_month: Optional[float] = Field(default=None, alias="1M")
    three_month: Optional[float] = Field(default=None, alias="3M")
    six_month: Optional[float] = Field(default=None, alias="6M")
    ytd: Optional[float] = Field(default=None, alias="ytd")
    one_year: Optional[float] = Field(default=None, alias="1Y")
    three_year: Optional[float] = Field(default=None, alias="3Y")
    five_year: Optional[float] = Field(default=None, alias="5Y")
    ten_year: Optional[float] = Field(default=None, alias="10Y")
    max: Optional[float] = Field(default=None, alias="max")
