# 飞书群聊免 @ 配置维修总结

## 基本信息
- **维修日期**: 2026-03-03
- **维修人员**: OpenClaw 配置专家
- **影响版本**: OpenClaw 2026.3.1
- **严重程度**: 中
- **问题大类**: configuration（配置管理）

---

## 1. 问题描述

### 问题现象
用户希望配置 OpenClaw 飞书机器人在指定的 3 个群聊中不需要 @ 机器人就能直接接收和回复消息。完成 OpenClaw 配置后，机器人在群聊中仍然需要 @ 才能响应，无法实现免 @ 回复功能。

### 问题影响
- **功能影响**：机器人无法在群聊中自动响应，用户必须 @ 机器人才能触发回复
- **用户体验**：增加了用户的操作负担，降低了机器人的便利性
- **潜在风险**：如果不了解真实原因，可能导致配置错误和无效的调试尝试

### 初步排查
1. 检查飞书渠道状态 - 显示运行正常
2. 检查 Gateway 日志 - 无错误信息
3. 多次重启服务 - 问题仍然存在
4. 验证 requireMention 配置 - 已正确设置为 false
5. 验证群组白名单 - 已正确配置 3 个群组
6. **关键发现**：用户提供官方文档信息，指出需要飞书平台权限

---

## 2. 解决方案

### 根本原因
问题的根源不是 OpenClaw 配置错误，而是**飞书开放平台的敏感权限缺失**。

飞书机器人在群聊中需要申请敏感权限 `im:message.group_msg`（获取群组中所有消息）才能接收群组中的所有消息。如果只配置了 OpenClaw 侧的参数而没有申请这个权限，机器人只能接收 @ 它的消息，无法接收群组中所有消息。

### 解决步骤

#### 步骤一：安装飞书官方插件

**操作命令**：
```bash
# 禁用内置 feishu 插件
openclaw config set plugins.entries.feishu.enabled false

# 下载并安装官方插件
curl -o /tmp/feishu-openclaw-plugin.tgz https://sf3-cn.feishucdn.com/obj/open-platform-opendoc/22fb1b6c108fd389ba98bf9058b93a20_iuFdixhege.tgz
openclaw plugins install /tmp/feishu-openclaw-plugin.tgz
rm /tmp/feishu-openclaw-plugin.tgz

# 配置插件白名单
openclaw config set plugins.allow '["feishu-openclaw-plugin"]'
```

**结果**：
- feishu-openclaw-plugin 插件成功安装（版本 2026.2.28.11）
- 注册了大量 OAPI 工具（文档、日历、任务、多维表格等）
- 内置 feishu 插件已禁用

---

#### 步骤二：配置飞书渠道参数

**操作命令**：
```bash
openclaw config set channels.feishu.domain feishu
openclaw config set channels.feishu.connectionMode websocket
openclaw config set channels.feishu.dmPolicy open
openclaw config set channels.feishu.groupPolicy allowlist
openclaw config set channels.feishu.requireMention false
```

**结果**：
- 全局 requireMention 设置为 false
- 群聊策略设置为白名单模式（allowlist）
- 连接模式设置为 WebSocket（长连接）

---

#### 步骤三：配置群组白名单

**操作命令**：
```bash
# 配置第一个群组
openclaw config set channels.feishu.groups.oc_c40ece83ffc5509c9be2ecacd2ac6ea0.enabled true
openclaw config set channels.feishu.groups.oc_c40ece83ffc5509c9be2ecacd2ac6ea0.groupPolicy open
openclaw config set channels.feishu.groups.oc_c40ece83ffc5509c9be2ecacd2ac6ea0.requireMention false

# 配置第二个群组
openclaw config set channels.feishu.groups.oc_3e778d3a5943b92742149a4cc0f70a20.enabled true
openclaw config set channels.feishu.groups.oc_3e778d3a5943b92742149a4cc0f70a20.groupPolicy open
openclaw config set channels.feishu.groups.oc_3e778d3a5943b92742149a4cc0f70a20.requireMention false

# 配置第三个群组
openclaw config set channels.feishu.groups.oc_1e85847c0d79770f3f968e51606fb44c.enabled true
openclaw config set channels.feishu.groups.oc_1e85847c0d79770f3f968e51606fb44c.groupPolicy open
openclaw config set channels.feishu.groups.oc_1e85847c0d79770f3f968e51606fb44c.requireMention false
```

