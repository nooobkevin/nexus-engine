# 通用文字 TRPG 框架：實施計劃

## 項目概況

- **項目名稱**: Nexus Engine
- **類型**: 通用文字 TRPG 框架 / 互動敘事引擎
- **核心技術棧**: Python 3.11+ / Pydantic v2 / asyncio / SQLite (開發) / PostgreSQL (生產)
- **可選 LLM 適配**: OpenAI GPT-4 / Claude 3 / Local LLMs (via LiteLLM)

---

## 階段劃分總覽

| 階段 | 名稱 | 預計規模 | 依賴 |
|------|------|----------|------|
| Phase 0 | 項目基建 | 1-2 天 | - |
| Phase 1 | 核心資料模型 | 2-3 天 | Phase 0 |
| Phase 2 | 事件存儲與投影 | 3-4 天 | Phase 1 |
| Phase 3 | 規則引擎 | 3-4 天 | Phase 2 |
| Phase 4 | 驗證層 | 2-3 天 | Phase 3 |
| Phase 5 | LLM 工具面 | 3-4 天 | Phase 4 |
| Phase 6 | NPC 行為系統 | 4-5 天 | Phase 5 |
| Phase 7 | 世界模擬器 | 3-4 天 | Phase 6 |
| Phase 8 | 結晶化機制 | 2-3 天 | Phase 7 |
| Phase 9 | Setting Pack 系統 | 3-4 天 | Phase 8 |
| Phase 10 | 敘事生成流水線 | 3-4 天 | Phase 9 |
| Phase 11 | 整合測試與迭代 | 持續 | 所有階段 |

**總計**: 約 30-40 個工作日（6-8 週）

---

## Phase 0：項目基建

### 0.1 專案初始化

```
text-rpg-framework/
├── src/nexus_engine/              # 核心引擎包
│   ├── __init__.py
│   ├── core/                  # 核心資料模型
│   │   ├── __init__.py
│   │   ├── entity.py          # Entity, EntityRef, Observation
│   │   ├── event.py           # Event, StateChange, EventId
│   │   ├── ability.py         # Ability, Rule, Predicate
│   │   └── value_objects.py   # GameTime, EntityId, Tag, etc.
│   ├── store/                 # 事件存儲
│   │   ├── __init__.py
│   │   ├── event_store.py     # EventStore 介面與實現
│   │   └── snapshot_store.py  # 狀態快照存儲
│   ├── projection/            # 狀態投影
│   │   ├── __init__.py
│   │   ├── state_view.py      # StateView 實現
│   │   └── entity_projector.py # 實體投影器
│   ├── rules/                 # 規則引擎
│   │   ├── __init__.py
│   │   ├── rule_engine.py     # 規則匹配與執行
│   │   ├── resolvers.py       # 具體 resolver 實現
│   │   └── predicates.py      # 條件謂詞
│   ├── validation/            # 驗證層
│   │   ├── __init__.py
│   │   ├── validator.py       # 主驗證器
│   │   ├── rulings.py         # RulingDraft 驗證
│   │   └── canon.py           # Canon 事實驗證
│   ├── memory/                # 記憶系統
│   │   ├── __init__.py
│   │   ├── memory_system.py   # MemorySystem 實現
│   │   ├── canon_store.py     # CanonStore 實現
│   │   └── semantic_index.py  # 向量檢索 (可選前期用 BM25)
│   ├── agents/                # LLM Agent 工具面
│   │   ├── __init__.py
│   │   ├── tools.py           # AgentTools 定義
│   │   ├── context_builder.py # 上下文索引構建
│   │   └── llm_interface.py   # LLM 適配層
│   ├── world/                 # 世界模擬
│   │   ├── __init__.py
│   │   ├── world_simulator.py # WorldSimulator
│   │   ├── region.py          # 區域劃分與模擬
│   │   └── director.py        # Director 敘事規劃
│   ├── npc/                   # NPC 行為系統
│   │   ├── __init__.py
│   │   ├── npc.py             # NPC 實體
│   │   ├── drives.py          # Drive 系統
│   │   ├── goals.py           # Goal 與 Planner
│   │   └── ensemble.py        # 群體場景處理
│   ├── crystallization/       # 結晶化機制
│   │   ├── __init__.py
│   │   ├── crystallizer.py    # 觀察與提取
│   │   └── pattern.py         # 模式泛化
│   ├── setting/               # Setting Pack
│   │   ├── __init__.py
│   │   ├── setting_pack.py    # SettingPack 加載與驗證
│   │   ├── archetypes.py     # 原型定義
│   │   ├── power_systems.py   # 力量體系
│   │   └── vocabulary.py      # 受控詞彙表
│   └── narrative/            # 敘事生成
│       ├── __init__.py
│       ├── pipeline.py        # process_player_action 流水線
│       └── templates.py       # 敘事模板
├── tests/                     # 測試
│   ├── unit/
│   ├── integration/
│   └── fixtures/              # 測試用 Setting Pack
├── examples/                  # 示例
│   └── minimal_example.py
├── pyproject.toml
├── README.md
└── AGENTS.md                  # 代理指令（本文檔）
```

### 0.2 依賴管理

使用 `uv` 管理依賴，避免直接寫入 pyproject.toml：

```bash
# 添加依賴（代替直接編輯 pyproject.toml）
uv add pydantic pydantic-settings sqlalchemy aiosqlite httpx litellm ruff pytest pytest-asyncio
uv add --dev pytest-cov pre-commit

# 查看已解析的依賴
uv pip tree
```

### 0.3 驗收標準

- [ ] `pytest` 能發現並運行所有測試
- [ ] `ruff check` 無錯誤
- [ ] `ty check .` 無錯誤
- [ ] 專案可作為 uv 包安裝 (`uv pip install -e .`)

---

## Phase 1：核心資料模型

### 1.1 價值對象 (Value Objects)

**檔案**: `src/nexus_engine/core/value_objects.py`

```python
@dataclass(frozen=True, order=True)
class GameTime:
    """遊戲內時間，不可變"""
    ticks: int  # 從遊戲開始的 tick 數
    
@dataclass(frozen=True)
class EntityId:
    """全局唯一實體 ID"""
    uuid: UUID
    
@dataclass(frozen=True)
class EventId:
    """事件 ID"""
    uuid: UUID

@dataclass(frozen=True)
class Tag:
    """受控詞彙表的標籤"""
    namespace: str
    value: str
    
    def __str__(self) -> str:
        return f"{self.namespace}:{self.value}"

@dataclass(frozen=True)
class EntityRef:
    """實體引用（可在事件提交前存在）"""
    id: EntityId
    
@dataclass(frozen=True)
class SourceRef:
    """觀察來源"""
    source_type: Literal["event", "npc", "player", "setting_pack"]
    ref_id: str
    quote: str | None = None
```

