# user-collaboration

一个让模型与使用者配合更默契的 Codex 技能：处理用户提供路径/文本时的歧义与矛盾，稳定应用用户的约定，并在发布前清理个人信息。

## 安装

把 `user-collaboration` 文件夹复制到 Codex 全局技能目录：

```
$CODEX_HOME/skills/user-collaboration/
```

`CODEX_HOME` 未设置时默认为 `~/.codex`。也可以在任务中显式调用 `$user-collaboration`。

## 内容

- 路径与事实核实：创建前先验证，冲突时列目录确认
- 识别转义/渲染产物（如 `\_` 表示普通下划线）
- 矛盾时停下来，给出具体候选解读让用户选择
- 多轮协作中保持一致的用户约定
- 公开发布前的个人信息清理
