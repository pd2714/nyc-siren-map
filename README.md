# 纽约警笛听诊器 · NYC Siren Stethoscope

在地图上选一个点，回放 2026 年 9 月 21–27 日这一周纽约救护车、消防车和警车从附近经过时的警笛声。

Pick a spot on the map and replay one week (2026-09-21 to 27) of NYC ambulance, fire truck and police car runs, with synthesized sirens that fade, muffle and Doppler-shift with distance.

**在线访问 / Live:** https://pd2714.github.io/nyc-siren-map/

## 哪些是真的，哪些是模拟的

- **真实数据（NYC Open Data，2026-09-21 至 27）：** FDNY [EMS Incident Dispatch Data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj)（派出、到场、送医、到院时间，邮编，严重度，呼叫类型）；FDNY [Fire Incident Dispatch Data](https://data.cityofnewyork.us/Public-Safety/Fire-Incident-Dispatch-Data/8m42-w767)（出动时间、邮编、事件类型、派出车辆数）；[NYPD Calls for Service](https://data.cityofnewyork.us/Public-Safety/NYPD-Calls-for-Service-Year-to-Date-/n2zq-pubd)（派出、到达时间，类型，坐标）。医院、消防站位置和邮编边界也来自开放数据。
- **模拟：** 救护车和消防车只精确到邮编，现场位置在邮编区内随机取点；警察坐标加了约 75 m 随机偏移。救护车出发点按真实行驶时长反推，送医时挑一家距离与真实送医时长相符的医院；消防车从附近消防站出发，每起事件最多画 6 辆。路线按街道网格走 L 形。鸣笛规则是假设：救护车严重度 1–4 去现场、1–2 送医时鸣笛；消防车除警报测试、树木倒伏外都鸣笛；警车只算紧急出警。警笛声为浏览器合成（救护车电子警笛、消防车机械警笛加气喇叭、警车电子警笛加低频 rumbler），声级用简单的点声源衰减模型估算。
- 不包括私营救护车。

## 重新生成

```sh
sh fetch.sh        # 下载原始数据到 raw/
python3 build.py   # 生成 docs/index.html（独立网站）和 index.html
```

改 `fetch.sh` 里的日期可以换一周（`build.py` 里的 `WEEK0` 也要一起改）。
