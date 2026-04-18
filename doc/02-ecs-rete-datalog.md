# ECS + Tag System 與 Rete + Datalog 深入介紹

這兩組技術分別解決不同層面的問題：ECS + Tag 是**資料組織**的範式，Rete + Datalog 是**規則推理**的範式。兩者在我們的框架裡是互補的——前者定義「世界由什麼構成」，後者定義「世界如何運作」。

---

## 一、ECS（Entity-Component-System）深入

### 1.1 核心思想與歷史脈絡

ECS 的核心顛覆是：**放棄繼承，擁抱組合**。傳統 OOP 遊戲開發中，一個 `Orc` 繼承自 `Enemy` 繼承自 `Character` 繼承自 `GameObject`，層層套娃。結果是：

- 菱形繼承問題（一個會飛的魚既是 Fish 又是 FlyingCreature）
- 胖基類（GameObject 塞滿所有子類可能需要的方法）
- 改一處動全身（修改 Character 可能影響幾十個子類）

ECS 的回答是：**Entity 只是一個 ID，Component 是純資料，System 是純行為**。一個實體「是什麼」，由它**擁有哪些 Component** 決定，而非它的類別。

歷史上，ECS 的關鍵節點：
- **Thief (1998)** 和 **Dungeon Siege (2002)** 是早期探索，Scott Bilas 的 GDC 2002 talk 是經典材料
- **Unity** 普及了 component-based 設計（但不是純 ECS）
- **Overwatch** 的 GDC 2017 talk 展示了 ECS 如何支撐網路同步
- **Bevy、Unity DOTS、EnTT** 是現代的實作典範

### 1.2 三個核心概念的精確定義

```
Entity:
    id: UUID
    # 就這樣。Entity 本身不含任何資料。
    # 它只是一個「這裡有個東西」的標記。


Component:
    # 純資料，無行為（無方法）
    # 典型 Component 例子：
    Position { x, y, z }
    Health { current, max }
    Inventory { items: [ItemRef] }
    Faction { id: FactionRef }
    PersonaContract { voice_rules, forbidden }
    
System:
    # 純行為，無狀態
    # 一個 System 聲明它關心哪些 Component 組合
    # 對所有具備該組合的 Entity 批次處理
    
    MovementSystem:
        query: Entity with [Position, Velocity]
        update(dt):
            for entity in query:
                entity.Position += entity.Velocity * dt
```

**關鍵屬性**：Entity 可以**動態增減 Component**。一個普通 NPC 加上 `Beyonder` component 就變成非凡者，加上 `Poisoned` component 就進入中毒狀態，移除 `Alive` component 就死了。

### 1.3 ECS 對我們框架的意義

回到我們的系統設計，ECS 的適配度極高：

**動態世界的天然支持**

前面討論過「LLM 可以動態擴展實體屬性」的需求。在 ECS 下，這等於「動態添加 Component」。不需要修改類別定義，不需要資料庫遷移，只是往 entity 的 component 集合裡新增一項。

**跨 Setting 的統一表示**

D&D 的法師和武俠的劍客在 ECS 下都是 `Entity`。差異只在於 Component 組合：
```
法師 = [Actor, Position, Health, SpellSlots, SpellBook, Intelligence]
劍客 = [Actor, Position, Health, InnerQi, MartialArts, Meridians]
```
`SpellSlots` 和 `InnerQi` 在底層都是 `ResourcePool` component 的實例，只是配置不同。

**查詢即操作**

System 的「query by component signature」模式，天然對應 LLM 查詢工具的設計：
```
find_entity(with_components=[Merchant, LocatedIn(黃沙集), SuspicionLevel>50])
```
這比 SQL join 自然得多，因為它就是在問「世界中有哪些東西同時具備 X、Y、Z 屬性」。

### 1.4 ECS 的進階變體

**Archetype-based ECS** (Unity DOTS、Bevy)

所有擁有相同 component 組合的 entity 存在同一個 archetype table 中。例如所有 `[Position, Health, Merchant]` 的實體連續存儲。好處是 cache-friendly 的迭代，壞處是添加/移除 component 時要在 archetype 間搬移資料。

**Sparse Set ECS** (EnTT)

每個 component 類型有自己的 sparse set，支持快速添加/移除，但跨 component 迭代稍慢。

**對我們框架的選擇**：不需要追求極致性能，應優先**語義清晰度**。一個概念上類似 archetype 但實作簡單的設計足矣：

