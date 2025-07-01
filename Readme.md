<div align=center>
  <img width=200 src="https://bot.snowy.moe/logo.png"  alt="image"/>
  <h1 align="center">MuiceBot-Plugin-Sandbox</h1>
  <p align="center">让沐雪在沙盒中执行 Python 代码的插件✨</p>
</div>
<div align=center>
  <a href="https://nonebot.dev/"><img src="https://img.shields.io/badge/nonebot-2-red" alt="nonebot2"></a>
  <img src="https://img.shields.io/badge/Code%20Style-Black-121110.svg" alt="codestyle">
  <a href='https://qm.qq.com/q/lybolwibYW'><img src="https://img.shields.io/badge/QQ群-MuiceHouse-blue" alt="QQ群组"></a>
</div>

## 介绍✨

`MuiceBot-Plugin-Sandbox` 是一个基于 `Docker` 的 Function Call 插件，可让 LLM 在沙盒容器中执行真实 Python 代码

## 安装

- 提前配置 [Docker](https://www.docker.com/) 环境

- 向机器人对话：

```
.store install sandbox
```

- 根据操作系统环境配置 `runner_docker_base_url`

## 配置

### runner_docker_base_url

- 类型: str

- 说明: Docker 服务端的地址

- 默认值：`unix:///var/run/docker.sock` (Docker for unix)

### runner_container_networkmode

- 类型: Literal["bridge", "host", "none"]

- 说明: Docker 容器网络模式

- 默认值: `host`

### sandbox_container_waitfor

- 类型: float

- 说明: 容器操作最大等待时间

- 默认值: 30.0

## 局限性

**建议在每一次对话中手动声明引用目标操作文件（如有），否则 Muicebot 将无法获取所需的操作文件**

## 下一步工作

- [ ] 添加运行前代码评审

- [ ] 增加容器安全性
