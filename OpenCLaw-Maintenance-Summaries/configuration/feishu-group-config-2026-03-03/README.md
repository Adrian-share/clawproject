# 飞书群聊免 @ 配置总结

**日期：** 2026-03-03
**问题大类：** configuration（配置管理）
**子文件夹：** feishu-group-config-mention
**相关文件：** feishu-config-summary.md

---

## 问题描述

### 用户需求
用户希望配置 OpenClaw 飞书机器人，使其在指定的 3 个群聊中不需要 @ 机器人就能直接接收和回复消息。

### 初始配置
- App ID: cli_a92c50497b38dbc8
- App Secret: CBvKrlRpfb1joUe0976iFdI6A61vUzO5
- 目标群聊：
  - oc_c40ece83ffc5509c9be2ecacd2ac6ea0
  - oc_3e778d3a5943b92742149a4cc0f70a20
  - oc_1e85847c0d79770f3f968e51606fb44c

### 遇到的问题
完成 OpenClaw 配置后，机器人在群聊中仍然需要 @ 才能响应，无法实现免 @ 回复功能。

---

## 解决方案

### 步骤 1：安装飞书官方插件

**操作：**
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

**结果：**
- feishu-openclaw-plugin 插件成功安装（版本 2026.2.28.11）
- 注册了大量 OAPI 工具（文档、日历、任务、多维表格等）
- 内置 feishu 插件已禁用

### 步骤 2：配置飞书渠道参数

**操作：**
```bash
openclaw config set channels.feishu.domain feishu
openclaw config set channels.feishu.connectionMode websocket
openclaw config set channels.feishu.dmPolicy open
openclaw config set channels.feishu.groupPolicy allowlist
openclaw config set channels.feishu.requireMention false
```

**结果：**
- 全局 requireMention 设置为 false
- 群聊策略设置为白名单模式（allowlist）

### 步骤 3：配置群组白名单

**操作：**
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

**结果：**
- 3 个群组已添加到白名单
- 每个群组都设置了 requireMention: false

### 步骤 4：调整消息策略

**操作：**
```bash
openclaw config set messages.ackReactionScope all
```

**结果：**
- 消息反应范围设置为 all，机器人会对所有消息做出反应

### 步骤 5：问题诊断与发现

**排查过程：**
1. 检查飞书渠道状态 - 显示运行正常
2. 检查 Gateway 日志 - 无错误信息
3. 多次重启服务 - 问题仍然存在
4. 用户反馈提供关键信息

**关键发现：**
用户提供的信息指出，问题的根源不是 OpenClaw 配置，而是**飞书开放平台的敏感权限**：

> "申请飞书敏感权限：登录飞书开放平台，进入应用的「权限管理」，申请「获取群组中所有消息」（im:message.group_msg）权限（该权限需企业管理员审批，需说明申请原因）。"

### 步骤 6：生成权限申请指南

**操作：**
生成详细的权限申请文档，包含：
- 权限申请说明（可直接复制使用）
- 飞书开放平台配置步骤
- 事件订阅配置说明
- 常见问题解答

**文档位置：** `/tmp/feishu_permission_guide.md`

---

## 核心配置

### 完整的 openclaw.json 配置

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

**必须申请的敏感权限：**
- `im:message.group_msg` - 获取群组中所有消息

**必须配置的事件订阅：**
- `im.message.receive_v1` - 接收消息事件
- 连接模式：长连接（WebSocket）

**权限申请说明：**
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

---

## 参考材料

### 官方文档
- OpenClaw 官方文档：https://docs.openclaw.ai/
- 飞书开放平台：https://open.feishu.cn/
- 飞书权限列表：https://open.feishu.cn/document/ukTMukTMukTM/uUjNzUjL2YTM14iN2ATN

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

## 整体总结

### 问题本质
这是一个**权限问题**，而非配置问题。OpenClaw 的所有配置都是正确的，但由于缺少飞书开放平台的敏感权限 `im:message.group_msg`，机器人无法接收群组中的所有消息，只能接收 @ 机器人的消息。

### 解决流程
1. ✅ 安装飞书官方插件
2. ✅ 配置飞书渠道参数
3. ✅ 配置群组白名单
4. ✅ 设置 requireMention 为 false
5. ✅ 调整消息策略
6. ⏳ **等待飞书平台权限审批**（用户侧操作）

### 关键经验
1. **区分配置问题和权限问题**：OpenClaw 配置正确不代表功能就能正常工作，还需要平台侧的权限支持。
2. **敏感权限需要审批**：`im:message.group_msg` 是敏感权限，必须经过企业管理员审批。
3. **详细记录配置过程**：在排查问题时，详细的配置记录有助于快速定位问题根源。
4. **用户反馈至关重要**：用户提供的官方文档信息是解决问题的关键。

### 后续步骤
1. 用户在飞书开放平台申请 `im:message.group_msg` 权限
2. 管理员审批权限
3. 发布应用版本
4. 测试群聊免 @ 回复功能

### 风险提示
- `im:message.group_msg` 权限会让机器人能够读取群组中所有消息，需要谨慎申请
- 建议仅在企业内部环境使用，并严格控制白名单群组
- 定期审查机器人的使用情况和权限范围

---

**维护人员：** OpenClaw 配置专家
**维护时间：** 2026-03-03
**状态：** 配置完成，等待飞书平台权限审批