```
Archetype 定義 = Component 組合的「模板」
   WuxiaCharacter archetype = [Actor, Position, Health, InnerQi, 
                                MartialArts, Meridians, Faction,
                                PersonaContract]
   
實體化時：
   character = Entity()
   for component_type in WuxiaCharacter.components:
       character.add(component_type.default_instance())
```

這個「模板」就對應我們前面設計的 `Setting Archetypes` 層。

---

## 二、Tag System 深入

### 2.1 Tag vs Component：精妙的區別

乍看之下 Tag 和 Component 很像，其實有本質差異：

| 維度 | Component | Tag |
|------|-----------|-----|
| 資料載荷 | 有（如 Health.current=15） | 無，純粹標記 |
| 粒度 | 結構化，對應具體遊戲機制 | 語義化，對應概念屬性 |
| 變更頻率 | 經常變動（每幀/每回合） | 相對穩定（偶爾變動） |
| 用途 | 驅動 System 計算 | 驅動查詢與規則匹配 |
| 數量級 | 每 entity 幾個到十幾個 | 每 entity 可以幾十個 |

**Component 回答「這個東西是什麼」**，**Tag 回答「這個東西有什麼性質」**。

### 2.2 為什麼需要 Tag

前面討論的「常識推理」與「湧現互動」，核心依賴就是 tag。回想那個例子：

> 玩家說：「我用冰系法術凍住河面過河」

系統需要知道：
- 冰系法術有 `element:ice`、`effect:freeze` 的標籤
- 河流有 `material:water`、`state:liquid`、`temperature:ambient` 的標籤
- 常識規則：`freeze + liquid = solid`、`ice + water = solid_ice`

這些 tag 並不是 Component（河流沒有「flowability」這種遊戲機制），但它們是推理的基礎。

**Tag 的設計哲學**：描述世界的**概念本體**，而非遊戲機制。

### 2.3 受控詞彙表（Controlled Vocabulary）

最容易被忽視但極其關鍵：**tag 不能是任意字串**。否則 LLM 一次叫 "hot"、一次叫 "fiery"、一次叫 "burning"，推理系統無法對齊。

受控詞彙表的設計：

```
TagVocabulary:
    namespaces:
        element: [fire, water, earth, air, ice, lightning, 
                  metal, wood, light, dark, void]
        state: [solid, liquid, gas, plasma, spiritual]
        material: [stone, wood, metal, flesh, fabric, ...]
        social: [hostile, friendly, neutral, allied, rival]
        emotion: [calm, angry, afraid, suspicious, ...]
        ...
    
    synonyms:
        "burning" -> "fire"
        "frozen" -> "ice"
        "scared" -> "afraid"
    
    hierarchies:
        fire is_a element
        flesh is_a organic_material
        organic_material is_a material
```

LLM 提出新 tag 時，必須：
1. 查詢是否已存在同義詞
2. 若為新概念，必須歸入某個 namespace
3. 建立與現有 tag 的關係（is_a, opposite_of, interacts_with）

這等於在讓 LLM **維護本體論（ontology）**，而非自由命名。

### 2.4 Tag 的階層與推理

Tag 不是平面的，而是有結構的。這對推理效率至關重要。

**IS-A 階層（繼承）**：
```
element
├── fire
│   ├── mundane_fire
│   └── spiritual_fire（如三昧真火）
├── water
└── ice
```

規則匹配時，`rule.trigger: element` 可以匹配所有子類的 tag。

**相互作用關係**：
```
ice overcomes fire
water conducts lightning
metal blocks magic（in some settings）
```

**Setting Pack 覆蓋**：基礎詞彙表來自框架，各 Setting Pack 可以擴展或覆蓋。武俠世界加上「金木水火土」五行相生相剋，詭秘世界加上「序列」、「途徑」、「非凡特性」。

### 2.5 Tag-based 查詢的威力

```python
# 直接 tag 匹配
find_entity(tags={fire, weapon})  # 所有火系武器

# 階層匹配
find_entity(tags={element/*, weapon})  # 任何元素武器

# 組合條件
find_entity(
    tags_any={fire, burning, scorching},
    tags_none={water_resistant},
    properties={tier: ">=2"}
)

# 推理查詢
find_entity(vulnerable_to={ice})  # 反向推理：什麼東西怕冰
```

最後一個最有趣——它本身就是一個 tag-based 的推理：系統知道 `fire` 怕 `ice`、`liquid` 遇 `freeze` 會變 `solid`，於是能回答「誰怕冰」。