### 1.2 實體模型 (Entity)

**檔案**: `src/nexus_engine/core/entity.py`

```python
class Observation(NamedTuple):
    """非結構化觀察"""
    content: str
    source: SourceRef
    confidence: float  # 0.0 - 1.0
    timestamp: GameTime

class Entity(pydantic.BaseModel):
    """基礎實體"""
    id: EntityId
    archetype: ArchetypeId
    tags: FrozenSet[Tag] = FrozenSet()
    properties: Dict[str, Any] = Field(default_factory=dict)
    observations: List[Observation] = Field(default_factory=list)
    created_at: GameTime
    canon_locked: bool = False
    
    model_config = {"frozen": True}  # 不可變
```

### 1.3 事件模型 (Event)

**檔案**: `src/nexus_engine/core/event.py`

```python
class Operation(str, Enum):
    SET = "SET"
    DELTA = "DELTA"
    APPEND = "APPEND"
    REMOVE = "REMOVE"

class StateChange(pydantic.BaseModel):
    """狀態變更"""
    target: EntityRef
    path: str                    # e.g. "properties.hp"
    operation: Operation
    value: Any

class MechanicsResult(pydantic.BaseModel):
    """純數值結果（由規則引擎產生）"""
    success: bool
    degree: float               # 成功程度 0.0-1.0
    values: Dict[str, Any] = Field(default_factory=dict)

class Event(pydantic.BaseModel):
    """不可變事件"""
    id: EventId
    game_time: GameTime
    type: EventType             # 枚舉：ACTION, PERCEPTION, NARRATIVE, etc.
    actor: EntityRef | None
    targets: List[EntityRef]
    location: EntityRef
    
    mechanics: MechanicsResult
    effects: List[StateChange]
    witnesses: List[EntityRef]
    
    narrative_summary: str       # ≤150 字
    narrative_full: str | None
    
    parent_event: EventId | None
    canon: bool = False
    
    model_config = {"frozen": True}
```

### 1.4 能力與規則 (Ability, Rule)

**檔案**: `src/nexus_engine/core/ability.py`

```python
class TierLevel(int):
    """能力階層枚舉"""
    MUNDANE = 0
    HEROIC = 1
    LEGENDARY = 2
    MYTHIC = 3
    DIVINE = 4

@dataclass(frozen=True)
class ResourceCost:
    pool_id: str
    amount: int

@dataclass(frozen=True)
class Predicate:
    """可序列化的謂詞"""
    type: str
    params: Dict[str, Any]
    
    def evaluate(self, world_state, context) -> bool:
        # 由規則引擎動態加載執行
        ...

@dataclass(frozen=True)
class TargetingRule:
    """目標規則"""
    range: str           # "melee", "ranged", "touch", etc.
    constraints: List[Predicate]

@dataclass(frozen=True)
class EffectTemplate:
    """效果模板"""
    effect_type: str
    parameters: Dict[str, Any]

class Ability(NamedTuple):
    """能力定義"""
    id: AbilityId
    archetype: str
    costs: List[ResourceCost]
    requirements: List[Predicate]
    targeting: TargetingRule
    effect_chain: List[EffectTemplate]
    failure_branch: List[EffectTemplate]
    tier: TierLevel

class Rule(NamedTuple):
    """遊戲規則"""
    id: RuleId
    pattern: MatchPattern       # 基於 tags/archetypes 的匹配
    resolver: str               # 函數名（通過反射加載）
    priority: int               # 衝突時優先級
    source: Literal["CORE", "SETTING_PACK", "CRYSTALLIZED"]
```

### 1.5 實作順序

1. `value_objects.py` - 所有 ID、Time、Tag 等不可變值物件
2. `entity.py` - Entity, Observation, NPC (extends Entity)
3. `event.py` - Event, StateChange, MechanicsResult
4. `ability.py` - Ability, Rule, Predicate, TargetingRule

### 1.6 驗收標準

- [ ] 所有模型可序列化/反序列化 (JSON, binary)
- [ ] Entity 和 Event 實作 `frozen=True` 確保不可變性
- [ ] EntityId、EventId、Tag 可用 `==` 比較且 hashable
- [ ] 單元測試覆蓋核心資料結構

---

## Phase 2：事件存儲與投影

### 2.1 EventStore 介面

**檔案**: `src/nexus_engine/store/event_store.py`

```python
class EventStore(ABC):
    """事件存儲介面"""
    
    @abstractmethod
    async def append(self, event: Event) -> EventId:
        """追加事件（不可變）"""
        ...
    
    @abstractmethod
    async def get(self, id: EventId) -> Event:
        """獲取單個事件"""
        ...
    
    @abstractmethod
    async def query(self, filter: EventFilter) -> AsyncIterator[Event]:
        """查詢事件流"""
        ...
    
    @abstractmethod
    async def get_since(self, time: GameTime) -> AsyncIterator[Event]:
        """獲取指定時間後的所有事件"""
        ...

@dataclass
class EventFilter:
    actor: EntityRef | None = None
    target: EntityRef | None = None
    location: EntityRef | None = None
    types: List[EventType] | None = None
    time_range: tuple[GameTime, GameTime] | None = None
    involves_entity: EntityRef | None = None
    limit: int = 100
```

### 2.2 SQLite 實現（開發環境）

**檔案**: `src/nexus_engine/store/sqlite_event_store.py`

```python
class SQLiteEventStore(EventStore):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._pool = None
    
    async def initialize(self):
        """創建表結構"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    game_time INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    actor_id TEXT,
                    targets TEXT,  -- JSON
                    location_id TEXT,
                    mechanics TEXT,  -- JSON
                    effects TEXT,    -- JSON
                    witnesses TEXT,  -- JSON
                    narrative_summary TEXT,
                    narrative_full TEXT,
                    parent_event_id TEXT,
                    canon INTEGER DEFAULT 0,
                    raw JSON NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_game_time 
                ON events(game_time)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_actor 
                ON events(actor_id)
            """)
```

