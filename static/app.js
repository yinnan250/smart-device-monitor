// 监控大屏应用主逻辑
class MonitoringDashboard {
    constructor() {
        this.refreshInterval = 5000; // 5秒刷新间隔
        this.init();
    }

    async init() {
        console.log('初始化监控大屏...');
        await this.loadMonitoringData();
        this.startAutoRefresh();
    }

    // 加载监控数据
    async loadMonitoringData() {
        try {
            const response = await fetch('/api/monitoring/data');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log('监控数据加载成功:', data);
            
            this.updateDashboard(data);
            this.updateLastRefreshTime();
            
        } catch (error) {
            console.error('加载监控数据失败:', error);
            this.showError('加载监控数据失败: ' + error.message);
        }
    }

    // 更新仪表板显示
    updateDashboard(data) {
        const container = document.getElementById('hostsContainer');
        
        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>暂无监控数据</h3>
                    <p>请先添加监控主机</p>
                </div>
            `;
            return;
        }

        // 过滤在线主机
        const onlineHosts = data.filter(host => host.status === 'online');
        
        if (onlineHosts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>无在线主机</h3>
                    <p>所有监控主机均处于离线状态</p>
                </div>
            `;
            return;
        }

        // 生成主机卡片HTML
        container.innerHTML = onlineHosts.map(host => this.createHostCard(host)).join('');
    }

    // 创建主机监控卡片
    createHostCard(host) {
        const metrics = host.metrics;
        const isRealData = host.realData;
        
        return `
            <div class="host-card" data-host-id="${host.hostId}">
                <div class="host-header">
                    <div class="host-ip">${host.hostIp}</div>
                    <div class="host-status status-online">
                        ${isRealData ? '🟢 实时数据' : '🟡 模拟数据'} • 在线
                    </div>
                </div>
                
                <div class="metrics-grid">
                    <!-- CPU 使用率 -->
                    <div class="metric-item">
                        <div class="metric-label">CPU 使用率</div>
                        <div class="metric-value">${metrics.cpu.usage}%</div>
                        <div class="metric-bar">
                            <div class="metric-progress ${this.getUsageClass(metrics.cpu.usage)}" 
                                 style="width: ${metrics.cpu.usage}%"></div>
                        </div>
                        <div class="metric-info">温度: ${metrics.cpu.temperature}°C</div>
                    </div>
                    
                    <!-- 内存使用率 -->
                    <div class="metric-item">
                        <div class="metric-label">内存使用率</div>
                        <div class="metric-value">${metrics.memory.usage}%</div>
                        <div class="metric-bar">
                            <div class="metric-progress ${this.getUsageClass(metrics.memory.usage)}" 
                                 style="width: ${metrics.memory.usage}%"></div>
                        </div>
                        <div class="metric-info">
                            已用: ${this.formatBytes(metrics.memory.used)} / 
                            总计: ${this.formatBytes(metrics.memory.total)}
                        </div>
                    </div>
                    
                    <!-- 磁盘使用率 -->
                    <div class="metric-item">
                        <div class="metric-label">磁盘使用率</div>
                        <div class="metric-value">${metrics.disk.usage}%</div>
                        <div class="metric-bar">
                            <div class="metric-progress ${this.getUsageClass(metrics.disk.usage)}" 
                                 style="width: ${metrics.disk.usage}%"></div>
                        </div>
                        <div class="metric-info">
                            总计: ${metrics.disk.total}GB
                        </div>
                    </div>
                    
                    <!-- 网络流量 -->
                    <div class="metric-item">
                        <div class="metric-label">网络流量</div>
                        <div class="metric-value">↑${metrics.network.out} ↓${metrics.network.in}</div>
                        <div class="metric-info">
                            上传: ${metrics.network.out} MB/s<br>
                            下载: ${metrics.network.in} MB/s
                        </div>
                    </div>
                </div>
                
                <div class="host-footer">
                    <span class="timestamp">最后更新: ${new Date(host.timestamp).toLocaleString()}</span>
                    <span class="data-source">${isRealData ? '真实数据' : '模拟数据'}</span>
                </div>
            </div>
        `;
    }

    // 根据使用率返回对应的CSS类
    getUsageClass(usage) {
        if (usage < 50) return 'progress-low';
        if (usage < 80) return 'progress-medium';
        return 'progress-high';
    }

    // 格式化字节大小
    formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 更新最后刷新时间
    updateLastRefreshTime() {
        const timeElement = document.getElementById('lastUpdateTime');
        if (timeElement) {
            timeElement.textContent = `最后更新: ${new Date().toLocaleString()}`;
        }
    }

    // 显示错误信息
    showError(message) {
        const container = document.getElementById('hostsContainer');
        container.innerHTML = `
            <div class="error">
                <h3>数据加载失败</h3>
                <p>${message}</p>
                <button onclick="dashboard.loadMonitoringData()" class="btn-primary">重试</button>
            </div>
        `;
    }

    // 开始自动刷新
    startAutoRefresh() {
        setInterval(() => {
            this.loadMonitoringData();
        }, this.refreshInterval);
    }

    // 手动刷新数据
    refreshData() {
        this.loadMonitoringData();
    }
}

// API 调用类
class MonitoringAPI {
    static BASE_URL = '/api';
    