### 2.6 實作考量

**反向索引**：`tag -> Set<EntityId>`。當問「所有帶 fire tag 的實體」時 O(1) 查詢。

**位元組壓縮**：如果 tag 總數不多（比如 < 256），可以用 bitmask 表示一個 entity 的 tag 集合，集合運算變成位運算，極快。

**持久化**：tags 可以和 entity 一起存，或單獨存在 `entity_tags` 關聯表。推薦後者，支持更靈活的查詢。

---

## 三、Rete 演算法深入

### 3.1 問題背景

假設有 1000 條規則和 10000 個事實（entities + their tags + properties），每次狀態變化時，需要找出「哪些規則現在可以觸發」。最笨的做法：

```
for rule in all_rules:           # 1000
    for fact_tuple in all_tuples: # 可能 10000^2 或更多
        if matches(rule, fact_tuple):
            trigger(rule)
```

這是 O(rules × facts^n) 的災難，n 是規則的條件數。真實的專家系統有幾萬條規則，這種做法完全跑不動。

Charles Forgy 在 1979 年的 Rete 演算法（希臘文「網」的意思）是對這個問題的經典回答。

### 3.2 Rete 的核心洞察

**三個關鍵觀察**：

1. **時間冗餘**：連續兩次狀態變化間，大部分事實不變。重新完整匹配是浪費。
2. **結構冗餘**：許多規則共享共同的條件。不應為每條規則重複計算相同的 pattern match。
3. **增量更新**：新增/刪除一個事實時，只需要更新受影響的規則，不需要重新計算所有。

Rete 的解法：**把規則編譯成一個 dataflow 網路，事實變化在網路中傳播，只有受影響的節點重新計算**。

### 3.3 Rete 網路的結構

```
Facts flowing in
       │
       ▼
┌──────────────┐
│ Alpha Nodes  │  # 單一 pattern 匹配
│  (per cond.) │  # 例：所有帶 fire tag 的實體
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Beta Nodes  │  # 多條件合併（join）
│ (joins)      │  # 例：fire_entity AND nearby_flammable
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Terminal     │  # 規則觸發
│ Nodes        │
└──────────────┘
```

**Alpha memory**：每個單一條件的匹配結果快取。例如節點「所有 `tag:fire` 的 entity」維護一個 set，新增/刪除 entity 時只更新這個 set。

**Beta memory**：多條件 join 的結果快取。例如「fire entity 且附近有 flammable 物體」維護所有滿足的 tuple。

**增量傳播**：新事實進入網路後，只沿著**受影響的路徑**傳播。如果新事實不匹配任何 Alpha 節點，立即停止。如果匹配某 Alpha 但後續 Beta 不滿足，停止。只有一路匹配到 Terminal，才觸發規則。

### 3.4 共享節點：結構冗餘消除

假設有規則：
- R1: `fire(X) AND flammable(Y) AND near(X, Y) → burn(Y)`
- R2: `fire(X) AND wooden(Y) AND near(X, Y) → special_burn(Y)`

兩條規則都有 `fire(X)` 和 `near(X, Y)`。Rete 編譯時會**共享這些節點**，只有在 `flammable(Y)` 和 `wooden(Y)` 處分叉。規則越多、共享越多，效率提升越顯著。

### 3.5 對我們框架的應用

我們的「標籤推理層」本質上就是需要 Rete 或類似技術：

```
規則庫：
    "fire AND flammable AND proximity -> ignition"
    "water AND electric_source AND living -> shock"
    "stealth_action AND perception_check AND success -> undetected"
    "combat_action AND advantage AND roll -> enhanced_damage"
    ...（可能幾百到幾千條）

每次玩家行動 / NPC 行動 / 環境變化，都要檢查觸發哪些規則。
```

樸素實作在規則數過百後性能崩潰。Rete 讓這個擴展到數千條仍然即時。

**現代實作選擇**：
- **Drools**（Java, JBoss）**：成熟，強大，但重
- **CLIPS**（C）**：NASA 開發，嵌入式友善
- **Experta**（Python）**：Python 版 CLIPS
- **自己實作簡化版**：對於中等規模規則，幾百行就能寫出夠用的 Rete 變體

### 3.6 Rete 的變體與擴展

**Rete II / III**（Forgy 後來的改進）：更好的 join order、更激進的共享。

**TREAT**：放棄部分 beta memory，在某些情境下更省記憶體但重算更多。

