# 三个原仓库的内容与代码审阅

审阅日期：2026-10-21。清点默认分支的全部文件，逐个读取 Python 代码与 Skill
说明。精确提交和每个文件的 Git blob SHA 见 [source-manifest.json](source-manifest.json)。

| 原仓库 | 实际包含 | 在工作流中的位置 |
|---|---|---|
| `unesco-whc-osm-boundary-retriever` | 6 个文件：README、Apache 2.0 LICENSE、SKILL、Agent 元数据、OSM 决策参考、1 个批量检索脚本 | 查找边界候选与来源证据 |
| `unesco-boundary-packager` | 11 个文件：README、SKILL、Agent 元数据、5 份参考、2 个 Python 脚本和 .gitignore | 判断来源、地图数字化规则、GIS 包交付 |
| `UNESCO_Map_SC` | 3 个文件：35 字节 README、Apache 2.0 LICENSE、sc_500.py | 获取官方地图文档 |

前两个确实是 Skill 仓库，但都包含可执行辅助代码。第三个是下载器，不是
PDF 边界提取器；它从官方 XML 读遗产清单，按硬编码 ID 列表打开 maps 页面，
提取 `/document/` 链接并下载 PDF、JPEG、PNG、TIFF 或 GIF。
所谓 “1–500” 是原工作批次语境，并不等于遍历官方 ID 的连续 1–500。
原仓库没有附地图、工作簿、依赖清单或测试。

## 检索脚本：whc_osm_boundary_retrieve.py

已逐函数检查 `load_rows`、`explicit_osm_ids`、`official_area_and_components`、
`candidate_from_item`、`evaluate`、`process_row` 和主循环。

| 发现 | 后果 | 整合后的处理 |
|---|---|---|
| 默认个人目录、工作簿名与外部 venv 搜索 | 换机器难以运行 | 显式输入路径、标准 Python 包 |
| `load_rows` 混用表头和默认列位置，未执行 verified 行跳过规则 | 列变动可能读错；与打包语义不一致 | 只用命名列，验证必填/重复 ID；统一 verified 跳过 |
| 有 OSM 关键词就抓取所有 6 位以上数字，全部视为 relation | way 类型丢失，其他数字可能误作 ID | 只解析紧邻 relation/way 的显式编号，保留 R/W |
| 近似平面面积，首个含 area 的字段被当成官方面积并求和 | 单位与重复总面积可能混淆 | 椭球面积；原始字段交审核人明确指定 |
| 片段名称匹配和宽泛面积区间筛选 | 候选质量容易被高估 | 不自动接受候选；显式审核位置/范围/面积 |
| 有官方 polygon 就建议打包为 correct | 未检查完整组件和来源范围 | 官方结果也先进入 review_needed |
| 未识别 HTTP 200 内的 API error、截断；层失败中断整行 | 服务错误可能掩盖其他证据 | 各层记录错误；核心查询失败不按空层处理 |
| 说明提到 nearby/Overpass、距离和 tags 核验，脚本未完整实现 | 文档能力大于脚本能力 | 明确自动化边界，保留人工/GIS 扩展步骤 |

原脚本本来就将多数 OSM 结果写为 candidate，不能概括成“所有 OSM 自动成功”。
真正的问题是候选判据偏弱，以及官方结果的后续打包建议过早。

## 打包脚本与参考文件

`build_package_from_geojson.py` 的 `write_shape` 对 MultiPolygon 每个 polygon
调用一次 `writer.poly`，外层却每个 feature 只写一次 `record`；配合 autoBalance
会产生额外/空属性记录，破坏一条 feature 对应一条记录的关系。新导出器把
同一 feature 的全部外环/内环一次写入，并用带孔、多岛的回读测试验证。

其他问题包括：只查 geometry type、不查拓扑/闭环/CRS；环方向未标准化；
还未验证就创建最终目录；未回读图形和属性；输出文字默认称 verified。
新版本明确审核状态、绑定源文件哈希、先暂存后回读，并拒绝覆盖已有包。

`inspect_shapefile.py` 只读类型、字段、20 条样本和 .prj 文本，适合初检，
不是完整几何验证器；它的职责由新 `validate` 和导出回读分担。其他官方
Shapefile 的字段/编码/CRS检查仍应在源 GIS 软件中完成。

五份参考分别涉及来源政策、自动化提示、PDF/栅格数字化、比例尺锚定和历史会话。
原 `scale-anchor-digitization.md` 有“review_needed 也可能放 correct 文件夹”的
表述，与其他严格状态规则冲突。新版本统一按状态目录保存；历史个案不能直接
当作已验证样例，未向公开仓库复制原会话记录或个人联系信息。

原仓库版本与当前机器安装的同名 Skill 并非完全一致。本次审阅以 GitHub
冻结版本为准，没有把本机额外的修订误写成原仓库已有功能。

## 下载器：sc_500.py

检查了 XML 清单获取、链接发现、扩展名判断、下载和 CSV 日志。

| 发现 | 整合后的处理 |
|---|---|
| 固定长 ID 列表、输出路径和 sleep 参数 | 显式单个 UNESCO ID 和运行目录 |
| 未识别类型时默认 .jpg，可能把 HTML 保存成图片 | 检查 PDF/图片魔数；HTML 作为原始错误证据保留 |
| 手工拼接 CSV，标题中的引号/换行可破坏日志 | 结构化 JSON 清单 |
| 请求之后才检查文件存在 | 先按 URL 快照缓存，离线重放不联网 |
| 无响应哈希、时间和完整错误证据 | 保存原文、URL、响应元数据和 SHA-256 |
| 下载成功容易被理解为得到边界 | 下载状态明确为 document；GIS 提取另行审核 |

## 整合范围

新仓库保留方法与来源链，重写有问题的执行代码。原 Git 历史没有重写或合并，
原三个私有仓库未修改、归档或删除。公开仓库不是旧文件的简单拼盘：通用规则
收敛为一个 Skill，执行逻辑共享同一包，审阅和引用记录放在 docs。

复现依赖于固定输入、环境、源响应快照、审核记录和代码版本。软件回归测试
证明相关程序行为，不能证明任意遗产的边界符合 UNESCO 当前有效范围。
