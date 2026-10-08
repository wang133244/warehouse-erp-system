"""无 Key 回退关键词；plan_turn 用 mock。"""

from backend.app.agents.graph import classify_intent  # from backend.app.agents.
from backend.app.agents.llm import classify_intent_llm, llm_enabled, llm_provider, plan_turn, polish_answer  # from backend.app.agents.
from backend.app.core.config import get_settings  # from backend.app.core.co


def test_llm_is_disabled_without_api_key(monkeypatch):  # def test_llm_is_disabled
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")  # monkeypatch.setenv('DEEP
    get_settings.cache_clear()  # get_settings.cache_clear
    assert llm_enabled() is False  # assert llm_enabled() is 
    assert llm_provider() == "none"  # assert llm_provider() ==
    assert classify_intent_llm("查询库存") is None  # assert classify_intent_l
    assert plan_turn("这个还有多少") is None  # assert plan_turn('这个还有多少
    assert polish_answer("查询库存", "可用 4", ["query_inventory"]) is None  # assert polish_answer('查询
    get_settings.cache_clear()  # get_settings.cache_clear


def test_keyword_intent_still_works_when_llm_disabled(monkeypatch):  # def test_keyword_intent_
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")  # monkeypatch.setenv('DEEP
    get_settings.cache_clear()  # get_settings.cache_clear
    assert classify_intent("请给出 SKU 的 ABC 分类") == "analysis"  # assert classify_intent('
    assert classify_intent("查询 SKU-1 的可用库存") == "inventory"  # assert classify_intent('
    assert classify_intent("生成入库单草稿 SKU-1 库位 A-01 数量 2") == "draft"  # assert classify_intent('
    get_settings.cache_clear()  # get_settings.cache_clear


def test_llm_intent_and_polish_use_deepseek_when_configured(monkeypatch):  # def test_llm_intent_and_
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-real")  # monkeypatch.setenv('DEEP
    get_settings.cache_clear()  # get_settings.cache_clear
    assert llm_enabled() is True  # assert llm_enabled() is 
    assert llm_provider() == "deepseek"  # assert llm_provider() ==

    monkeypatch.setattr(  # monkeypatch.setattr(
        "backend.app.agents.llm.complete_chat",  # 'backend.app.agents.llm.
        lambda messages, **kwargs: '{"intent":"analysis"}'  # lambda messages, **kwarg
        if "意图分类器" in messages[0]["content"]  # if '意图分类器' in messages[0
        else "根据报表，SKU-1 属于 A 类。助手没有改库存。",  # else '根据报表，SKU-1 属于 A 类。
    )  # )
    assert classify_intent_llm("帮我看看分类情况") == "analysis"  # assert classify_intent_l
    polished = polish_answer("分类", "SKU-1=A", ["query_abc_report"])  # polished = polish_answer
    assert polished is not None  # assert polished is not N
    assert "库存" in polished or "A" in polished  # assert '库存' in polished 

    captured: list[list[dict[str, str]]] = []  # captured: list[list[dict

    def fake_complete(messages, **kwargs):  # def fake_complete(messag
        captured.append(messages)  # captured.append(messages
        return "继续说明库存。"  # return '继续说明库存。'

    monkeypatch.setattr("backend.app.agents.llm.complete_chat", fake_complete)  # monkeypatch.setattr('bac
    polish_answer(  # polish_answer(
        "那可用量呢",  # '那可用量呢',
        "可用 4",  # '可用 4',
        ["query_inventory"],  # ['query_inventory'],
        history=[{"role": "user", "content": "查询 SKU-1"}, {"role": "assistant", "content": "库位 A-01 有货"}],  # history=[{'role': 'user'
    )  # )
    blob = " ".join(item["content"] for item in captured[0])  # blob = ' '.join(item['co
    assert "查询 SKU-1" in blob  # assert '查询 SKU-1' in blo
    get_settings.cache_clear()  # get_settings.cache_clear


def test_plan_turn_reads_history_and_slots(monkeypatch):  # def test_plan_turn_reads
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-real")  # monkeypatch.setenv('DEEP
    get_settings.cache_clear()  # get_settings.cache_clear
    captured: list[list[dict[str, str]]] = []  # captured: list[list[dict

    def fake_complete(messages, **kwargs):  # def fake_complete(messag
        captured.append(messages)  # captured.append(messages
        return (  # return (
            '{"intent":"inventory","sku_code":null,"location_code":null,'  # '{'intent':'inventory','
            '"quantity":null,"report":null,"draft_type":null,"use_history_sku":true}'  # ''quantity':null,'report
        )  # )

    monkeypatch.setattr("backend.app.agents.llm.complete_chat", fake_complete)  # monkeypatch.setattr('bac
    plan = plan_turn(  # plan = plan_turn(
        "这个还有多少",  # '这个还有多少',
        history=[{"role": "user", "content": "查询 SKU-1"}, {"role": "assistant", "content": "库位 A-01 可用 4"}],  # history=[{'role': 'user'
    )  # )
    assert plan is not None  # assert plan is not None
    assert plan["intent"] == "inventory"  # assert plan['intent'] ==
    assert plan["use_history_sku"] is True  # assert plan['use_history
    blob = " ".join(item["content"] for item in captured[0])  # blob = ' '.join(item['co
    assert "SKU-1" in blob  # assert 'SKU-1' in blob
    assert "这个还有多少" in blob  # assert '这个还有多少' in blob
    get_settings.cache_clear()  # get_settings.cache_clear