**LEAPS**：lazy evaluation，只在規則需要觸發時才完成匹配。

對我們的場景，**Rete 基礎版足矣**。真正的瓶頸通常不是演算法，而是規則本身的設計品質。

---

## 四、Datalog 深入

### 4.1 Datalog 是什麼

Datalog 是 Prolog 的一個子集——去掉了函數符號、遞迴結構，保留了純粹的邏輯規則。這個「削弱」看起來是限制，實際上是強大的保證：

- **保證終止**：任何 Datalog 查詢都會在有限時間內完成（Prolog 可以無限循環）
- **高效求解**：有多種經典演算法（semi-naive evaluation、magic sets）
- **聲明式**：只說「什麼是真」，不說「怎麼計算」
- **無副作用**：純函數式，易於推理

### 4.2 語法示例

```datalog
% 事實（facts）
is_fire(fireball_001).
is_flammable(wooden_crate_042).
position(fireball_001, room_a).
position(wooden_crate_042, room_a).

% 規則（rules）
ignites(X, Y) :- is_fire(X), is_flammable(Y), 
                 position(X, P), position(Y, P).

% 查詢（query）
?- ignites(X, Y).
% 返回：ignites(fireball_001, wooden_crate_042).
```

規則讀作：「X 點燃 Y，如果 X 是火、Y 可燃、且兩者在同一位置」。

### 4.3 遞迴查詢：Datalog 的超能力

這是 Datalog 相對 SQL 的最大優勢（雖然現代 SQL 有 CTE，但語法笨重）：

```datalog
% 「誰敵對誰」的傳遞推理
hostile(X, Y) :- directly_hostile(X, Y).
hostile(X, Y) :- hostile(X, Z), allied(Z, Y).

% 查詢
?- hostile(player, X).
% 返回所有傳遞敵對玩家的實體
```

或者組織關係：

```datalog
member_of(X, O) :- direct_member(X, O).
member_of(X, O) :- direct_member(X, sub_org), 
                   sub_organization(sub_org, O).

?- member_of(X, heishabang).
% 黑沙幫的所有成員（包括子組織的）
```

這對我們框架中的**關係推理**極為有用。

### 4.4 Datalog 與規則引擎的關係

Rete 是一種**執行策略**，Datalog 是一種**宣告語言**。二者不衝突，往往結合使用：

- **用 Datalog 定義規則**（宣告式、易讀、可驗證）
- **用 Rete 執行匹配**（增量、高效）

現代一些規則引擎（如 **DataFun**、**Differential Datalog**、**Soufflé**）正是這個路線：Datalog 語法 + 高效執行器。

### 4.5 對我們框架的應用

**常識推理規則**：
```datalog
% 元素克制
overcomes(ice, fire).
overcomes(fire, wood).
overcomes(water, fire).

% 派生規則
advantage_against(X, Y) :- has_element(X, E1), 
                            has_element(Y, E2), 
                            overcomes(E1, E2).
```

**NPC 反應規則**：
```datalog
% 直接負面印象
negative_impression(N, P) :- witnessed(N, event_harm(P, ally(N))).

% 傳遞不信任
distrusts(N, P) :- negative_impression(N, P).
distrusts(N, P) :- trusts(N, M), distrusts(M, P), 
                   close_relationship(N, M).
```

**訪問控制（「誰知道什麼」）**：
```datalog
knows(N, fact(F)) :- witnessed(N, event_of(F)).
knows(N, fact(F)) :- told_by(N, M, F), trusts(N, M).

% 查詢：NPC 對話時該 NPC 知道哪些相關事實？
?- knows(han_ying, fact(F)), relevant_to(F, current_topic).
```

### 4.6 與向量檢索的分工

前面提到「純結構化查詢處理不了『找出和這次類似的情境』」，這正是 Datalog 的弱點——它做精確邏輯推理，不做語義相似。

**正確的分工**：
- **結構化事實與因果關係** → Datalog（精確、可解釋、可審計）
- **語義相似、模糊匹配，自然語言意圖** → 向量檢索

兩者的結果再合併，餵給 LLM。

### 4.7 實作選擇

對我們的場景：
- **Soufflé**：C++ 實作，極快，但 build system 複雜
- **pyDatalog**：純 Python，易整合，性能一般
- **Differential Datalog**：支持增量更新，適合狀態頻繁變動
- **自己實作**：Datalog 核心演算法不複雜，幾百行 Python 能寫出教學版