### 2.3 StateView 投影視圖

**檔案**: `src/nexus_engine/projection/state_view.py`

```python
class StateView:
    """從事件流重建狀態"""
    
    def __init__(self, event_store: EventStore, snapshot_store: SnapshotStore | None = None):
        self.event_store = event_store
        self.snapshot_store = snapshot_store
        self._entity_cache: Dict[EntityId, Entity] = {}
    
    async def get_entity(self, id: EntityId, depth: int = 1) -> EntityView:
        """獲取實體視圖（depth 控制關聯載入深度）"""
        ...
    
    async def get_location_snapshot(
        self, loc: EntityId, aspects: List[str]
    ) -> LocationView:
        """獲取位置快照"""
        ...
    
    async def get_relationship(self, a: EntityId, b: EntityId) -> Relationship:
        """獲取兩實體關係"""
        ...
    
    async def get_inventory(self, holder: EntityId) -> List[ItemRef]:
        """獲取庫存"""
        ...
    
    async def project_from(
        self, 
        events: AsyncIterator[Event], 
        base_snapshot: Snapshot | None
    ) -> Snapshot:
        """從事件流增量投影"""
        ...
    
    async def snapshot_at(self, time: GameTime) -> Snapshot:
        """重建指定時間點的快照"""
        ...
```

### 2.4 快照存儲

**檔案**: `src/nexus_engine/store/snapshot_store.py`

每 N 個事件（或每 M 遊戲時間）存一次快照，加速狀態重建。

```python
class Snapshot(NamedTuple):
    game_time: GameTime
    event_id: EventId           # 快照對應的最後一個事件 ID
    state: Dict[str, Any]       # 壓縮後的狀態 JSON
    
class SnapshotStore:
    async def save(self, snapshot: Snapshot) -> None: ...
    async def load(self, event_id: EventId) -> Snapshot | None: ...
    async def load_nearest(self, game_time: GameTime) -> Snapshot | None: ...
```

### 2.5 驗收標準

- [ ] 事件追加後可通過 ID 精確檢索
- [ ] EventFilter 支援所有查詢維度
- [ ] StateView 可從空快照正確投影所有實體
- [ ] 快照策略可配置（預設每 1000 事件）
- [ ] 積壓測試：10000 事件後投影一致性正確

---

## Phase 3：規則引擎

### 3.1 規則匹配

**檔案**: `src/nexus_engine/rules/rule_engine.py`

```python
class RuleEngine:
    """分層裁決引擎"""
    
    def __init__(self, rules: List[Rule], setting_pack: SettingPack | None = None):
        self._exact_rules: Dict[EventType, Rule] = {}
        self._tag_rules: List[Rule] = []
        self._setting_rules: List[Rule] = []
        self._load_rules(rules)
    
    def match_exact(self, intent: Intent, context: Context) -> Rule | None:
        """第一層：精確規則匹配"""
        return self._exact_rules.get(intent.action_type)
    
    def match_by_tags(self, intent: Intent, context: Context) -> Rule | None:
        """第二層：標籤推理匹配"""
        best_match = None
        best_score = 0
        for rule in self._tag_rules:
            score = self._calculate_tag_affinity(intent, rule.pattern)
            if score > best_score:
                best_score = score
                best_match = rule
        return best_match if best_score > THRESHOLD else None
    
    def resolve(self, rule: Rule, intent: Intent, context: Context) -> Outcome:
        """執行規則解析"""
        resolver = self._resolvers[rule.resolver]
        return resolver(intent, context, rule.params)
```

### 3.2 內建核心規則

**檔案**: `src/nexus_engine/rules/resolvers.py`

```python
# 預設提供的 resolver 實現

async def resolve_ability_check(
    intent: Intent, 
    context: Context, 
    params: Dict
) -> Outcome:
    """技能檢定解析"""
    actor = context.get_entity(intent.actor_id)
    ability = context.get_ability(intent.ability_id)
    
    # 擲骰 + 修正值 vs 難度
    roll = random.randint(1, 20) + actor.ability_modifiers.get(intent.ability_id, 0)
    difficulty = params["difficulty"]
    
    success = roll >= difficulty
    degree = (roll - difficulty) / 20  # 標準化成功度
    
    return Outcome(
        success=success,
        degree=max(0.0, min(1.0, degree)),
        mechanics=MechanicsResult(
            success=success,
            degree=degree,
            values={"roll": roll, "dc": difficulty}
        ),
        effects=_generate_effects(intent, success, context)
    )

async def resolve_damage(
    intent: Intent,
    context: Context,
    params: Dict
) -> Outcome:
    """傷害解析"""
    ...
```

### 3.3 謂詞系統

**檔案**: `src/nexus_engine/rules/predicates.py`

```python
class PredicateEvaluator:
    """謂詞求值器"""
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._register_builtins()
    
    def _register_builtins(self):
        self._handlers["has_tag"] = self._pred_has_tag
        self._handlers["has_resource"] = self._pred_has_resource
        self._handlers["in_location"] = self._pred_in_location
        self._handlers["entity_has_property"] = self._pred_entity_property
        self._handlers["time_elapsed"] = self._pred_time_elapsed
        self._handlers["relationship_above"] = self._pred_relationship
        self._handlers["and"] = self._pred_and
        self._handlers["or"] = self._pred_or
        self._handlers["not"] = self._pred_not
    
    def evaluate(self, predicate: Predicate, world_state, context) -> bool:
        handler = self._handlers.get(predicate.type)
        if not handler:
            raise ValueError(f"Unknown predicate type: {predicate.type}")
        return handler(predicate.params, world_state, context)
```

### 3.4 驗收標準

- [ ] 規則引擎支援三層匹配（精確 → 標籤 → LLM 回退）
- [ ] 預設 resolver 覆蓋常見場景（技能檢定、傷害、法術效果）
- [ ] 自定義規則可通過模組化方式註冊
- [ ] 規則優先級正確處理衝突
- [ ] 單元測試：規則匹配邏輯隔離可測試

---

## Phase 4：驗證層

### 4.1 驗證器架構

**檔案**: `src/nexus_engine/validation/validator.py`