**结果**：
- 3 个群组已添加到白名单
- 每个群组都设置了 requireMention: false
- 群组策略设置为 open

---

#### 步骤四：调整消息策略

**操作命令**：
```bash
openclaw config set messages.ackReactionScope all
```

**结果**：
- 消息反应范围设置为 all，机器人会对所有消息做出反应

---

#### 步骤五：问题诊断与发现

**排查过程**：
1. 检查飞书渠道状态 - 显示运行正常
2. 检查 Gateway 日志 - 无错误信息
3. 多次重启服务 - 问题仍然存在
4. 用户反馈提供关键信息

**关键发现**：
用户提供的信息指出，问题的根源不是 OpenClaw 配置，而是**飞书开放平台的敏感权限**：

> "申请飞书敏感权限：登录飞书开放平台，进入应用的「权限管理」，申请「获取群组中所有消息」（im:message.group_msg）权限（该权限需企业管理员审批，需说明申请原因）。"

---

#### 步骤六：生成权限申请指南（用户侧操作）

**操作**：
生成详细的权限申请文档，包含：
- 权限申请说明（可直接复制使用）
- 飞书开放平台配置步骤
- 事件订阅配置说明
- 常见问题解答

**用户侧需要完成的操作**：

1. 登录飞书开放平台（open.feishu.cn）
2. 进入应用 → 权限管理
3. 申请权限：`im:message.group_msg`

**权限申请说明**：
```
申请原因：
使用 OpenClaw AI 助手在飞书群聊中自动响应消息，帮助团队提升工作效率。

应用场景：
1. 智能问答：机器人直接回复群内问题，无需 @ 机器人
2. 自动任务处理：识别群内指令并执行相关操作
3. 知识库查询：自动检索企业知识库并返回相关信息

安全性说明：
- 机器人仅在白名单群组中启用（已配置 3 个指定群组）
- 不会主动外发群组消息
- 所有操作均有日志记录，可追溯

审批后，机器人将在指定群组中提供 24/7 智能服务。
```

4. 等待企业管理员审批
5. 发布应用版本
6. 测试群聊免 @ 回复功能

---

### 验证方法

**验证步骤**：
1. 在以下任一群聊中直接发送消息（无需 @ 机器人）：
   - oc_c40ece83ffc5509c9be2ecacd2ac6ea0
   - oc_3e778d3a5943b92742149a4cc0f70a20
   - oc_1e85847c0d79770f3f968e51606fb44c

2. 测试消息："你好" 或 "测试一下"

3. 机器人应该能够直接回复

**预期结果**：
- 权限审批通过后，机器人可以免 @ 回复
- 单聊功能不受影响，继续保持开放策略

---

## 3. 参考材料

