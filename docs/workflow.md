# 使用教程

本教程从遗产清单开始，说明如何查找候选、选择边界并导出 GIS 数据包。先按 [README](../README.md#安装与第一次运行) 安装，并运行离线示例确认环境可用。

## 1. 准备遗产清单

创建 UTF-8 编码的 CSV，或使用 XLSX 的活动工作表。列名固定，顺序不限：

```csv
id,unesco_id,site_name
615,870,Historic Monuments of Ancient Nara
```

| 列名 | 要求 |
|---|---|
| `id` | 项目自定的正整数编号，每行唯一 |
| `unesco_id` | UNESCO 官方遗产编号，例如官方条目 `/en/list/870/` 中的 `870` |
| `site_name` | 完整遗产名称 |
| `remarks` | 可选，填写已知 OSM 编号，如 `relation 123456` 或 `way 789012` |
| `right or not` | 可选，`1` 表示已核对，此行默认跳过 |

## 2. 检索边界与下载地图

打开遗产的官方条目和 maps 页面，确认所需边界版本以及是否包含多个组件。然后运行：

```bash
unesco-boundary probe --input examples/sites.csv --run runs/nara-01 --no-osm --user-agent "BoundaryStudy/1.0 (https://github.com/YOUR_ACCOUNT)"
```

将 `YOUR_ACCOUNT` 替换为自己的公开项目或个人主页地址。请求会查询 WHC 的组件元数据、核心边界和缓冲区图层。

查看 `runs/nara-01/retrieval.md` 中的结果，并打开 `candidates/` 下的 GeoJSON。官方核心图层可能没有多边形；此时可从官方 GIS 门户寻找数据，或去掉 `--no-osm` 查询 OSM 候选。检索结果保留在待核对状态，不会自动导出为最终边界。

需要地图资料时运行：

```bash
unesco-boundary maps --unesco-id 870 --run runs/nara-01 --user-agent "BoundaryStudy/1.0 (https://github.com/YOUR_ACCOUNT)"
```

地图与清单保存在 `runs/nara-01/maps/870/`。该命令下载 PDF/图片；如果需要从地图得到矢量边界，使用 QGIS 等工具配准和提取，方法见 [地图处理说明](../references/map-digitization.md)。

### 复用已下载的来源

每个运行目录保存请求响应，可在不联网时重复检索步骤：

```bash
unesco-boundary probe --input examples/sites.csv --run runs/nara-01 --no-osm --offline
```

读取最新来源时，改用新的目录，如 `runs/nara-02`。重新检查 `right or not=1` 的行时，添加 `--override-verified`。

## 3. 选择边界并填写审核记录

在 GIS 软件中查看候选，核对遗产名称、核心范围、位置、面积和组件覆盖。核心区与缓冲区分别处理；连续遗产应包含所需的全部组件。将选定的 WGS84 GeoJSON 保存为 `source.geojson`，再检查几何：

```bash
unesco-boundary validate source.geojson
```

输入必须是非空的 GeoJSON FeatureCollection，包含 Polygon 或 MultiPolygon。需要先修正未闭合环、无效几何、错误坐标系或未切分的跨日期变更线几何。

复制 [review.template.json](../examples/review.template.json) 并命名为 `review.json`。按下表填写：

| 字段 | 填写内容 |
|---|---|
| `local_id`、`unesco_id`、`site_name` | 与目标遗产对应的编号和名称 |
| `source_url`、`source_kind` | 选定数据的地址和来源类型 |
| `source_sha256` | 源文件校验值，计算方法见下方 |
| `reviewer` | 审核人的项目用户名或角色名，无需填写私人联系方式 |
| `reviewed_at` | 带时区的审核时间，如 `2026-01-01T09:00:00+08:00` |
| `scope_note` | 边界版本、核心范围及包含哪些组件 |
| `official_check` | WHC 核心图层查询地址、结果和说明；结果使用 `found`、`empty` 或 `unusable` |
| `status`、`caveats` | 审核状态和仍需说明的问题；无问题时 `caveats` 填 `[]` |

在 `source.geojson` 所在目录运行以下命令，复制输出值到 `source_sha256`：

```bash
python -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('source.geojson').read_bytes()).hexdigest())"
```

文件发生任何修改后，需要重新核对并计算校验值。

来源类型：`official_whc`（WHC）、`official_vector`（其他官方矢量）、`osm`、`geospatial_pdf`（地理 PDF）、`digitized_map`（地图数字化）、`scale_anchor`（比例尺锚定）。`synthetic` 仅用于练习数据。

### 如何选择状态

| 状态 | 使用条件 |
|---|---|
| `review_needed` | 范围、来源、配准或面积仍待核对 |
| `partial` | 只有部分组件，或仅作为参考图层 |
| `correct` | 已核对来源、核心范围、位置、面积，并覆盖全部目标组件 |

使用 `correct` 时，还要填写：

- `checks` 的五项核对结果，均为 `true`。
- `expected_components` 与 `covered_components`，使用一致、完整的组件 ID 列表。
- 正数 `official_area_ha` 和 `area_comparison_note`，说明官方面积与计算面积的差别。
- 使用替代来源时，在 `official_check` 中说明官方核心图层为何为空或不可用。
- 地图提取结果在 `georeference_evidence` 中填写配准或控制点记录的位置。

比例尺锚定和合成几何不使用 `correct`。更详细的来源选择标准见 [边界核对说明](../references/source-review.md)。

## 4. 导出并在 GIS 中打开

```bash
unesco-boundary package --geojson source.geojson --review review.json --out-root outputs
```

在生成的 `outputs/<状态>/<本地编号>_<名称>/` 目录中：

- 打开 `.geojson` 可读取完整属性。
- 打开 `.shp` 可使用 Shapefile；移动时应连同 `.shx .dbf .prj .cpg` 一起移动。
- `.md` 和 `review.json` 记录边界来源和范围，`validation.json` 记录几何检查结果。

已有同名包不会被覆盖。修订结果时使用新的输出目录，例如 `--out-root outputs-v2`。

## 在 Python 项目中调用

安装后，可以在自己的脚本或 Notebook 中导入：

```python
import json
from pathlib import Path

from unesco_boundary.geometry import validate_collection
from unesco_boundary.package import build_package

source = Path("source.geojson")
data = json.loads(source.read_text(encoding="utf-8-sig"))
print(validate_collection(data))

# review.json 按第 3 步填写。
result = build_package(source, Path("review.json"), Path("outputs"))
print(result["path"])
```

要扩展检索或导出功能，安装 `requirements-dev.txt`，修改 `src/unesco_boundary/`，运行 `python -m pytest -q` 检查兼容性。命令参数可用 `unesco-boundary --help` 和 `unesco-boundary <命令> --help` 查看。

## 交给 Agent 使用

让 Agent 读取完整仓库中的 [SKILL.md](../SKILL.md)，例如：

> 读取 SKILL.md，处理 sites.csv 中的遗产。检索官方核心边界，核对范围与组件，按审核状态导出 GIS 包，并列出尚缺少的边界。

保留完整仓库，供 Agent 使用其中的代码、模板和参考文件。