```python
@dataclass
class ValidationViolation:
    code: str                    # e.g. "POWER_EXCEEDS_TIER"
    message: str
    severity: Literal["error", "warning"]
    context: Dict[str, Any]

@dataclass
class ValidationResult:
    valid: bool
    violations: List[ValidationViolation]
    
    @property
    def failed(self) -> bool:
        return len(self.violations) > 0

class Validator:
    """主驗證器"""
    
    def __init__(
        self,
        canon_store: CanonStore,
        rule_engine: RuleEngine,
        setting_pack: SettingPack,
    ):
        self.canon_store = canon_store
        self.rule_engine = rule_engine
        self.setting_pack = setting_pack
        self._power_limits = self._load_power_tiers()
    
    async def validate_event(self, event: EventDraft) -> ValidationResult:
        """驗證事件草稿"""
        violations = []
        
        # 引用完整性
        for target in event.targets:
            if not await self.state_view.exists(target):
                violations.append(ValidationViolation(
                    code="DANGLING_REF",
                    message=f"Target {target} does not exist",
                    severity="error",
                    context={"target": target}
                ))
        
        # 階層合規
        if event.actor:
            actor = await self.state_view.get_entity(event.actor)
            power = self._estimate_power(event)
            if power > actor.tier_max_power * POWER_TOLERANCE:
                violations.append(ValidationViolation(
                    code="POWER_EXCEEDS_TIER",
                    ...
                ))
        
        return ValidationResult(valid=len(violations) == 0, violations=violations)
    
    async def validate_ruling(
        self, 
        ruling: RulingDraft, 
        actor: Entity
    ) -> ValidationResult:
        """驗證 LLM 生成的裁決"""
        ...
    
    async def validate_persona(
        self, 
        output: str, 
        contract: PersonaContract
    ) -> ValidationResult:
        """驗證 NPC 輸出符合角色契約"""
        ...
```

### 4.2 Canon 驗證

**檔案**: `src/nexus_engine/validation/canon.py`

```python
class CanonStore:
    """正典事實存儲"""
    
    def __init__(self):
        self._facts: Dict[str, CanonFact] = {}
        self._contradiction_index: Dict[str, List[str]] = defaultdict(list)
    
    async def assert_fact(self, fact: CanonFact) -> ValidationResult:
        """聲明正典事實（僅 Setting Pack 初始化時）"""
        if self.contradicts(fact.as_claim()):
            return ValidationResult(valid=False, violations=[...])
        self._facts[fact.id] = fact
        self._index_fact(fact)
        return ValidationResult(valid=True, violations=[])
    
    async def contradicts(self, claim: Claim) -> Optional[CanonFact]:
        """檢查是否與現有正典矛盾"""
        ...
    
    async def query(self, pattern: ClaimPattern) -> List[CanonFact]:
        """查詢正典事實"""
        ...
```

### 4.3 驗收標準

- [ ] 所有 LLM 提議必須經 validate_event 才能提交
- [ ] 引用完整性檢查（INV-1）
- [ ] Canon 事實不可違反（INV-5）
- [ ] 階層威力上限強制執行（INV-7）
- [ ] 驗證失敗時返回可操作的錯誤訊息

---

## Phase 5：LLM 工具面

### 5.1 工具定義

**檔案**: `src/nexus_engine/agents/tools.py`

```python
class AgentTool(Protocol):
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    async def execute(self, params: Dict, context: AgentContext) -> Any: ...

class FindEntityTool:
    name = "find_entity"
    description = "Find entities matching criteria"
    input_schema = {
        "type": "object",
        "properties": {
            "archetype": {"type": "string"},
            "filters": {"type": "object"}
        }
    }
    
    async def execute(self, params: Dict, context: AgentContext) -> List[EntityRef]:
        entities = await context.state_view.find_by_archetype(
            params["archetype"],
            params.get("filters", {})
        )
        return [EntityRef(id=e.id) for e in entities]

class GetEntityTool:
    name = "get_entity"
    ...

class QueryEventsTool:
    name = "query_events"
    ...

class RecallSimilarTool:
    name = "recall_similar_events"
    ...
```

### 5.2 AgentTools 集合

```python
class AgentTools:
    """LLM 可用的完整工具集"""
    
    def __init__(self, state_view: StateView, event_store: EventStore, ...):
        self._tools: Dict[str, AgentTool] = {
            "find_entity": FindEntityTool(state_view),
            "get_entity": GetEntityTool(state_view),
            "query_events": QueryEventsTool(event_store),
            "recall_similar_events": RecallSimilarTool(memory_system),
            "get_applicable_rules": GetApplicableRulesTool(rule_engine),
            "check_canon": CheckCanonTool(canon_store),
            "propose_event": ProposeEventTool(validator),
            # ... others
        }
    
    def get_tool_schemas(self) -> List[Dict]:
        """返回 OpenAI 格式的工具 schema"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema
            }
            for tool in self._tools.values()
        ]
    
    async def execute(self, tool_name: str, params: Dict, context: AgentContext) -> Any:
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await tool.execute(params, context)
```

### 5.3 上下文索引構建

**檔案**: `src/nexus_engine/agents/context_builder.py`

```python
class ContextBuilder:
    """為 LLM 構建精準上下文"""
    
    def __init__(
        self,
        state_view: StateView,
        memory_system: MemorySystem,
        setting_pack: SettingPack,
    ):
        self.state_view = state_view
        self.memory_system = memory_system
        self.setting_pack = setting_pack
    
    async def build_scene_context(
        self,
        player_id: EntityId,
        location_id: EntityId,
        recent_events: List[Event] | None = None,
    ) -> SceneContext:
        """構建當前場景的精準上下文"""
        
        # 1. 位置及其直接內容
        location = await self.state_view.get_location_snapshot(
            location_id, 
            aspects=["entities", "exits", "conditions"]
        )
        
        # 2. 玩家狀態
        player = await self.state_view.get_entity(player_id, depth=2)
        
        # 3. 最近的關鍵事件（壓縮敘事摘要）
        recent = recent_events or await self._get_recent_events(player_id, limit=10)
        
        # 4. 相關記憶
        memories = await self.memory_system.recall_relevant_to(
            entities=[player_id, location_id],
            limit=5
        )
        
        # 5. 可用能力
        abilities = self.setting_pack.get_abilities_for_archetype(player.archetype)
        
        return SceneContext(
            location=location,
            player=player,
            recent_events=recent,
            relevant_memories=memories,
            available_abilities=abilities,
            vocabulary=self.setting_pack.vocabulary,
        )
```

### 5.4 LLM 介面適配

