<!-- L0: Лог инцидентов — root cause analysis, фиксы, append-only -->
# Incident Log

Автоматический и ручной лог инцидентов. Агент аппендит сюда после каждого root cause analysis.

## Формат записи

```
### INC-YYYY-MM-DD-N: краткое описание
- **Severity**: low | medium | high | critical
- **Tool/Area**: какой тул или область задели
- **Symptom**: что пошло не так (ошибка, поведение)
- **Root Cause**: почему (5 Почему если нужно)
- **Fix**: что сделали
- **Design Injection**: что поменяли в стандартах/скиллах/хуках чтобы не повторилось
- **Status**: fixed | mitigated | open
```

---

## 2026-03

### INC-2026-03-12-1: EAN override — неверный id_name для Азитромицина
- **Severity**: medium
- **Tool/Area**: PharmOrder VPS (db.py)
- **Symptom**: EAN 4670033321227 показывал Цетиризин вместо Азитромицина
- **Root Cause**: pr_all.dbf содержит 50 конфликтных EAN из 63K (0.1%) — разные товары с одним штрихкодом у разных поставщиков
- **Fix**: ean_overrides.json + apply_ean_overrides() в db.py
- **Design Injection**: добавлен механизм ручных override-ов, применяется автоматически после каждого sync
- **Status**: fixed

### INC-2026-03-12-2: tg-pharma 409 Conflict
- **Severity**: high
- **Tool/Area**: tg-pharma (main.py)
- **Symptom**: бот не стартовал — 409 Conflict на getUpdates
- **Root Cause**: второй процесс polling с тем же токеном
- **Fix**: отдельный бот-токен @pharmorder_ops_bot
- **Design Injection**: документировано в memory — один токен = один poller
- **Status**: fixed

### INC-2026-03-16-1: Дайджест heartbeat — мусор в выдаче
- **Severity**: medium
- **Tool/Area**: tg-monitor (daily.py)
- **Symptom**: Roblox-кликер, trump-code в дайджесте — нерелевантный шум
- **Root Cause**: нет персонального фильтра, heartbeat берёт top по метрикам без оценки релевантности
- **Fix**: PERSONAL_INTEREST_KEYWORDS + PERSONAL_BLOCKLIST + _filter_relevant_signals()
- **Design Injection**: фильтр интегрирован в pipeline, 23→11 сигналов
- **Status**: fixed

### INC-2026-03-16-2: NLM заменял heartbeat вместо дополнения
- **Severity**: low
- **Tool/Area**: tg-monitor (daily.py)
- **Symptom**: при успешном NLM deep research heartbeat section пропадал из дайджеста
- **Root Cause**: логика сборки: if NLM → skip heartbeat. Heartbeat с фильтром и описаниями никогда не показывался
- **Fix**: heartbeat всегда первый, NLM аппендится после
- **Design Injection**: parts.append(heartbeat) вынесен перед NLM блоком
- **Status**: fixed
