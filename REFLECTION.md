# Final Reflection

> 本文档初稿由我自己完成，后期利用ai主要进行markdown文件格式的转化以及部分专业词汇的润色

这次项目我做的是 PyRepair Agent，一个面向小型 Python + pytest 项目的 Coding Agent Harness。刚开始我以为 harness engineering 可能就是写好 prompt、接上 API key，剩下的就可以完全交给 ai了。做完以后我才明白，LLM 只是提出下一步动作，真正让系统可靠的是外面的工程层：动作格式、工具分发、测试反馈、护栏、停止条件、日志、凭据和分发。我的主贡献是 pytest feedback loop：运行测试，把 pytest 输出解析成结构化反馈，再喂回 agent，让它下一轮改变动作。这个机制能用 mock LLM 稳定测试，所以不是只靠模型“自己聪明”。

Superpowers 里作用最大的是 `brainstorming`、`writing-plans`、`test-driven-development` 和 `verification-before-completion`。前两个帮我从很大的 coding agent 缩到 Test-Repair Coding Agent，并拆成小 task；后两个逼我先写测试、再实现，且不能在没有证据时说“完成”。也有一些技能和日志我觉得形式大于实质，尤其是 task 很小时流程显得重, 甚至导致我的 tokens消耗的非常快 (让我不得已重置了 codex的周额度)。但如果它能产生约束，比如诚实记录 `make test` 在 Windows 本机无法运行，而不是假装通过，这种“形式”反而变成了证据。在 token预算有限的前提下，工程师就要考虑一个平衡。但这个 skill也并非完美的。经过我的亲身实践，brainstorm确实可以帮你找到一些没有确定的边界问题，让你来觉得具体实现细节，但容易成为走个流程，ai有自己的推荐，而我往往就是按 ai的推荐来选择细节的实现。再者，它提出的问题数量也有限，不足以完全覆盖细节实现，就比如说，我的第一次尝试中 ai就没有询问是否要接入真实 api密钥，而是直接默认选择 mock LLM来减少任务量，但这可能不符合我的预期。所以，就单论 `brainstorming`这个 skill而言，它仍存在着提出的问题是否有意义，是否覆盖了所有细节实现分支等问题。还有一点就是，我看网络上有一种言论，随着近期chatgpt 5.6的升级，有些 Superpowers的功能已经被潜在的包括进 LLM自身中了，再额外安装 Superpowers反而会导致模型变得更重。但因为我目前尝试的少且缺少经验，没有感受到较大的区别。本段落仅提出一些我对 Superpowers的了解、实践与疑惑。

TDD 在 AI 协作下，一开始像阻碍。AI 明明可以直接写实现，却要先写失败测试、跑红、再写代码。但后面我觉得它更像一个放大器。AI 写代码很快，也很容易自信地错，它可能按照自己臆想而非工程师的思路来完成代码。guardrail、patch applier、secret redaction 里的很多问题，是靠回归测试逼出来的。TDD 把“我觉得对”变成了“这个行为被确定验证过”。

subagent-driven 工作流能让智能体自主运行多久，取决于 task 颗粒度。如果 task 清楚，它可以在一个小模块内完成红绿测试、实现和局部验证；如果 task 跨太多边界，就容易偏离。我感觉最优颗粒度是“一个可验收行为一个 task”。例如“实现 action parser 并覆盖非法 JSON、未知动作、缺字段”比较合适；“完成 CLI + WebUI + 凭据”太大。因为现在缺少足量的测试样本，我只能根据 ai的推荐来解释，对于完成本作业的 coding agent，我预计使用 14-20个task为佳。

SPEC / PLAN 的质量直接影响实现质量。最具体的例子是 cold-start validation即冷启动。一个没有前面对话记忆的 agent 只看 `SPEC.md` 和 `PLAN.md` 去尝试 Task 3 时，发现 enum、dataclass 字段、默认值、嵌套关系都不够明确。如果不提前发现，subagent 可能会自己猜字段名和状态值，导致 parser、store、core loop 后面都不一致。后来我让 ai补充了 Data Model、enum value、字段默认值和序列化规则，Task 3 才变得可执行。这让我意识到，SPEC 不是漂亮文档，而是给“没有共同记忆的执行者”看的接口合同。

我最有效的 prompt / context 策略是少给泛泛目标，多给边界、证据和停止条件。比如我反复强调“只能自动修改 Python 源码，默认不改测试”“遇到权限问题必须停下来告诉我”“不要绕过审批”。这些不是风格偏好，而是直接限制 agent 的行动空间。另一个有效策略是让 agent 对照 `SPEC.md`、`PLAN.md`、`AGENT_LOG.md`，而不是只靠聊天记忆继续。

凭据和分发这两条要求，逼我想清楚了很多原本会忽略的问题。凭据方面，我原来以为用户提供 API key 就行，后来才发现重点是 key 会不会出现在命令行历史、日志、配置文件、异常 traceback、WebUI 或 Git 历史里，所以项目需要 hidden input、key status 不回显、log redaction，真实 API smoke test 也只能记录非敏感结果。分发方面，我原来只关心本机能跑，后来 Docker、CI、公开 WebUI 让我意识到“别人从零运行”还要考虑依赖、测试命令和公网安全边界。

如果重做一次，我会更早准备最终仓库、PR、CI 和部署路径，而不是后面再补证据。我也会把 PLAN 拆得更均匀，因为有些 task 后来经历了很多 review fix，说明边界还可以更清楚。WebUI 方面，我会更早区分本地真实 repair console 和公网 mock-only demo。

我对 Superpowers 的批判是：它假设开发者愿意慢下来，愿意维护文档、计划、日志和测试，也假设 task 可以被拆成清楚的小块。在我的项目里这些假设大部分成立，因为 PyRepair Agent 本身强调机制和证据；但如果是探索性很强、需求变化很快的项目，Superpowers 可能会显得重。它还假设“更多流程能减少偏离”，但流程只有认真执行才有用。如果只是为了满足表格而调用技能，反而会制造噪音。总体来说，这个项目让我看到，AI4SE 里的工程师角色不是被 AI 替代，而是从“逐行写代码的人”变成“定义边界、设计反馈、验证结果、承担责任的人”。