    // 获取所有主机
    static async getHosts() {
        try {
            const response = await fetch(`${this.BASE_URL}/hosts`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('获取主机列表失败:', error);
            throw error;
        }
    }
    
    // 添加主机
    static async addHost(hostData) {
        try {
            const response = await fetch(`${this.BASE_URL}/hosts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(hostData)
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('添加主机失败:', error);
            throw error;
        }
    }
    
    // 删除主机
    static async deleteHost(hostId) {
        try {
            const response = await fetch(`${this.BASE_URL}/hosts/${hostId}`, { 
                method: 'DELETE' 
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
        } catch (error) {
            console.error('删除主机失败:', error);
            throw error;
        }
    }
    
    // 获取监控数据
    static async getMonitoringData() {
        try {
            const response = await fetch(`${this.BASE_URL}/monitoring/data`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('获取监控数据失败:', error);
            throw error;
        }
    }
    
    // 测试SSH连接
    static async testSshConnection(hostData) {
        try {
            const response = await fetch(`${this.BASE_URL}/test-ssh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(hostData)
            });
            return await response.json();
        } catch (error) {
            console.error('SSH连接测试失败:', error);
            return { success: false, message: '网络错误: ' + error.message };
        }
    }
}

// 主机管理类
class HostManager {
    constructor() {
        this.init();
    }
    
    async init() {
        if (document.getElementById('addHostForm')) {
            this.setupHostForm();
            await this.loadHostsList();
        }
    }
    
    setupHostForm() {
        const form = document.getElementById('addHostForm');
        form.addEventListener('submit', (e) => this.handleAddHost(e));
        
        document.getElementById('testSshBtn').addEventListener('click', () => this.testSshConnection());
    }
    
    async testSshConnection() {
        const form = document.getElementById('addHostForm');
        const formData = new FormData(form);
        const hostData = {
            hostIp: formData.get('hostIp'),
            sshUser: formData.get('sshUser'),
            sshPassword: formData.get('sshPassword'),
            sshPort: formData.get('sshPort') || '22'
        };
        
        if (!this.isValidIp(hostData.hostIp)) {
            alert('请输入有效的IP地址');
            return;
        }
        
        const resultDiv = document.getElementById('sshTestResult');
        resultDiv.innerHTML = '<div class="testing">正在测试SSH连接...</div>';
        
        try {
            const result = await MonitoringAPI.testSshConnection(hostData);
            
            if (result.success) {
                resultDiv.innerHTML = '<div class="success">✅ SSH连接测试成功！</div>';
            } else {
                resultDiv.innerHTML = `<div class="error">❌ SSH连接测试失败: ${result.message}</div>`;
            }
        } catch (error) {
            resultDiv.innerHTML = `<div class="error">❌ 测试过程中发生错误: ${error.message}</div>`;
        }
    }
    
    async handleAddHost(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const hostData = {
            hostIp: formData.get('hostIp'),
            sshUser: formData.get('sshUser'),
            sshPassword: formData.get('sshPassword'),
            sshPort: formData.get('sshPort') || '22'
        };
        
        if (!this.isValidIp(hostData.hostIp)) {
            alert('请输入有效的IP地址');
            return;
        }
        
        try {
            await MonitoringAPI.addHost(hostData);
            event.target.reset();
            document.getElementById('sshTestResult').innerHTML = '';
            await this.loadHostsList();
            alert('主机添加成功！');
        } catch (error) {
            alert('添加主机失败: ' + error.message);
        }
    }
    
    isValidIp(ip) {
        const pattern = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/;
        if (!pattern.test(ip)) return false;
        
        return ip.split('.').every(segment => {
            const num = parseInt(segment);
            return num >= 0 && num <= 255;
        });
    }
    
    async loadHostsList() {
        const hostsList = document.getElementById('hostsList');
        
        try {
            const hosts = await MonitoringAPI.getHosts();
            
            if (hosts.length === 0) {
                hostsList.innerHTML = '<div class="empty-state">暂无监控主机，请先添加主机。</div>';
                return;
            }
            
            hostsList.innerHTML = hosts.map(host => `
                <div class="host-list-item">
                    <div class="host-info">
                        <div><strong>IP地址:</strong> ${host.hostIp}</div>
                        <div><strong>SSH用户:</strong> ${host.sshUser}</div>
                        <div><strong>SSH端口:</strong> ${host.sshPort}</div>
                        <div><strong>添加时间:</strong> ${new Date(host.createdAt).toLocaleString()}</div>
                    </div>
                    <button class="btn-danger" onclick="hostManager.deleteHost(${host.id})">删除</button>
                </div>
            `).join('');
        } catch (error) {
            hostsList.innerHTML = '<div class="error">加载主机列表失败</div>';
        }
    }
    
    async deleteHost(hostId) {
        if (confirm('确定要删除这个主机吗？')) {
            try {
                await MonitoringAPI.deleteHost(hostId);
                await this.loadHostsList();
            } catch (error) {
                alert('删除失败: ' + error.message);
            }
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 如果是监控大屏页面
    if (document.getElementById('hostsContainer')) {
        window.dashboard = new MonitoringDashboard();
    }
    
    // 如果是主机管理页面
    if (document.getElementById('addHostForm')) {
        window.hostManager = new HostManager();
    }
});

// 全局刷新函数
function refreshDashboard() {
    if (window.dashboard) {
        window.dashboard.refreshData();
    }
}