### 相关文档
- [OpenClaw 官方文档](https://docs.openclaw.ai/)
- [飞书开放平台](https://open.feishu.cn/)
- [飞书权限列表](https://open.feishu.cn/document/ukTMukTMukTM/uUjNzUjL2YTM14iN2ATN)
- [飞书机器人官方插件文档](https://sf3-cn.feishucdn.com/obj/open-platform-opendoc/22fb1b6c108fd389ba98bf9058b93a20_iuFdixhege.tgz)

### 配置文件
- OpenClaw 配置：`/workspace/projects/openclaw.json`
- 权限申请指南：`/tmp/feishu_permission_guide.md`

### 命令参考
```bash
# 检查渠道状态
openclaw channels status --probe

# 检查完整状态
openclaw status --all

# 查看配置
openclaw config get channels.feishu

# 诊断配置
openclaw doctor

# 重启服务
sh /workspace/projects/scripts/restart.sh
```

---

## 4. 核心配置

### 配置变更

**变更前**：
- 使用内置 feishu 插件
- 未配置群组白名单
- requireMention 使用默认值（true）

**变更后**：
```json
{
  "channels": {
    "feishu": {
      "appId": "cli_a92c50497b38dbc8",
      "appSecret": "CBvKrlRpfb1joUe0976iFdI6A61vUzO5",
      "dmPolicy": "open",
      "connectionMode": "websocket",
      "allowFrom": ["*"],
      "groupPolicy": "allowlist",
      "requireMention": false,
      "groups": {
        "oc_c40ece83ffc5509c9be2ecacd2ac6ea0": {
          "enabled": true,
          "groupPolicy": "open",
          "requireMention": false
        },
        "oc_3e778d3a5943b92742149a4cc0f70a20": {
          "enabled": true,
          "groupPolicy": "open",
          "requireMention": false
        },
        "oc_1e85847c0d79770f3f968e51606fb44c": {
          "enabled": true,
          "groupPolicy": "open",
          "requireMention": false
        }
      }
    }
  },
  "messages": {
    "ackReactionScope": "all"
  },
  "plugins": {
    "allow": ["feishu-openclaw-plugin"],
    "entries": {
      "feishu": {
        "enabled": false
      }
    }
  }
}
```

### 飞书开放平台配置要求

**必须申请的敏感权限**：
- `im:message.group_msg` - 获取群组中所有消息

**必须配置的事件订阅**：
- `im.message.receive_v1` - 接收消息事件
- 连接模式：长连接（WebSocket）

### 依赖项

**新增插件**：
- feishu-openclaw-plugin（版本 2026.2.28.11）

**插件能力**：
- 消息：读取历史、发送回复、消息搜索
- 文档：创建/读取/更新云文档
- 多维表格：增删改查、批量操作
- 日历日程：日程管理、参会人管理
- 任务：任务/清单/子任务管理

---

## 5. 总结与反思

### 关键经验

1. **区分配置问题和权限问题**
   - OpenClaw 配置正确不等于功能可用
   - 平台侧的权限配置同样重要

2. **敏感权限需要审批**
   - `im:message.group_msg` 是敏感权限
   - 必须经企业管理员审批
   - 需要详细说明申请原因

3. **详细记录配置过程**
   - 便于快速排查问题
   - 为后续维护提供参考
   - 有助于知识积累

4. **用户反馈至关重要**
   - 用户提供的官方文档信息是解决问题的关键
   - 及时收集和利用用户反馈可以提高效率

### 避坑指南

1. **不要忽略平台权限**
   - 配置 OpenClaw 时，同步检查飞书开放平台配置
   - 确认所有必要的权限都已申请

2. **优先检查官方文档**
   - 飞书机器人配置有特殊的权限要求
   - 官方文档通常包含最新的配置指南

3. **耐心等待权限审批**
   - 敏感权限审批可能需要时间
   - 在此期间可以完成其他配置准备工作

4. **白名单模式更安全**
   - 相比全局开放，白名单模式更可控
   - 建议仅启用必要的群组

### 后续改进

1. **自动化权限检查**
   - 可以添加脚本检查飞书平台权限状态
   - 提前提示用户申请所需权限

2. **配置验证工具**
   - 开发配置验证工具
   - 自动检测配置中的潜在问题

3. **文档完善**
   - 补充更多飞书配置场景的文档
   - 提供更多的故障排查指南

### 相关 Issue
- 无

---

## 附录

### 相关日志

**渠道状态检查**：
```
Checking channel status…
Gateway reachable.
- Feishu default: enabled, configured, running
```

**插件加载状态**：
```
Plugins (1/39 loaded)
┌──────────────┬──────────┬──────────┬─────────────────────────────────┐
│ Name         │ ID       │ Status   │ Version                          │
├──────────────┼──────────┼──────────┼─────────────────────────────────┤
│ Feishu       │ feishu-  │ loaded   │ 2026.2.28.11                     │
│              │ openclaw │          │                                 │
│              │ -plugin  │          │                                 │
└──────────────┴──────────┴──────────┴─────────────────────────────────┘
```

### 测试用例

**测试场景 1：单聊测试**
- 步骤：在飞书中向机器人发送"你好"
- 预期：机器人能够正常回复
- 结果：✅ 通过

**测试场景 2：群聊 @ 测试**
- 步骤：在群聊中 @ 机器人发送"你好"
- 预期：机器人能够正常回复
- 结果：✅ 通过

**测试场景 3：群聊免 @ 测试（待权限审批）**
- 步骤：在群聊中直接发送"你好"（无需 @）
- 预期：机器人能够正常回复
- 结果：⏳ 等待飞书平台权限审批

### 备注

1. **权限审批时间**：敏感权限审批可能需要 1-3 个工作日
2. **权限有效期**：权限审批通过后长期有效，除非手动撤销
3. **安全性提醒**：`im:message.group_msg` 权限会让机器人读取群组所有消息，建议仅在可控环境中使用
4. **监控建议**：建议定期检查机器人的使用情况和权限范围

---

**文档版本**: v1.0
**最后更新**: 2026-03-03
**维护人员**: OpenClaw 配置专家