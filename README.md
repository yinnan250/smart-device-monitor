# smart-device-monitor
服务器实时监控数据大屏系统

项目简介

服务器实时监控数据大屏系统是一个基于Flask的Web应用程序，用于实时监控多台服务器的运行状态。系统通过SSH连接获取服务器的CPU使用率、内存使用率、磁盘使用率和网络流量等关键指标，并以可视化大屏的形式展示监控数据。

主要功能

• 实时监控大屏: 可视化展示所有服务器的实时运行状态

• 主机管理: 添加、删除和测试监控的主机

• 历史数据查询: 查看历史监控数据记录

• SSH连接测试: 在添加主机前测试SSH连接是否正常

• 数据持久化: 使用SQLite数据库存储历史监控数据

• 响应式设计: 支持桌面和移动设备访问

技术栈

• 后端: Flask 2.3.3, SQLite, Paramiko (SSH连接)

• 前端: HTML5, CSS3, JavaScript (原生)

• 部署: Docker, Gunicorn

• 监控指标: CPU使用率、内存使用率、磁盘使用率、网络流量

项目结构


smart-device-monitor/
├── .git/                          # Git版本控制目录
├── data/                          # 数据存储目录
│   ├── hosts.json                # 主机配置信息
│   ├── monitor.db                # SQLite监控数据库
│   └── monitoring_history.json   # 历史监控数据（备用）
├── static/                       # 静态资源文件
│   ├── app.js                   # 前端JavaScript逻辑
│   └── styles.css               # 样式表文件
├── templates/                    # HTML模板文件
│   ├── data-history.html        # 历史数据页面
│   ├── host-management.html     # 主机管理页面
│   └── index.html               # 监控大屏主页
├── .gitignore                   # Git忽略文件配置
├── app.py                       # Flask主应用文件
├── Dockerfile                   # Docker镜像构建文件
├── kelong                       # 未知文件（可能为测试文件）
├── LICENSE                      # 项目许可证文件
├── README.md                    # 项目说明文档（本文件）
└── requirements.txt             # Python依赖包列表


快速部署

使用Docker部署（推荐）

1. 构建Docker镜像
   docker build -t server-monitor .
   

2. 运行Docker容器
   docker run -d \
     --name server-monitor \
     -p 5000:5000 \
     -v $(pwd)/data:/app/data \
     server-monitor
   

3. 访问应用
   打开浏览器访问: http://localhost:5000

传统部署方式

1. 安装Python依赖
   pip install -r requirements.txt
   

2. 初始化数据库
   python -c "from app import init_database; init_database()"
   

3. 启动应用
   # 开发模式
   python app.py
   
   # 生产模式（使用Gunicorn）
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   

4. 访问应用
   打开浏览器访问: http://localhost:5000

配置说明

主机配置

系统通过data/hosts.json文件存储监控主机的配置信息，包括：
• 主机IP地址

• SSH用户名和密码

• SSH端口（默认22）

数据库配置

监控数据存储在SQLite数据库data/monitor.db中，包含以下表结构：
• monitoring_data: 存储历史监控数据记录

• 自动创建的索引优化查询性能

使用指南

1. 添加监控主机

1. 访问"主机管理"页面
2. 填写主机信息：
   • IP地址（如：192.168.1.100）

   • SSH用户名（如：root）

   • SSH密码

   • SSH端口（默认22）

3. 点击"测试SSH连接"验证配置
4. 点击"添加主机"完成添加

2. 查看监控大屏

1. 访问首页查看实时监控数据
2. 系统每5秒自动刷新数据
3. 支持手动刷新功能

3. 查询历史数据

1. 访问"历史数据"页面
2. 选择查询条件：
   • 目标主机（可选所有主机）

   • 时间范围（小时）

   • 显示条数限制

3. 点击"查询数据"查看结果
4. 支持数据导出为CSV格式

API接口说明

监控数据接口

• GET /api/monitoring/data - 获取实时监控数据

• GET /api/history/data - 获取历史监控数据

• GET /api/history/hosts - 获取有历史数据的主机列表

主机管理接口

• GET /api/hosts - 获取所有主机列表

• POST /api/hosts - 添加新主机

• DELETE /api/hosts/<host_id> - 删除主机

• POST /api/test-ssh - 测试SSH连接

故障排除

常见问题

1. SSH连接失败
   • 检查IP地址是否正确

   • 验证SSH用户名和密码

   • 确认防火墙设置允许SSH连接

   • 检查SSH服务是否正常运行

2. 监控数据不更新
   • 确认主机在线状态

   • 检查网络连通性（ping测试）

   • 查看应用日志获取详细错误信息

3. 页面加载异常
   • 清除浏览器缓存

   • 检查控制台错误信息

   • 确认静态资源加载正常

日志查看

# 查看Docker容器日志
docker logs server-monitor

# 查看应用日志
tail -f data/monitor.log


安全建议

1. 修改默认配置
   • 更改默认端口（如从5000改为其他端口）

   • 使用强密码保护SSH连接

2. 网络隔离
   • 将监控系统部署在内网环境

   • 限制外部网络访问

3. 定期维护
   • 定期清理历史数据

   • 更新系统依赖包

   • 备份重要配置文件

许可证

本项目基于MIT许可证开源，详见LICENSE文件。

技术支持

如有问题或建议，请通过以下方式联系：
• 提交GitHub Issue

• 查看项目文档

• 联系开发团队

最后更新: 2025年11月