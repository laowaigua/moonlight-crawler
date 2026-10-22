# 🌙 Moonlight-Crawler

> ——在月光下镌刻我们的回忆。

**Moonlight-Crawler** 是一个以回忆珍藏为核心的网络爬虫项目，致力于从各大视频网站中采集、整理与保存有价值的信息，让每一段值得留存的记忆，都能在月光下被温柔珍藏。

## ✨ 项目简介

月光洒落，时光流转。

我们希望通过爬虫技术，把在时光长河中散落的互联网信息汇集起来，化作可以保存、检索与回顾的数字记忆。

Moonlight-Crawler 不仅是一个爬虫项目，更是一种关于记录与对抗遗忘的探索。

## 项目结构

```text
.
├── core/                   # 爬取、存储和数据库搜索的通用实现
│   ├── crawler.py          # 异步爬取调度、并发与分块处理
│   ├── storager.py         # SQLite 建表、批量写入和错误记录
│   └── searcher.py         # 从已有数据库中检索记录
├── sites/                  # 站点解析器和数据结构
│   ├── base.py             # Parser 基类、请求重试与异常处理
│   ├── loader.py           # 动态发现并加载站点 Parser/Schema
│   └── <site>/             # 每个站点独立目录
│       ├── parser.py       # 站点请求与响应解析逻辑
│       └── schema.py       # 该站点的数据库字段定义
├── data/                   # 采集数据目录（本地数据库文件）
├── search/                 # 搜索结果数据库目录
├── run_crawler.py          # 爬虫命令行入口
├── run_searcher.py         # 数据搜索命令行入口
├── retry.py                # 数据库记录修复/重试工具
└── README.md
```

## 支持的站点列表

| 站点       | 说明             | Parser 代码                                                  |
| -------- | -------------- | ---------------------------------------------------------- |
| 优酷土豆     | 优酷土豆视频信息接口     | [`sites/youku/parser.py`](sites/youku/parser.py)           |
| 新浪视频     | 新浪视频信息接口       | [`sites/sina/parser.py`](sites/sina/parser.py)             |
| 新浪WAP   | 新浪视频WAP信息接口    | [`sites/sina_wap/parser.py`](sites/sina_wap/parser.py)     |
| 新浪存储桶元数据 | 新浪视频存储桶文件元数据接口 | [`sites/sina_meta/parser.py`](sites/sina_meta/parser.py)   |
| 新浪酷搜     | 新浪视频酷搜缩略图文件    | [`sites/sina_kusou/parser.py`](sites/sina_kusou/parser.py) |
| 搜狐视频     | 搜狐视频信息接口       | [`sites/sohu/parser.py`](sites/sohu/parser.py)             |
| 爱奇艺PPS   | 爱奇艺PPS视频信息接口   | [`sites/iqiyi_pps/parser.py`](sites/iqiyi_pps/parser.py)           |
| 爱奇艺泡泡    | 爱奇艺泡泡视频信息接口    | [`sites/iqiyi_paopao/parser.py`](sites/iqiyi_paopao/parser.py)           |

## ⚠️ 注意事项

- 请遵守目标网站的服务条款及 `robots.txt` 规则。
- 合理控制请求频率，避免对目标服务器造成负担。
- 尊重个人隐私、版权及数据使用限制。
- 仅采集具有合法访问权限的数据。

## 💫 项目愿景

> 有些故事会随时间褪色，有些记忆值得被永久珍藏。
>
> 我们以代码为笔，以网络为海，以月光为引。
>
> 愿每一次采集，都是一次与时光的温柔相遇。

---

<p align="center">
  🌙 <b>Moonlight-Crawler</b>
  <br>
  <i>在月光下镌刻我们的回忆</i>
</p>