務實建議：初期用 pyDatalog 或自己寫簡化版，規模上去後再考慮 Soufflé。

---

## 五、四者結合的完整圖像

回到我們的框架，這四個技術的定位：

```
┌─────────────────────────────────────────────────┐
│  World representation（世界表示）                  │
│                                                   │
│  ECS: 實體結構（Entity + Components）             │
│  Tags: 實體的概念屬性（語義標籤）                 │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│  Knowledge representation（知識表示）              │
│                                                   │
│  Datalog: 規則與因果關係的宣告式定義              │
│  Controlled Vocabulary: tag 本體論               │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│  Inference execution（推理執行）                   │
│                                                   │
│  Rete: 高效的規則匹配與觸發                      │
│  Reverse indexes: tag 快速查詢                   │
└─────────────────────────────────────────────────┘
```

**具體流程**：

1. 玩家行動產生事件 → 事件修改 ECS 中某些 component、增減某些 tag
2. 狀態變化通過 Rete 網路傳播 → 命中相關規則
3. 規則可能是 Datalog 形式的宣告（易於 Setting Pack 作者編寫）
4. 規則觸發產生更多事件 → 級聯推理
5. 最終的確定性結果交給數值引擎計算
6. 無法用規則處理的情況才降級到 LLM 裁決

---

## 六、幾個重要的注意事項

**不要過早引入 Rete**。規則數在幾十條以內時，純粹的線性遍歷就夠快。Rete 的複雜度在規則設計、調試、增量更新管理上，小系統不划算。**當規則數突破 100 且性能成問題時**，再引入。

**Datalog 的學習曲線**。對習慣 imperative 編程的開發者，宣告式邏輯需要心智轉換。但 Setting Pack 作者往往不是程式員，Datalog 的宣告式反而更接近他們「寫設定書」的思維。所以這是對工程師的挑戰，對作者的幫助。

**Tag 詞彙表的治理成本**。技術上不難，治理上很難。誰有權新增 tag？新 Setting Pack 如何避免 tag 衝突？這些是**社會層面的問題**，需要配套的審核流程，類似維基百科的社群治理。

**ECS 不是萬能銀彈**。某些涉及複雜繼承層次的邏輯用 OOP 仍然更自然。不必強迫所有代碼都 ECS 化。框架核心用 ECS，但具體規則的執行邏輯（如技能的效果鏈）用普通類別更清晰。

**演算法重要，但設計品質更重要**。Rete 讓一千條垃圾規則跑得飛快，但結果仍然是垃圾。真正花時間的地方應該是**設計好那一百條核心規則**，而不是優化幾千條湊數的。

---

## 七、從哪裡開始學

**ECS**：
- Scott Bilas 的 GDC 2002 talk "A Data-Driven Game Object System"
- Adam Martin 的部落格系列 "Entity Systems are the future of MMOG development"
- Bevy 的 ECS 文件（最現代，最優雅的範例之一）
- Unity DOTS 的官方文件（工業級實作）

**Tag system**：
- Evennia MUD 引擎的 tag 設計（實用主義路線）
- Unreal 的 GameplayTags 系統（大型遊戲的成熟方案）
- OWL / RDF 的本體論設計（學術路線，過於重但有啟發）

**Rete**：
- Charles Forgy 1982 年的原始論文 "Rete: A Fast Algorithm for the Many Pattern/Many Object Pattern Match Problem"
- Robert Doorenbos 的博士論文（Rete 變體的完整分析）
- Drools 的 source code（工業實作）

**Datalog**：
- Abiteboul、Hull、Vianu 的 "Foundations of Databases"（理論基石）
- Soufflé 的 tutorial（現代實作視角）
- "The Essence of Datalog" 系列部落格文章

這四個技術合起來，為我們的框架提供了**從實體表示，到知識編碼，到高效推理**的完整工具鏈。它們都不是新技術——ECS 二十多年、Rete 四十多年、Datalog 五十多年——但這種成熟正是優勢：陷阱都被踩過了，最佳實踐都有文獻，社群支援完整。

在 LLM 時代重新審視這些技術，會發現它們不但沒過時，反而恰好是**LLM 難以替代的那一半**：LLM 做不好精確邏輯、確定性推理、大規模事實維護，而這些正是 ECS+Tag+Rete+Datalog 的強項。這也再次呼應框架的核心哲學——**讓確定性的歸於代碼，讓表達性的歸於 LLM**。
