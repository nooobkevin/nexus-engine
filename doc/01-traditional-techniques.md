# 相關的傳統技巧清單

> 本系統本質上是多個成熟領域的交匯點。很多看起來新穎的設計，其實都有幾十年的工程智慧可以借鑒。以下按子問題分類整理。

---

## 一、事件溯源與狀態管理

### Event Sourcing (金融/分散式系統)

銀行交易系統幾十年前就在用這個模式。核心想法完全一樣：append-only 事件日誌 + 可重建的狀態投影。Martin Fowler 的經典文章、Greg Young 的 CQRS 演講是必讀材料。

### CQRS (Command Query Responsibility Segregation)

讀寫分離。寫入走 event store，讀取走 materialized views。我們的 `EventStore` 與 `StateView` 正是這個模式。

### Git 的物件模型

不可變 commit + 引用 + 分支。存檔系統幾乎可以直接抄 Git：事件流 = commit history，存檔點 = tag，劇情分支 = branch，甚至可以做 `diff` 兩個存檔的差異。

### Redux / Flux 架構

前端世界的 state management 範式。action → reducer → new state，本質上是 event sourcing 的輕量版。Action creator 的模式可以借鑒來設計 LLM 的 event proposal。

### Write-Ahead Logging (資料庫)

SQLite、PostgreSQL 的 WAL 機制。事件必須先寫入日誌才能修改狀態，崩潰後可從日誌恢復。我們的系統天然具備這個特性。

---

## 二、遊戲 AI 與 NPC 行為

### GOAP (Goal-Oriented Action Planning)

Jeff Orkin 在《F.E.A.R.》裡提出的架構。NPC 有 goals 和 available actions，用 A* 搜索規劃達成目標的行動序列。我們的 `Drive-Goal-Plan` 架構直接繼承自這個傳統。

### Behavior Trees

《Halo 2》以後成為業界標準。比有限狀態機更好組織的 NPC 行為結構。日常慣性行為非常適合用 BT 實作。

### Utility AI

《Sims》、《The Sims 3》用的系統。每個可能行動計算一個 utility score，選最高的執行。非常適合處理 drives 驅動的行為：餓了 → 吃飯的 utility 升高。

### HTN (Hierarchical Task Networks)

《Killzone 2》等作品使用。把高層目標逐級分解為具體動作。我們的 Director → Scheduler → Scene Runner 就是 HTN 的結構。

### Left 4 Dead 的 AI Director

Valve 2008 年的設計。不直接控制怪物，而是動態調整節奏、生成壓力。我們的 Director 模式直接致敬這個設計。Michael Booth 的 GDC talk 極有啟發。

### Dwarf Fortress 的模擬哲學

極致的細粒度模擬 + 湧現敘事。Tarn Adams 的設計對「世界感覺活著」這件事有深刻啟示。但它的教訓也很重要：**過度模擬會導致性能災難與體驗稀釋**，我們的分級模擬正是為避免這個陷阱。

---

## 三、資料結構與查詢

### Entity-Component-System (ECS)

遊戲引擎的現代標配（Unity DOTS、Bevy、Overwatch）。Entity 是 id，Component 是資料，System 是行為。我們的 `Entity + tags + properties + observations` 結構非常 ECS-like。ECS 的好處：組合優於繼承、cache friendly、易於查詢。

### Component-based design (Unity GameObject)

雖然沒有 ECS 極致，但組合屬性的思想一致。NPC = Actor + Dialogue + Combat + Schedule 等組件的組合。

### Spatial Indexing (四叉樹、八叉樹、BVH)

處理「玩家附近的實體」查詢。我們的 regional partitioning（active/nearby/distant）本質上是空間索引問題。

### Inverted Index (搜尋引擎)

Lucene、Elasticsearch 的核心。Tag → Entity 的反向索引能加速「所有帶 fire 標籤的實體」這類查詢，是常識推理引擎的基礎。

### Graph Database 模式

Neo4j、JanusGraph。人物關係、組織結構、地點連接天然是圖結構。Cypher 查詢語言的設計思路可借鑒來設計 LLM 的查詢 API。

---

## 四、記憶與壓縮

### LRU Cache / 多層快取

CPU 有 L1/L2/L3 cache，我們的上下文組裝有 working context / scene pack / vector retrieval / full replay。完全同構的分級思想。

### Checkpoint-Restart

HPC 與資料庫領域的標準技術。定期做 snapshot，崩潰後從最近 snapshot + 重放 log 恢復。我們的 state_snapshots 正是這個。

### Write-Through vs Write-Back Cache

應用於 narrative_cache 的決策：什麼時候需要持久化，什麼時候可以丟棄。

### Log Compaction (Kafka)

事件日誌過大時如何壓縮。保留關鍵事件（canon）、合併瑣碎事件為摘要。我們的分層摘要金字塔本質上是這個。

### 向量檢索 (Information Retrieval)

TF-IDF、BM25 到 dense embedding。幾十年的 IR 研究可以直接套用。混合檢索（稀疏 + 稠密）通常比純 embedding 效果更好，這個教訓很重要。

---

## 五、規則引擎與推理

### Rete Algorithm (專家系統)

Drools、CLIPS 等規則引擎的核心算法。高效匹配大量規則對大量事實。我們的「標籤推理層」需要類似技術才能擴展到數千條規則。

### Prolog / Datalog

邏輯編程的典範。`fire(X) :- match(X), lit(X).` 這類聲明式規則非常適合表達常識推理。即使不用 Prolog，其思想值得借鑒。

### Production Systems (Soar, ACT-R)

認知建模的經典架構。IF-THEN 規則 + 工作記憶。我們的 NPC 決策系統可以看作簡化版 production system。

