# 设计参考

先在 GitHub 搜索公开高星项目，再开始整合。2026-10-21 通过 GitHub API
记录以下星数；星数会变化，它们只帮助选择结构范例，不证明地理数据可靠性。

| 项目 | 当日 stars | 阅读内容与借鉴 |
|---|---:|---|
| [anthropics/skills](https://github.com/anthropics/skills) | 182,525 | README、skills/skill-creator/SKILL.md：Skill 元数据、按需展开的参考、脚本和说明分工 |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | 35,858 | README：短入口、清楚的命令表和能力范围 |
| [drivendataorg/cookiecutter-data-science](https://github.com/drivendataorg/cookiecutter-data-science) | 10,102 | README：不可变原始证据、过程数据与输出分离 |
| [othneildrew/Best-README-Template](https://github.com/othneildrew/Best-README-Template) | 16,408 | README：先解释用途，再给安装、使用和许可入口；不照搬宣传语和装饰 |
| [openai/skills](https://github.com/openai/skills) | 28,194 | README：核查技能目录结构；该仓库已声明弃用，不作为当前安装入口 |

初始搜索包括 `agent skills stars:>10000`、`readme template stars:>10000`、
`geospatial workflow stars:>1000`。最后一项未返回结果，随后直接核查了与
可复现科学项目组织有关的 Cookiecutter Data Science。没有发现并验证一个
可直接替代这三个 UNESCO 仓库的高星整合项目。

新仓库采用的是这些项目的组织方法，未把其代码复制进来。具体的边界来源
优先级、组件覆盖和地图配准规则来自原 UNESCO 仓库，并经过本次代码核对。
README 保留用途、流程、命令、输出、限制和许可；详细证据留在 docs。