**檔案**: `src/nexus_engine/agents/llm_interface.py`

```python
from litellm import acompletion

class LLMInterface:
    """多 LLM 適配"""
    
    def __init__(
        self,
        model: str = "gpt-4",
        api_base: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.api_base = api_base
        self._tool_schemas = []
    
    async def completion(
        self,
        messages: List[ChatMessage],
        tools: List[Dict] | None = None,
        **kwargs,
    ) -> ChatCompletionResult:
        return await acompletion(
            model=self.model,
            messages=[m.model_dump() for m in messages],
            tools=tools,
            api_base=self.api_base,
            api_key=self.api_key,
            **kwargs
        )
    
    async def structured_completion(
        self,
        messages: List[ChatMessage],
        response_schema: Dict,
    ) -> Any:
        """返回結構化輸出（使用 JSON mode）"""
        response = await self.completion(
            messages=messages,
            response_format={"type": "json_object", "schema": response_schema}
        )
        return json.loads(response.choices[0].message.content)
```

### 5.5 驗收標準

- [ ] 所有 AgentTools 可通過統一的 `execute(tool_name, params)` 調用
- [ ] 工具 schema 符合 OpenAI function calling 格式
- [ ] 上下文構建不泄露無關信息（精準拉取）
- [ ] LLM Interface 支持切換不同 provider（測試用 mock provider）

---

## Phase 6：NPC 行為系統

### 6.1 NPC 實體

**檔案**: `src/nexus_engine/npc/npc.py`

```python
@dataclass
class PersonaContract:
    """角色契約（硬約束）"""
    persona_id: str
    core_traits: List[str]
    speech_pattern: str
    forbidden_behaviors: List[str]  # 必須被遵守
    required_behaviors: List[str]
    
@dataclass
class NPCDrive:
    """底層驅力"""
    drive_id: str
    intensity: float              # 0.0 - 1.0
    saturation: float             # 逐漸衰減

class NPC(Entity):
    """NPC 實體"""
    drives: Dict[str, NPCDrive]
    current_goals: PriorityQueue[Goal]
    persona_contract: PersonaContract
    schedule: Schedule
    memory: NPCMemory
    
    async def tick(self, delta: Duration, context: NPCContext) -> List[Event]:
        """NPC 決策主迴圈"""
        # 見下方 6.2-6.4
```

### 6.2 驅力系統

**檔案**: `src/nexus_engine/npc/drives.py`

```python
# 預設驅力類型
DRIVE_SURVIVAL = "survival"       # 生存
DRIVE_SOCIAL = "social"           # 社交
DRIVE_PRESTIGE = "prestige"       # 聲望
DRIVE_KNOWLEDGE = "knowledge"     # 知識
DRIVE_GOODS = "goods"             # 財物
DRIVE_FREEDOM = "freedom"         # 自由

def calculate_drive_change(
    drive: NPCDrive, 
    event: Event, 
    context: NPCContext
) -> float:
    """根據事件計算驅力強度變化"""
    # 威脅增加生存驅力
    if event.type == EventType.THREAT_DETECTED:
        if drive.drive_id == DRIVE_SURVIVAL:
            return +0.3
    
    # 社交成功增加社交驅力
    if event.type == EventType.SOCIAL_INTERACTION:
        if drive.drive_id == DRIVE_SOCIAL:
            return +0.2 * event.mechanics.degree
    
    # 基礎衰減
    return -0.01
```

### 6.3 目標與規劃

**檔案**: `src/nexus_engine/npc/goals.py`

```python
@dataclass
class Goal:
    id: GoalId
    priority: float
    prerequisites: List[Predicate]
    target_state: StateSpec
    deadline: GameTime | None
    source: Literal["DRIVE_DERIVED", "REACTIVE", "DIRECTOR_ASSIGNED"]
    plan: List[Action] | None = None

class SimplePlanner:
    """簡單的 GOP 規劃器"""
    
    async def plan_next(
        self, 
        npc: NPC, 
        goal: Goal, 
        context: NPCContext
    ) -> Action | None:
        """生成達成目標的下一步行動"""
        # 實現：基於目標狀態逆向規劃
        # 前期可使用簡單的規則映射表
        ...
```

### 6.4 NPC 決策迴圈

**檔案**: `src/nexus_engine/npc/npc.py`

```python
async def npc_tick(npc: NPC, delta: Duration, context: NPCContext) -> List[Event]:
    """NPC 決策主迴圈（分層）"""
    
    # 第一層：慣性（零 LLM）
    if npc.schedule and can_follow_schedule(npc, context.current_situation):
        scheduled = npc.schedule.get_action_at(context.world_time)
        if scheduled:
            return await execute_scheduled_action(npc, scheduled, context)
    
    # 第二層：反應式（規則驅動）
    triggers = detect_reactive_triggers(npc, context)
    if triggers:
        return await execute_reactive_action(npc, triggers, context)
    
    # 第三層：規劃（可能用 LLM）
    if npc.current_goals.empty() or goals_stale(npc):
        npc.current_goals = await goal_generator.generate(npc, context)
    
    action = await planner.plan_next(npc, npc.current_goals.top(), context)
    if action:
        return await execute_action(npc, action, context)
    
    return []
```

### 6.5 群體場景

**檔案**: `src/nexus_engine/npc/ensemble.py`

```python
async def ensemble_scene(
    npcs: List[NPC],
    context: SceneContext,
) -> List[Event]:
    """多 NPC 同場景處理"""
    
    # 收集所有人的人格契約和內部狀態
    personas = [npc.persona_contract for npc in npcs]
    internal_states = [
        {
            "goals": [g.id for g in npc.current_goals],
            "drives": {k: v.intensity for k, v in npc.drives.items()},
            "relationship_to_player": context.relationship_to_player(npc),
        }
        for npc in npcs
    ]
    
    # 單次 LLM 調用生成所有人
    script = await llm.generate_ensemble(
        personas=personas,
        internal_states=internal_states,
        context=context,
        schema=EnsembleScriptSchema,
    )
    
    events = []
    for beat in script.beats:
        # 驗證人格合約
        validated = validator.validate_persona(beat, personas[beat.speaker_index])
        if validated.failed:
            beat = rephrase_to_follow_contract(beat, validated.violations)
        
        event = beat.to_event()
        events.append(event)
    
    return events
```

### 6.6 驗收標準

