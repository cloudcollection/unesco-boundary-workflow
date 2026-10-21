# 运行与复现

## 从三个仓库迁移

1. 冻结原仓库版本，保存文件路径、Git blob SHA 和代码审阅记录。
2. 将来源检索、地图收集、几何验证、打包拆成同一 Python 包的四个命令。
3. 用根目录 `SKILL.md` 连接工作步骤；条件性细节留在 `references/`。
4. 针对原代码缺陷编写离线测试，再保存实际安装环境和小范围联网检查结果。
5. 新仓库独立发布。旧仓库、原始项目工作簿和本地 GIS 源文件继续保留。

这是代码和方法的整合，原仓库 Git 历史未合并进新仓库；精确来源见
[source-manifest.json](source-manifest.json)。原文快照留在本次任务的本地审阅目录，
公开仓库保留清单和必要的方法说明，不附带个人路径、邮件地址及历史会话材料。

## 环境

`pyproject.toml` 固定直接依赖；`requirements.lock.txt` 记录本次 Windows x64 /
Python 3.12 环境的完整依赖版本，供重建相同环境。它不是跨平台字节一致性承诺，
也未包含 wheel 哈希或底层系统库。GitHub Actions 配置在 Windows/Linux 和
Python 3.12/3.13 上运行离线测试；远端实际结果以 Actions 为准。

Windows 上可在启动安装前指定临时目录，避免安装器使用系统盘：

```powershell
New-Item -ItemType Directory -Force 'D:\Temp\unesco' | Out-Null
$env:TEMP='D:\Temp\unesco'
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR=Join-Path $env:TEMP 'pip-cache'
$env:PYTHONDONTWRITEBYTECODE='1'
```

临时路径仅为示例，可改为自己的数据盘目录。
`runs/`、`outputs/` 和虚拟环境不提交到仓库。不要把真实联系方式写进公开示例数据。

## 输入与检索

CSV（UTF-8）或 XLSX 活动工作表至少提供 `id`、`unesco_id`、`site_name` 三列。
`id` 是本地行标识，`unesco_id` 才是官方遗产 ID。可选 `remarks` 保存显式
OSM relation/way 信息，`right or not=1` 默认跳过；有授权重查时使用
`--override-verified`。列顺序不影响读取，缺列和重复本地 ID 会报错。

在工作前打开官方遗产页和 maps 页，确认历史版本与组件范围。`probe` 自动查询
WHC 0/1/2 图层，并保存原始字段。服务结构改变、截断、HTTP/API 错误会被记录，
不会自动解释成“官方无边界”。检索候选一律待审核；没有靠名称和面积打分直接
变成 `correct` 的捷径。

`probe` 的 OSM 名称/显式 ID 查询是辅助发现功能。其他官方矢量门户、
附近 Overpass 检索、复杂 relation 拼接、PDF 元数据提取和 QGIS 配准没有自动实现。
做这些步骤时保存查询、脚本、投影、控制点和中间结果，再把选定的 WGS84
FeatureCollection 交给同一套审核/打包流程。

## 响应快照与离线重放

```text
runs/nara-01/
  raw/                URL 哈希命名的响应字节与元数据
  candidates/615/     待审核官方/OSM 几何
  reviews/            每个本地 ID 的检索记录
  maps/870/           地图文档与 manifest.json
  retrieval.json      机器可读汇总
  retrieval.md        人工检查表
```

同 URL 的快照会复用，先检查保存内容的 SHA-256。`--offline` 禁止联网，
归档缺失就报错。下载失败的 HTTP 响应也保留；需要重试更新时，新建 run 目录。
自动重试限三次并限速，不能消除服务端变化。记录所用代码提交和输入清单，
与运行环境一起保存；响应快照与来源版本才是复现某次结果的关键。

## 审核与交付

审核记录绑定源 GeoJSON 的原始字节 SHA-256，连格式化变更也需要重算并重新核对。
对 `correct` 要求正面的五项检查、明确且完整的组件 ID 列表、官方面积和比较说明。
它们是审核人填写的判断，程序不替人证明权威性。没有可信替代时不打包猜测几何。

包先写入新建暂存目录，回读 GeoJSON/Shapefile，确认图形和属性条数、
孔洞与多岛保持一致，成功后才移到对应状态目录。已存在的同名输出会报错。
这是防止覆盖的设计；需要修订时先给旧包留存版本，再选择新的输出根目录。
当前 CLI 不改写原工作簿、旧源文件或已有包，也不自动移动不同状态下的历史版本。

GeoJSON 是完整属性存档；Shapefile DBF 只保留索引，长中文名称按 UTF-8
完整字符截到 240 字节。当前拒绝未闭合环、无效拓扑、混合/点几何、非二维坐标
和跨日期变更线的未切分环。输入必须已经正确转换到 WGS84；程序不猜源 CRS。

## 把工作流交给 Agent

保留整个仓库并安装 Python 包，让 Agent 读取根目录 `SKILL.md`。例如：

> 读取这个仓库的 SKILL.md，处理 sites.csv 中的目标。先核验官方核心图层和
> 连续遗产组件，保存证据，只为审核通过的范围导出，缺失项明确列出。

只复制 `SKILL.md` 会缺少代码、模板和参考文件。本仓库尚未发布到 PyPI，
也没有声称在所有 Agent 客户端完成了自动安装兼容性验证。
