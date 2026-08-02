---
kind: frontend_style
name: DSA Web 前端样式系统：Tailwind CSS v4 + CSS 变量主题体系
category: frontend_style
scope:
    - '**'
source_files:
    - apps/dsa-web/tailwind.config.js
    - apps/dsa-web/src/index.css
    - apps/dsa-web/src/components/theme/ThemeProvider.tsx
    - apps/dsa-web/src/utils/cn.ts
    - apps/dsa-web/package.json
---

## 1. 使用的系统与工具
- **框架与构建**：React 19 + Vite 7，TypeScript 5.9，ESLint。
- **CSS 原子化方案**：Tailwind CSS v4（`tailwindcss@^4.1.18`），通过 `@import "tailwindcss"` + `@config "../tailwind.config.js"` 引入配置。
- **主题切换**：`next-themes` 作为 ThemeProvider，以 `class="dark"` 模式驱动明暗主题。
- **类名合并**：统一使用 `clsx` + `tailwind-merge` 封装的 `cn()` 工具函数进行 className 合并。
- **图标库**：`lucide-react`、`@remixicon/react`。
- **动画**：`motion`（Framer Motion）+ Tailwind 自定义 keyframes/animation。
- **图表**：`recharts`。
- **状态管理**：`zustand`（非样式相关，但影响组件渲染结构）。

## 2. 核心文件与位置
- **Tailwind 配置**：`apps/dsa-web/tailwind.config.js` — 定义颜色、阴影、圆角、动画等扩展。
- **全局样式入口**：`apps/dsa-web/src/index.css` — 导入 Tailwind、声明所有 CSS 变量（设计令牌）、定义基础层与组件层样式。
- **主题提供者**：`apps/dsa-web/src/components/theme/ThemeProvider.tsx` — 基于 `next-themes` 的 ThemeProvider。
- **类名合并工具**：`apps/dsa-web/src/utils/cn.ts` — `clsx` + `twMerge` 封装。
- **应用根样式**：`apps/dsa-web/src/App.css` — 仅设置 `#root` 宽高。
- **页面与组件**：`src/pages/*`、`src/components/*` — 大量使用 Tailwind 原子类 + CSS 变量。

## 3. 架构与设计约定
### 3.1 设计令牌（Design Tokens）体系
- 所有颜色、阴影、圆角、间距等通过 CSS 自定义属性（`--background`、`--primary`、`--shadow-soft-card` 等）集中定义在 `index.css` 的 `:root` 和 `.dark` 块中。
- Tailwind 配置中的颜色全部映射到 HSL 变量（如 `primary: hsl(var(--primary))`），实现主题色一键切换。
- 语义化 token 分层：
  - 基础层：`--background`、`--foreground`、`--card`、`--primary`、`--destructive` 等。
  - 派生层：`--bg-subtle`、`--border-dim`、`--surface-1/2/3`、`--overlay-hover` 等。
  - 业务层：`--home-*`、`--login-*`、`--chat-*`、`--backtest-*`、`--settings-*` 等页面/功能域专用 token。

### 3.2 明暗主题策略
- 通过 `next-themes` 的 `attribute="class"` 模式，在 `<html>` 或根节点上切换 `class="dark"`。
- `index.css` 中为每个 token 提供 light/dark 两套值，组件无需关心主题，直接使用变量。
- 默认主题为 `dark`，支持系统主题跟随（`enableSystem`）。

### 3.3 样式组织方式
- **Tailwind 原子类**：组件内大量使用 `className="..."` 直接写原子类（如 `bg-base`、`text-primary`、`border-border/60`）。
- **CSS 变量**：复杂样式（渐变、阴影、动画、特定组件样式）通过 `index.css` 中的 `.xxx` 类 + CSS 变量组合。
- **@layer 分层**：`base` 层定义全局基础样式，`components` 层定义可复用组件样式。
- **@apply 组合**：部分样式通过 `@apply` 组合多个原子类（如 `.glass-panel`）。

### 3.4 组件样式约定
- 通用 UI 组件集中在 `src/components/common/`，遵循统一的命名与结构。
- 业务组件按功能域分目录（`alerts/`、`dashboard/`、`report/`、`settings/` 等）。
- 所有组件通过 `cn()` 工具合并 className，避免冲突。

## 4. 约定与约束
- **必须使用 Tailwind 原子类**：组件样式优先使用 `className` 中的 Tailwind 类，而非自定义 CSS。
- **颜色必须通过 CSS 变量**：禁止硬编码颜色值，统一使用 `var(--xxx)` 或 Tailwind 的颜色别名。
- **主题切换通过 class="dark"**：所有主题相关逻辑通过 `next-themes` 管理，禁止手动操作 DOM 切换主题。
- **类名合并必须用 cn()**：组件 props 中的 className 必须通过 `cn()` 合并，确保样式优先级正确。
- **响应式断点**：使用 Tailwind 内置断点（sm/md/lg/xl/2xl），在 `tailwind.config.js` 中扩展了 `2xl: 1400px`。
- **动画规范**：预定义的动画（`fade-in`、`slide-up`、`pulse-glow` 等）通过 Tailwind 配置注册，组件直接使用 `animate-*` 类。
- **Glassmorphism 风格**：通过 `.glass-panel`、`.glass-panel-lg` 等类提供毛玻璃效果，配合 backdrop-blur 和半透明背景。
- **财务终端风格**：整体采用深色科技风，主色调为青色（cyan, `hsl(193 100% 43%)`），辅以紫色（purple）和绿色（success）作为状态色。