- [ ] NPC 決策可追溯至 drives / goals / rules 之一（INV-9）
- [ ] PersonaContract.forbidden_behaviors 不可違反（INV-8）
- [ ] 慣性層可在零 LLM 情況下正常運作
- [ ] LLM 生成的 NPC 行為必須通過 persona 驗證

---

## Phase 7：世界模擬器

### 7.1 區域劃分

**檔案**: `src/nexus_engine/world/region.py`

```python
class RegionType(str, Enum):
    ACTIVE = "active"         # 玩家附近，完整模擬
    NEARBY = "nearby"          # 鄰近區域，快進
    DISTANT = "distant"       # 遠方，只處理排程

@dataclass
class Region:
    region_id: str
    region_type: RegionType
    npcs: List[NPC]
    locations: List[EntityId]
    pending_events: List[Event]
    
def partition_by_player_proximity(
    all_regions: List[Region],
    player_location: EntityId,
    radius: Dict[RegionType, int],  # tile 為單位的半徑
) -> Dict[RegionType, List[Region]]:
    """按玩家注意力分區"""
    ...
```

### 7.2 世界模擬主迴圈

**檔案**: `src/nexus_engine/world/world_simulator.py`

```python
class WorldSimulator:
    """世界模擬器"""
    
    async def advance_time(self, delta: Duration) -> List[Event]:
        all_events = []
        
        regions = partition_by_player_proximity(
            self.world_regions, 
            self.player_location,
            self.config.proximity_radius
        )
        
        # Active region：完整處理
        for region in regions[RegionType.ACTIVE]:
            for npc in region.npcs:
                events = await npc.tick(delta, self.context)
                all_events.extend(events)
        
        # Nearby：批次快進
        for region in regions[RegionType.NEARBY]:
            events = await fast_forward_region(region, delta)
            all_events.extend(events)
        
        # Distant：只處理排程/重大事件
        for region in regions[RegionType.DISTANT]:
            events = await process_scheduled_only(region, delta)
            all_events.extend(events)
        
        # 組織動態
        for faction in self.factions:
            events = await faction.tick(delta, self.world_state)
            all_events.extend(events)
        
        # Director：低頻敘事規劃（每 N 個 delta）
        if self._should_invoke_director():
            blueprint = await self.director.plan(self.world_state, self.player_arc)
            self.scheduler.ingest(blueprint)
        
        return all_events
```

### 7.3 Director（敘事導演）

**檔案**: `src/nexus_engine/world/director.py`

```python
class Director:
    """低頻敘事規劃"""
    
    async def plan(
        self, 
        world_state: StateView,
        player_arc: PlayerArc,
    ) -> NarrativeBlueprint:
        """生成敘事藍圖"""
        # 1. 評估玩家當前弧
        arc_progress = self._evaluate_arc_progress(player_arc, world_state)
        
        # 2. 識別未充分利用的元素
        underused = self._find_underused_elements(world_state)
        
        # 3. 生成下一步建議
        suggestions = await self.llm.generate_arc_suggestions(
            arc_progress=arc_progress,
            underused=underused,
            world_state_summary=self._summarize_world_state(world_state),
        )
        
        return NarrativeBlueprint(
            pacing_adjustments=suggestions.pacing,
            recommended_encounters=suggestions.encounters,
            foreshadowing_hooks=suggestions.hooks,
            schedule_modifications=suggestions.schedules,
        )
```

### 7.4 驗收標準

- [ ] 按玩家注意力分級模擬精度（INV-8, INV-9 隱式）
- [ ] 時間推進不遺漏任何活躍 NPC
- [ ] Director 以可配置頻率運行（非每幀）
- [ ] 世界模擬器可脫離 LLM 獨立運行（僅規則引擎）

---

## Phase 8：結晶化機制

### 8.1 觀察器

**檔案**: `src/nexus_engine/crystallization/crystallizer.py`

```python
@dataclass
class RulingObservation:
    ruling: RulingDraft
    context: Context
    outcome: Outcome
    timestamp: GameTime

@dataclass
class CrystallizationCandidate:
    """結晶化候選模式"""
    pattern_description: str
    occurrences: int
    consistency_score: float      # 0.0 - 1.0
    sample_rulings: List[RulingObservation]
    suggested_rule: Rule | None

class Crystallizer:
    """觀察成功的湧現模式，沉澱為新規則"""
    
    def __init__(self, config: CrystallizerConfig):
        self.config = config
        self._observations: List[RulingObservation] = []
        self._pattern_groups: Dict[str, List[RulingObservation]] = defaultdict(list)
    
    def observe(self, ruling: RulingDraft, context: Context, outcome: Outcome):
        """觀察裁決"""
        self._observations.append(RulingObservation(ruling, context, outcome, context.game_time))
        
        # 嘗試模式分組
        pattern_key = self._extract_pattern_key(ruling)
        if pattern_key:
            self._pattern_groups[pattern_key].append(
                RulingObservation(ruling, context, outcome, context.game_time)
            )
    
    def extract_candidates(self) -> List[CrystallizationCandidate]:
        """提取結晶化候選"""
        candidates = []
        
        for pattern_key, observations in self._pattern_groups.items():
            if len(observations) >= self.config.threshold:
                consistency = self._calculate_consistency(observations)
                if consistency > self.config.min_consistency:
                    candidates.append(CrystallizationCandidate(
                        pattern_description=pattern_key,
                        occurrences=len(observations),
                        consistency_score=consistency,
                        sample_rulings=observations[-10:],  # 最近 10 個
                        suggested_rule=None,
                    ))
        
        return candidates
    
    async def crystallize(self, candidate: CrystallizationCandidate) -> Rule:
        """將成功的模式泛化為新規則"""
        # 泛化具體 entity 為 archetype/tag
        generalized = self._generalize_pattern(candidate)
        
        # 驗證新規則
        validated = await self.validator.validate_rule(generalized)
        if validated.failed:
            raise CrystallizationError(validated.violations)
        
        # 註冊到規則引擎
        self.rule_engine.register(generalized, source=RuleSource.CRYSTALLIZED)
        
        return generalized
```

### 8.2 模式泛化

**檔案**: `src/nexus_engine/crystallization/pattern.py`

