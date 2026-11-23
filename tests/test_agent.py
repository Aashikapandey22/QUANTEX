"""
Automated Tests for the Refactored 9-Stage QUANTEX AI Cognitive Architecture.
Validates:
- 10 required demonstration commands
- Intent classification across all 10 intent types
- Strict tool execution rules (greetings execute 0 tools, clarification asks without tools)
- Validated symbol extraction and invalid candidate rejection
- Multi-stock comparison tool orchestration
- Honest observation verification
- Grounded responses without fabricated data
"""
import pytest
from backend.agents.tool_agent import QuantexToolAgent
from backend.agents.tools import APPROVED_TOOLS

@pytest.fixture
def agent():
    return QuantexToolAgent()

def test_approved_tools_allowlist():
    required_tools = [
        "fetch_stock_data",
        "calculate_indicators",
        "generate_ml_prediction",
        "explain_stock_analysis",
        "run_backtest",
        "get_portfolio",
        "calculate_risk_metrics",
        "get_transaction_history",
        "get_market_overview"
    ]
    for t in required_tools:
        assert t in APPROVED_TOOLS

def test_agent_act_phase_security(agent):
    malicious_call = [{"name": "execute_arbitrary_shell", "args": {"cmd": "rm -rf"}}]
    results = agent.act(malicious_call)
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "not in approved tool registry" in results[0]["error"]

# ==================== 10 DEMO COMMAND TESTS ====================

def test_cmd_1_greeting_hello(agent):
    """CMD 1: 'hello' -> Intent GREETING, 0 stock tools executed."""
    res = agent.run("hello")
    p = res["pipeline"]
    assert p["intent"] == "GREETING"
    assert p["act"] == []
    assert len(p["entities"]["valid_symbols"]) == 0
    assert "QUANTEX" in res["response"]
    assert "What I Can Do For You" in res["response"]

def test_cmd_2_what_can_you_do(agent):
    """CMD 2: 'What can you do?' -> Intent GENERAL_QUESTION, 0 stock tools executed."""
    res = agent.run("What can you do?")
    p = res["pipeline"]
    assert p["intent"] == "GENERAL_QUESTION"
    assert p["act"] == []
    assert "QUANTEX Platform Capabilities & Architecture" in res["response"]

def test_cmd_3_should_i_invest_clarification(agent):
    """CMD 3: 'Should I invest?' -> Intent INVESTMENT_QUESTION, 0 tools, asks clarification."""
    res = agent.run("Should I invest?")
    p = res["pipeline"]
    assert p["intent"] == "INVESTMENT_QUESTION"
    assert p["act"] == []
    assert len(p["entities"]["valid_symbols"]) == 0
    assert "Investment Decision Clarification" in res["response"]
    assert "Which specific stock would you like me to analyze" in res["response"]
    assert "SHOULD" not in p["entities"]["valid_symbols"]

def test_cmd_4_analyse_tcs(agent):
    """CMD 4: 'Analyse TCS' -> Intent STOCK_ANALYSIS, executes explain_stock_analysis for TCS.NS."""
    res = agent.run("Analyse TCS")
    p = res["pipeline"]
    assert p["intent"] == "STOCK_ANALYSIS"
    assert p["entities"]["valid_symbols"] == ["TCS.NS"]
    assert len(p["act"]) == 1
    assert p["act"][0]["tool"] == "explain_stock_analysis"
    assert p["verification_status"] == "VERIFIED"
    assert "TCS.NS" in res["response"]
    assert "Price Action" in res["response"]
    assert "Technical Evidence" in res["response"]

def test_cmd_5_predict_reliance(agent):
    """CMD 5: 'Predict RELIANCE for 5 trading days' -> Intent PREDICTION, executes generate_ml_prediction."""
    res = agent.run("Predict RELIANCE for 5 trading days")
    p = res["pipeline"]
    assert p["intent"] == "PREDICTION"
    assert "RELIANCE.NS" in p["entities"]["valid_symbols"]
    assert len(p["act"]) == 1
    assert p["act"][0]["tool"] == "generate_ml_prediction"
    assert "5-Day Horizon" in res["response"]
    assert "RELIANCE.NS" in res["response"]

