// 修改后的MonitoringAPI类 - 使用Flask后端API
class MonitoringAPI {
    static BASE_URL = '/api'; // 使用相对路径指向Flask后端
    
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
}

// 主机管理功能类保持不变（与文档1相同）
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
        
        // 验证IP地址
        if (!this.isValidIp(hostData.hostIp)) {
            alert('请输入有效的IP地址');
            return;
        }
        
        try {
            await MonitoringAPI.addHost(hostData);
            event.target.reset();
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

// 监控仪表板功能类保持不变（与文档1相同）
class MonitoringDashboard {
    constructor() {
        this.charts = new Map();
        this.refreshInterval = null;
        this.refreshRate = 5000; // 5秒刷新一次
        
        if (document.getElementById('hostsContainer')) {
            this.init();
        }
    }
    
    async init() {
        await this.loadMonitoringData();
        this.startAutoRefresh();
        
        // 页面可见性变化时控制刷新
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopAutoRefresh();
            } else {
                this.startAutoRefresh();
            }
        });
    }
    
    async loadMonitoringData() {
        try {
            const monitoringData = await MonitoringAPI.getMonitoringData();
            this.renderMonitoringData(monitoringData);
            this.updateLastUpdateTime();
        } catch (error) {
            console.error('加载监控数据失败:', error);
            document.getElementById('hostsContainer').innerHTML = 
                '<div class="error">加载监控数据失败，请检查网络连接</div>';
        }
    }
    
    renderMonitoringData(data) {
        const container = document.getElementById('hostsContainer');
        
        if (!data || data.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无监控数据，请先添加监控主机</div>';
            return;
        }
        
        container.innerHTML = data.map(hostData => this.createHostCard(hostData)).join('');
        
        // 初始化或更新图表
        data.forEach(hostData => {
            this.updateCharts(hostData);
        });
    }
    
    createHostCard(hostData) {
        const metrics = hostData.metrics;
        const statusClass = hostData.status === 'online' ? 'status-online' : 'status-offline';
        const statusText = hostData.status === 'online' ? '在线' : '离线';
        
        // 计算进度条样式
        const cpuProgressClass = this.getProgressClass(metrics.cpu.usage);
        const memoryProgressClass = this.getProgressClass(metrics.memory.usage);
        const diskProgressClass = this.getProgressClass(metrics.disk.usage);
        
        return `
            <div class="host-card" data-host-id="${hostData.hostId}">
                <div class="host-header">
                    <div class="host-ip">${hostData.hostIp}</div>
                    <div class="host-status ${statusClass}">${statusText}</div>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-item">
                        <div class="metric-label">CPU使用率</div>
                        <div class="metric-value">${metrics.cpu.usage.toFixed(1)}%</div>
                        <div class="metric-bar">
                            <div class="metric-progress ${cpuProgressClass}" 
                                 style="width: ${metrics.cpu.usage}%"></div>
                        </div>
                    </div>
                    
                    <div class="metric-item">
                        <div class="metric-label">内存使用率</div>
                        <div class="metric-value">${metrics.memory.usage.toFixed(1)}%</div>
                        <div class="metric-bar">
                            <div class="metric-progress ${memoryProgressClass}" 
                                 style="width: ${metrics.memory.usage}%"></div>
                        </div>
                    </div>
                    
                    <div class="metric-item">
                        <div class="metric-label">磁盘使用率</div>
                        <div class="metric-value">${metrics.disk.usage.toFixed(1)}%</div>
                        <div class="metric-bar">
                            <div class="metric-progress ${diskProgressClass}" 
                                 style="width: ${metrics.disk.usage}%"></div>
                        </div>
                    </div>
                    
                    <div class="metric-item">
                        <div class="metric-label">网络流量</div>
                        <div class="metric-value">${metrics.network.in.toFixed(1)}/s</div>
                        <div class="metric-label">入: ${metrics.network.in.toFixed(1)}MB/s 出: ${metrics.network.out.toFixed(1)}MB/s</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="chart-${hostData.hostId}" width="400" height="200"></canvas>
                </div>
            </div>
        `;
    }
    
    getProgressClass(usage) {
        if (usage < 50) return 'progress-low';
        if (usage < 80) return 'progress-medium';
        return 'progress-high';
    }
    
    updateCharts(hostData) {
        const canvasId = `chart-${hostData.hostId}`;
        const canvas = document.getElementById(canvasId);
        
        if (!canvas) return;
        
        if (!this.charts.has(hostData.hostId)) {
            this.initializeChart(hostData.hostId, canvas);
        }
    }
    
    initializeChart(hostId, canvas) {
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: 10}, (_, i) => `${i * 5}秒前`).reverse(),
                datasets: [
                    {
                        label: 'CPU使用率 (%)',
                        data: Array(10).fill(0).map(() => Math.random() * 100),
                        borderColor: '#6c5ce7',
                        backgroundColor: 'rgba(108, 92, 231, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#dfe6e9' }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#a29bfe' }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#a29bfe' }
                    }
                }
            }
        });
        this.charts.set(hostId, chart);
    }
    
    updateLastUpdateTime() {
        const now = new Date();
        document.getElementById('lastUpdateTime').textContent = 
            `最后更新: ${now.toLocaleTimeString()}`;
    }
    
    startAutoRefresh() {
        this.stopAutoRefresh(); // 清除现有定时器
        
        this.refreshInterval = setInterval(async () => {
            await this.loadMonitoringData();
        }, this.refreshRate);
        
        document.getElementById('refreshStatus').textContent = '🟢🟢🟢 实时刷新中';
        document.getElementById('refreshStatus').style.color = '#2ecc71';
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        
        document.getElementById('refreshStatus').textContent = '🔴🔴 刷新已暂停';
        document.getElementById('refreshStatus').style.color = '#e74c3c';
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.hostManager = new HostManager();
    window.dashboard = new MonitoringDashboard();
    
    // 添加手动刷新功能
    document.addEventListener('keydown', (e) => {
        if (e.key === 'r' && e.ctrlKey) {
            e.preventDefault();
            if (window.dashboard) {
                window.dashboard.loadMonitoringData();
            }
        }
    });
    
    console.log('服务器监控系统前端已初始化');
});