```python
def generalize_pattern(candidate: CrystallizationCandidate) -> Rule:
    """將具體裁決泛化為通用規則"""
    
    # 1. 提取共同的效果模板
    common_effects = find_common_effects(candidate.sample_rulings)
    
    # 2. 將具體實體替換為 archetype 或 tag
    generalized_effects = []
    for effect in common_effects:
        gen_effect = replace_specific_with_placeholder(
            effect,
            placeholder_fn=_archetype_placeholder
        )
        generalized_effects.append(gen_effect)
    
    # 3. 構建通用匹配模式
    pattern = MatchPattern(
        action_types={ruling.intent.action_type for ruling in candidate.sample_rulings},
        tags={tag for ruling in candidate.sample_rulings for tag in ruling.intent.tags},
        context_conditions=extract_common_conditions(candidate.sample_rulings),
    )
    
    return Rule(
        id=RuleId(f"crystallized_{candidate.pattern_description}"),
        pattern=pattern,
        resolver="crystallized_effect",
        priority=50,  # 低優先級，可被精確規則覆蓋
        source=RuleSource.CRYSTALLIZED,
        params={"effects": generalized_effects},
    )
```

### 8.3 驗收標準

- [ ] 觀察者追蹤所有 LLM 裁決（可審計）
- [ ] 一致性分數可配置
- [ ] 結晶化後的規則自動擁有較低優先級
- [ ] 可手動觸發結晶化（調試用）

---

## Phase 9：Setting Pack 系統

### 9.1 Setting Pack 結構

**檔案**: `src/nexus_engine/setting/setting_pack.py`

```python
@dataclass
class Archetype:
    """原型定義"""
    id: ArchetypeId
    name: str
    description: str
    base_tags: FrozenSet[Tag]
    base_properties: Dict[str, Any]
    default_abilities: List[AbilityId]
    power_tier: TierLevel

@dataclass
class PowerSystemSpec:
    """力量體系規範"""
    resource_pools: List[ResourcePoolDef]
    tier_levels: List[TierDef]
    advancement_rules: List[AdvancementRule]
    ability_taxonomy: AbilityTaxonomy

@dataclass
class ControlledVocabulary:
    """受控詞彙表"""
    namespaces: FrozenSet[str]
    tags_by_namespace: Dict[str, FrozenSet[str]]
    
    def is_valid_tag(self, tag: Tag) -> bool:
        return (
            tag.namespace in self.namespaces and
            tag.value in self.tags_by_namespace.get(tag.namespace, FrozenSet())
        )

@dataclass
class StyleGuide:
    """敘事風格指南"""
    tone: str                    # "gritty", "heroic", "whimsical", etc.
    perspective: str             # "first_person", "third_person_limited", etc.
    prose_style: Dict[str, Any]  # 具體風格參數

class SettingPack:
    """設定包"""
    id: str
    version: str
    archetypes: Dict[ArchetypeId, Archetype]
    power_system: PowerSystemSpec
    vocabulary: ControlledVocabulary
    common_sense_rules: List[Rule]
    narrative_style: StyleGuide
    lore_corpus: LoreCorpus      # 向量化的原典
    canon_facts: List[CanonFact]
    
    def validate_entity(self, entity: Entity) -> ValidationResult:
        """驗證實體符合設定包約束"""
        ...
```

### 9.2 預設 Setting Pack：金庸武俠示例

**檔口**: `src/nexus_engine/setting/packs/jinyong.py`

```python
# 預設 Vocabulary
JINYONG_VOCABULARY = ControlledVocabulary(
    namespaces=frozenset(["material", "technique", "school", "rank", "element", "body_part"]),
    tags_by_namespace={
        "material": frozenset(["steel", "jade", "wood", "bone"]),
        "technique": frozenset(["sword", "palm", "fist", "staff", "inner_force"]),
        "school": frozenset(["shaolin", "wudang", "emei", "songliao"]),
        "rank": frozenset(["junior", "senior", "master", "grandmaster"]),
        "element": frozenset(["fire", "water", "earth", "wood", "metal"]),
        "body_part": frozenset(["hand", "foot", "eye", "meridian"]),
    }
)

# 力量體系：內力系統
JINYONG_POWER_SYSTEM = PowerSystemSpec(
    resource_pools=[
        ResourcePoolDef(id="qi", name="氣", max_at_tier=[100, 200, 400, 800, 1600]),
        ResourcePoolDef(id="jing", name="精", max_at_tier=[50, 100, 200, 400, 800]),
    ],
    tier_levels=[
        TierDef(level=0, name="不入流", abilities=["basic_movement"]),
        TierDef(level=1, name="三流", abilities=["basic_techniques"]),
        TierDef(level=2, name="二流", abilities=["advanced_techniques"]),
        TierDef(level=3, name="一流", abilities=["master_techniques"]),
        TierDef(level=4, name="宗師", abilities=["grandmaster_techniques"]),
    ],
    advancement_rules=[...],
    ability_taxonomy=[...],
)

# 預設 Archetype
JINYONG_ARCHETYPES = {
    ArchetypeId("swordsman"): Archetype(
        id=ArchetypeId("swordsman"),
        name="劍客",
        base_tags=frozenset([Tag("technique", "sword"), Tag("school", "neutral")]),
        base_properties={"martial_arts_style": "sword"},
        default_abilities=["basic_sword_strike", "defensive_stance"],
        power_tier=TierLevel.MUNDANE,
    ),
    ...
}
```

### 9.3 驗收標準

- [ ] Setting Pack 可完整序列化/反序列化（JSON/YAML）
- [ ] 實體創建時強制檢查 vocabulary 合規（INV-6）
- [ ] 可在運行時動態切換 Setting Pack
- [ ] 提供至少一個完整的示例 Pack（金庸或 D&D 5e）

---

## Phase 10：敘事生成流水線

### 10.1 主流水線

**檔案**: `src/nexus_engine/narrative/pipeline.py`

