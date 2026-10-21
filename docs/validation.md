# 验证记录

日期：2026-10-21；本地环境：Windows x64、Python 3.12.14。
运行依赖完整版本见 [requirements.lock.txt](../requirements.lock.txt)。

| 验证 | 结果 |
|---|---|
| 原仓库快照 | 20 个文件的 Git blob SHA 全部一致 |
| 离线回归 | 24 项通过，最终一次约 1.3 秒 |
| Skill 规范 | skill-creator 的 quick_validate 检查通过 |
| 本地文档 | Skill 元数据与 Markdown 相对文件链接检查通过 |
| 安装 | 隔离环境中 editable 安装成功 |
| 离线演示 | 带孔 MultiPolygon 导出并回读，1 条图形/属性，面积约 508.002090 ha |
| 真实 WHC 连通 | UNESCO 870：图层 0 返回 7 条记录，图层 1/2 返回空 FeatureCollection |
| 响应重放 | 上述官方响应在离线模式下得到相同候选/状态结果 |
| GitHub Actions | Windows/Linux × Python 3.12/3.13 四个组合全部通过 |

真实服务响应时间约为 2026-10-21 11:16（Asia/Shanghai）。查询使用原仓库
记录的 WHC FeatureServer，对 0/1/2 层应用 `property_id=870`、
`outFields=*`、`returnGeometry=true`、`f=geojson` 和 `outSR=4326`。
图层 1 的[查询地址](https://services6.arcgis.com/eMd5K6XXEvJETxfQ/arcgis/rest/services/prd_whc_sites_dossiers_elements_v2_view/FeatureServer/1/query?where=property_id%3D870&outFields=%2A&returnGeometry=true&f=geojson&outSR=4326)
是本次空核心结果的直接来源。

这证明该端点在本次查询时可达，不能据此断言奈良没有官方边界，也不能将
7 条元数据记录直接认作完整组件总数。本次没有制作奈良最终 GIS 包。
完整响应快照留在本地 `runs/live-nara-20261021/`，未放进公开仓库。

回归覆盖：多岛/孔洞记录对应、中文属性、含点号文件名、无效环/拓扑/坐标、
哈希变更、已有输出保护、缺失组件、比例尺和合成数据不得进入 correct、
完整审核的导出、OSM relation/way 类型、HTML 下载误判、官方 API 错误、
离线缺失/篡改、离线命令链和退出码。合成数据不代表真实遗产边界。

GitHub Actions 的[首次完整运行](https://github.com/cloudcollection/unesco-boundary-workflow/actions/runs/39537913006)
在 Windows/Linux、Python 3.12/3.13 四个组合中均完成安装、24 项回归、
Skill/文档检查与离线演示。后续变更结果以仓库 Actions 为准。
PDF 配准、复杂关系拼接和大批量长时间运行未在本次验证中自动化测试。
