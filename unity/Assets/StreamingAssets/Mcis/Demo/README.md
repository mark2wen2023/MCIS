# Lily / Mary 示例数据

**示例数据（虚构），改编自论文 5.4 节。** 船名、MMSI（999000001 / 999000002）、港口（虚构海岛港口，约 21.78°N, 113.70°E）与事故情节均为虚构，仅供演示。

## 情节
- Lily（散货船，离港）与 Mary（满载集装箱船，外来进港）在窄航道会遇。
- 起始时刻 2026-05-18T10:00:00Z，时长 15 分钟，10 秒间隔；约 T+9 min（540 s）发生碰撞（最小距离 < 0.05 nm），此后 Lily 减速并缓慢漂移直至近似停止。
- 关键点取自 `prototype/index.html` 的 `DEFAULT_LILY_WAYPOINTS` / `DEFAULT_MARY_WAYPOINTS`，经三次 Hermite 插值后按 10 s 采样；SOG/COG 由插值曲线的导数得到。

## 文件
| 文件 | 说明 |
|---|---|
| `lily_mary_demo.csv` | 列 `mmsi,timestamp_utc,lat,lon,sog_kn,cog_deg,hdg_deg,vessel_name`，UTC ISO-8601 |
| `lily_mary_demo.nmea` | `!AIVDM` 类型 1 位置报告 + 类型 5 静态/航次（两句），含校验和；时间由 `# epoch_utc:` 注释与报告秒字段恢复 |

CSV 导入时需映射列名（见 `CsvMappingProfile`）。

## 重新生成
```
python3 unity/Tools/generate_demo_data.py
```