```python
async def process_player_action(
    input: String,
    player_id: EntityId,
    context: GameContext,
) -> NarrativeOutput:
    """處理玩家輸入的核心流水線"""
    
    # 1. 意圖解析
    scene_context = await context_builder.build_scene_context(
        player_id, 
        context.current_location
    )
    
    intent = await llm.parse_intent(
        input=input,
        context=scene_context,
        schema=IntentSchema,
    )
    
    # 2. 驗證引用
    validate_intent_refs(intent)
    
    # 3. 資訊收集（LLM agent loop）
    working_context = await agent_gather_context(intent, scene_context)
    
    # 4. 分層裁決
    outcome = await resolve_action(intent, working_context)
    
    # 5. 執行
    events = outcome.to_events()
    for event in events:
        validation = await validator.validate_event(event)
        if validation.failed:
            event = rebalance(event, validation.violations)
        await event_store.append(event)
        await state_view.apply(event)
    
    # 6. 生成敘事（僅此步自由發揮，但有 grounding）
    narrative = await llm.narrate(
        events=events,
        context=working_context,
        style=setting_pack.narrative_style,
        persona_contracts=get_active_personas(working_context),
    )
    
    # 7. 記憶更新
    await memory_system.ingest(events, narrative)
    canon_candidates = extract_canon_candidates(events)
    await canon_store.consider(canon_candidates)
    
    return NarrativeOutput(
        narrative=narrative,
        events=events,
        game_time=context.game_time,
    )
```

### 10.2 意圖解析

```python
class IntentSchema(pydantic.BaseModel):
    action_type: EventType
    actor_ref: EntityRef
    targets: List[EntityRef]
    tags: List[Tag]
    parameters: Dict[str, Any]
    implied_location: EntityRef | None

async def parse_intent(
    input: String,
    context: SceneContext,
    llm: LLMInterface,
) -> Intent:
    """將自然語言解析為結構化意圖"""
    prompt = f"""
    玩家輸入: {input}
    
    當前場景: {context.location.summary}
    玩家可用能力: {context.available_abilities}
    
    請解析玩家意圖，返回結構化結果。
    """
    
    result = await llm.structured_completion(
        messages=[ChatMessage(role="user", content=prompt)],
        response_schema=IntentSchema,
    )
    return Intent(**result)
```

### 10.3 敘事生成

```python
async def narrate(
    events: List[Event],
    context: WorkingContext,
    style: StyleGuide,
    persona_contracts: List[PersonaContract],
) -> String:
    """生成自然語言敘事"""
    
    # 構建 grounding 上下文
    grounding = {
        "facts": [e.narrative_summary for e in events],
        "mechanics": {e.id: e.mechanics.dict() for e in events},
        "character_states": context.get_relevant_character_states(),
    }
    
    prompt = f"""
    事件事實:
    {grounding['facts']}
    
    角色狀態:
    {grounding['character_states']}
    
    風格指導: {style}
    
    請根據上述事實生成生動的敘事描述。
    確保敘事與事實一致，不添加未經確認的細節。
    """
    
    response = await llm.completion(
        messages=[ChatMessage(role="user", content=prompt)],
    )
    
    return response.choices[0].message.content
```

### 10.4 驗收標準

- [ ] 流水線每步可獨立測試和替換
- [ ] LLM 輸出始終有事實 grounding
- [ ] 敘事風格可通過 StyleGuide 配置
- [ ] 失敗路徑（驗證失敗）有優雅降級

---

## Phase 11：整合測試與迭代

### 11.1 測試策略

```
tests/
├── unit/                      # 隔離單元測試
│   ├── test_entity.py
│   ├── test_event.py
│   ├── test_rule_engine.py
│   ├── test_validator.py
│   └── test_predicates.py
├── integration/                # 整合測試
│   ├── test_event_store.py
│   ├── test_state_projection.py
│   └── test_full_pipeline.py
├── fixtures/                   # 測試數據
│   └── minimal_jinyong_pack.yaml
└── e2e/                        # 端到端
    └── test_playthrough.py
```

### 11.2 關鍵不變式測試

```python
def test_invariant_1_referential_integrity(event_store, state_view):
    """INV-1: 所有 EntityRef 必須指向實存實體"""
    # 嘗試創建引用不存在實體的事件
    ...

def test_invariant_2_event_immutability(event_store):
    """INV-2: Event 一旦 append 即不可變"""
    ...

def test_invariant_4_validator_runs_before_commit(validator, event_draft):
    """INV-4: LLM 輸出必須經 Validator 才能影響 world_state"""
    ...
```

### 11.3 性能基準

```python
@pytest.mark.benchmark
async def test_projection_performance(event_store, benchmark):
    """10000 事件後投影性能"""
    # 基準：10000 事件投影 < 500ms
    ...
```

---

## 技術決策記錄（ADR）

| ID | 決策 | 理由 |
|----|------|------|
| ADR-001 | 使用 Pydantic v2 進行資料驗證 | 類型安全、自动生成 JSON schema |
| ADR-002 | 事件存儲使用 SQLite（開發） | 零配置，易於測試 |
| ADR-003 | 使用 LiteLLM 統一 LLM 介面 | 支持多 provider，便於切換 |
| ADR-004 | 前期向量檢索使用 BM25 | 避免額外依賴，快速實現 |
| ADR-005 | 規則Resolver通過字串反射加載 | 允許 Setting Pack 定義自定義規則 |

---

## 依賴與風險

### 關鍵依賴

- **LLM API 穩定性**：系統功能依賴 LLM 提供者的可用性
- **向量檢索延遲**：記憶系統性能直接影響上下文質量
- **規則覆蓋度**：前期預設規則無法覆盖所有創意互動

### 已知風險

1. **LLM 幻覺**：即使有驗證層，LLM 可能生成合理的錯誤裁決
   - 緩解：嚴格的分層裁決，LLM 裁決僅作為最後回退

2. **規則爆炸**：隨著 Setting Pack 增加，規則衝突可能增多
   - 緩解：明確的優先級和結晶化機制

3. **性能瓶頸**：向量檢索和狀態投影在長時間遊玩後可能變慢
   - 緩解：快照策略和分層模擬

---

## 後續擴展方向

1. **多人支援**：添加 session 管理與玩家間同步
2. **視覺化工具**：GM 控制台、事件流視圖
3. **自定義 Resolver**：允許用戶用 Python 編寫規則邏輯
4. **分支/存檔**：基於事件流的遊戲狀態分支
5. **多語言支援**：Setting Pack 的本地化框架

---

## 快速開始預期用戶流程

```python
# 1. 初始化引擎
engine = NexusEngine()

# 2. 加載或創建 Setting Pack
setting = SettingPack.load("jinyong_wuxia")
engine.load_setting(setting)

# 3. 創建遊戲会话
session = engine.create_session()

# 4. 玩家輸入循環
async for input in player_input_stream():
    output = await session.process_action(input)
    print(output.narrative)
```

---

*本文檔為初步實施計劃，具體實現細節將在每階段開始前進一步細化。*
