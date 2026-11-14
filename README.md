# 纽约警笛听诊器 · NYC Siren Stethoscope

在地图上选一个点，回放 2026 年 9 月 21–27 日这一周纽约 FDNY 救护车从附近经过时的警笛声。

Pick a spot on the map and replay one week (2026-09-21 to 27) of FDNY EMS ambulance trips, with a synthesized siren that fades, muffles and Doppler-shifts with distance.

**在线访问 / Live:** https://pd2714.github.io/nyc-siren-map/

## 哪些是真的，哪些是模拟的

- **真实数据：** 每次派车的时间（派出、到场、送医、到院）、邮编、严重度和呼叫类型，来自 NYC Open Data 的 [EMS Incident Dispatch Data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj)。医院位置来自 [NYC Facilities Database](https://data.cityofnewyork.us/City-Government/Facilities-Database/ji82-xba5)，邮编边界来自 [MODZCTA](https://data.cityofnewyork.us/Health/Modified-Zip-Code-Tabulation-Areas-MODZCTA-/pri4-ifjk)。
- **模拟：** 公开数据只精确到邮编，所以现场位置在邮编区内随机取点；出发点按真实行驶时长反推；路线按街道网格走 L 形；送医时按真实送医时长挑一家距离相符的医院。假设严重度 1–4 去现场时鸣笛，1–2 送医时鸣笛。警笛声为浏览器合成，声级用简单的点声源衰减模型估算。
- 不包括警车、消防车，以及医院自营和私营救护车的警笛。

## 重新生成

```sh
sh fetch.sh        # 下载原始数据到 raw/
python3 build.py   # 生成 docs/index.html（独立网站）和 index.html
```

改 `fetch.sh` 里的日期可以换一周（`build.py` 里的 `WEEK0` 也要一起改）。