### Constraint Satisfaction

CSP solver（AC-3、backtracking）。當 LLM 提議的實體或能力有多個約束要同時滿足時，這是正確的解題工具。

---

## 六、模擬與時間管理

### Discrete Event Simulation

SimPy、排隊論的基礎。我們的 world clock + scheduled events 正是 DES。優先隊列（堆）實作的事件調度器是標配。

### Frame-based vs Event-based Simulation

遊戲引擎的雙路傳統。Active region 可以 frame-based（每 tick 更新），Distant region 可以 event-based（只在事件時處理）。

### Level of Detail (LOD)

3D 渲染的經典優化：遠處物體用低模。我們的模擬精度分級（active/nearby/distant）是 LOD 在敘事領域的對應物。

### Fog of War

RTS 遊戲的視野系統。玩家看不到的地方用模糊/過期資訊呈現。這正是處理 NPC 離開玩家視野後的最佳心智模型。

---

## 七、一致性與驗證

### Type Systems

Hindley-Milner、Rust 的 borrow checker。編譯期防止不合法狀態。我們的 schema validation 本質上是在運行時做類型檢查，Pydantic / JSON Schema 是具體工具。

### Design by Contract (Eiffel, Bertrand Meyer)

前置條件、後置條件、不變式。我們明確列出的 10 條 invariants 正是 DbC 思想。每個函數應該有 precondition 和 postcondition。

### Referential Integrity (資料庫)

Foreign key constraints。我們的 `EntityRef 必須指向實存實體`就是這個。ACID 的 C（Consistency）是框架的核心訴求。

### Model Checking (形式化方法)

TLA+、Alloy。對於關鍵不變式，可以用形式化方法驗證。至少在設計階段用 TLA+ 建模核心狀態轉換是值得的。

---

## 八、劇本與敘事結構

### Interactive Fiction 傳統

Infocom 時代到 Inform 7。Graham Nelson 的 Inform 7 對「世界建模」（rooms, objects, rules）有深刻洞察。Emily Short 的設計文章極有價值。

### Twine / Ink / Yarn

現代敘事腳本語言。Ink (Inkle, 《80 Days》《Heaven's Vault》) 的 weave 語法處理分支與歸併的方式值得學習。Setting Pack 的 arc 定義可以參考 Ink 的結構。

### Façade (2005, Procedural Drama)

Michael Mateas 和 Andrew Stern 的突破性作品。Beat-based narrative、drama manager 的概念直接對應我們的 Director。論文《A Behavior Language for Story-Based Believable Agents》必讀。

### Storylets (Failbetter Games, 《Fallen London》)

小塊劇情單元 + 觸發條件 + 後果。極為靈活的敘事結構，正好對應我們的 scheduled events + dynamic events。Alexis Kennedy 的文章有深入討論。

### Drama Management (James Lester 等的研究)

1990s 以來學術界對「如何在玩家自由度下維持戲劇張力」的研究。Director 模式的理論基礎。

---

## 九、Agent 與多 Agent 系統

### BDI 架構 (Belief-Desire-Intention)

經典 agent 架構。NPC 的 `drives` 是 desires，`current_goals` 是 intentions，`observations` 是 beliefs。Rao & Georgeff 的論文是起點。

### Blackboard Systems

多 agent 共享資訊的架構。HEARSAY-II 語音識別系統的遺產。我們的 world_state 就是黑板，各子系統讀寫其上。

### Contract Net Protocol

任務分配協議。NPC 組織內部的任務分派可以借鑒。

---

## 十、工程實踐

### CRDTs (Conflict-free Replicated Data Types)

分散式系統中的合併策略。如果未來要做多人共享世界，CRDTs 是處理同時修改的正解。

### Actor Model (Erlang, Akka)

每個 NPC 是一個 actor，透過訊息傳遞互動。對於大規模 NPC 模擬是優雅方案。

### Memoization / 動態規劃

LLM 裁決的快取。相同情境下的裁決應該能復用。

### Rate Limiting / Backpressure

LLM API 調用的現實約束。每回合的 LLM 預算管理。

### Observability (Metrics, Tracing, Logging)

OpenTelemetry 等工具。Event store 天然是 trace log，但需要加上 LLM 調用追蹤，成本監控、一致性違反告警。

### A/B Testing 基礎設施

測試不同的 prompt、裁決策略、模型版本的效果。長週期遊戲的迴歸測試極為重要。

---

## 最有啟發的幾個交叉點

如果要挑最值得深入研究的對應關係：

**Event Sourcing + Git** 共同為存檔、分支、審計提供完整範式，這套組合直接搬過來基本就夠用。

**ECS + Tag system** 讓 entity 具備組合性與可查詢性，是動態世界的核心資料結構。

**GOAP + Utility AI + BDI** 三者結合起來覆蓋了 NPC 行為的絕大部分需求，分別對應規劃、選擇、內在驅力。

**Storylets + Drama Management** 是開放世界敘事的成熟答案，比線性劇本和純湧現都更務實。

**Rete + Datalog** 是規則引擎擴展性的技術基礎，手寫規則匹配很快會遇到瓶頸。

**Level of Detail + Fog of War** 是處理「世界很大但計算資源有限」的最佳心智模型。

---

## 一個重要的提醒

這個領域的很多「新想法」其實都有先例。在實作前花一兩週泡在這些經典材料裡，能省下幾個月的重新發明。尤其是 Façade 那個項目——2005 年就在做我們今天討論的大部分問題，遇到的坑和解法都極有參考價值。

LLM 只是一個新的工具，不改變底層的軟體工程原則。**框架的骨架應該由這些傳統智慧構成，LLM 嵌入到其中合適的位置**，而不是反過來讓 LLM 主導架構。