def test_cmd_6_explain_rsi_infy(agent):
    """CMD 6: 'Explain RSI of INFY' -> Intent INDICATOR_EXPLANATION, executes calculate_indicators."""
    res = agent.run("Explain RSI of INFY")
    p = res["pipeline"]
    assert p["intent"] == "INDICATOR_EXPLANATION"
    assert p["entities"]["valid_symbols"] == ["INFY.NS"]
    assert len(p["act"]) == 1
    assert p["act"][0]["tool"] == "calculate_indicators"
    assert "Relative Strength Index" in res["response"] or "RSI" in res["response"]
    assert "INFY.NS" in res["response"]

def test_cmd_7_compare_tcs_and_infy(agent):
    """CMD 7: 'Compare TCS and INFY' -> Intent COMPARISON, executes tools for both equities."""
    res = agent.run("Compare TCS and INFY")
    p = res["pipeline"]
    assert p["intent"] == "COMPARISON"
    assert set(p["entities"]["valid_symbols"]) == {"TCS.NS", "INFY.NS"}
    assert len(p["act"]) == 2
    assert all(a["tool"] == "explain_stock_analysis" for a in p["act"])
    assert "TCS.NS vs INFY.NS" in res["response"]

def test_cmd_8_backtest_moving_average(agent):
    """CMD 8: 'Backtest the moving average strategy' -> Intent BACKTEST, executes run_backtest."""
    res = agent.run("Backtest the moving average strategy")
    p = res["pipeline"]
    assert p["intent"] == "BACKTEST"
    assert len(p["act"]) == 1
    assert p["act"][0]["tool"] == "run_backtest"
    assert "Moving Average Crossover" in res["response"]
    assert "Strategy Return" in res["response"]

def test_cmd_9_show_portfolio(agent):
    """CMD 9: 'Show my paper trading portfolio' -> Intent PORTFOLIO, executes get_portfolio and calculate_risk_metrics."""
    res = agent.run("Show my paper trading portfolio")
    p = res["pipeline"]
    assert p["intent"] == "PORTFOLIO"
    assert any(a["tool"] == "get_portfolio" for a in p["act"])
    assert any(a["tool"] == "calculate_risk_metrics" for a in p["act"])
    assert "Virtual Paper Trading Portfolio Summary" in res["response"]
    assert "Available Virtual Cash" in res["response"]

def test_cmd_10_analyse_invalid_symbol(agent):
    """CMD 10: 'Analyse INVALIDXYZ' -> Rejected cleanly without executing stock tools or fabricating data."""
    res = agent.run("Analyse INVALIDXYZ")
    p = res["pipeline"]
    assert p["act"] == []
    assert "INVALIDXYZ" in p["entities"]["invalid_symbols"]
    assert len(p["entities"]["valid_symbols"]) == 0
    assert "Unsupported Instrument Symbol: `INVALIDXYZ`" in res["response"]
    assert "RELIANCE.NS" in res["response"]

# ==================== ADDITIONAL REGRESSION TESTS ====================

def test_regression_should_i_buy_tcs(agent):
    res = agent.run("Should I buy TCS?")
    assert res["pipeline"]["intent"] == "INVESTMENT_QUESTION"
    assert res["pipeline"]["entities"]["valid_symbols"] == ["TCS.NS"]
    assert len(res["pipeline"]["act"]) == 1
    assert res["pipeline"]["act"][0]["tool"] == "explain_stock_analysis"

def test_regression_ordinary_words_not_tickers(agent):
    assert agent.extract_entities("Can I trade tomorrow?") == []
    assert agent.extract_entities("What will happen to the market?") == []
    assert agent.extract_entities("Should we buy or sell?") == []
