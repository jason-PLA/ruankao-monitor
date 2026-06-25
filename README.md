# 🎯 软考成绩监控助手 (Ruankao Monitor)

[![Docker Pulls](https://img.shields.io/docker/pulls/your-dockerhub-username/ruankao-monitor?style=flat-square)](https://hub.docker.com/r/your-dockerhub-username/ruankao-monitor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

一个轻量级的网页监控程序，专为**软考（计算机技术与软件专业技术资格考试）** 考生打造。

自动轮询软考官网（ruankao.org.cn），当检测到“成绩查询”相关通知发布时，第一时间通过**邮件、微信、钉钉、Bark**等多种渠道推送通知给你。

告别频繁手动刷新网页，让你的 NAS 替你盯成绩！

## ✨ 特性

- 🚀 **开箱即用**：提供 Docker 镜像，一条命令即可部署。
- 💻 **NAS 友好**：资源占用极低（<50MB内存），完美适配群晖、威联通、**飞牛NAS (fnOS)**、绿联等 x86/ARM 设备。
- 📱 **全渠道通知**：支持 SMTP 邮件、Server酱（微信推送）、企业微信、钉钉、Bark（iOS推送）。
- 🔄 **状态记忆**：持久化已通知状态，重启容器不会重复发送通知。
- 🛡️ **多策略解析**：内置多种 HTML 解析策略，无惧官网页面结构微调。

## 🚀 快速开始 (Docker Compose)

### 1. 准备配置文件
```bash
mkdir -p ruankao-monitor && cd ruankao-monitor
wget https://raw.githubusercontent.com/你的GitHub用户名/ruankao-monitor/main/config.yaml.example -O config.yaml
# 编辑 config.yaml，填入你的邮箱或 Webhook 信息
nano config.yaml 