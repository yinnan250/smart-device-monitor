from flask import Flask, render_template, request, jsonify
import json
import os
import time
import paramiko
from datetime import datetime
import re
import subprocess
import sqlite3
from contextlib import contextmanager

app = Flask(__name__)

# 数据文件路径
DATA_DIR = 'data'
HOSTS_FILE = os.path.join(DATA_DIR, 'hosts.json')
DB_FILE = os.path.join(DATA_DIR, 'monitor.db')

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建监控数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitoring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_id INTEGER NOT NULL,
            host_ip TEXT NOT NULL,
            status TEXT NOT NULL,
            cpu_usage REAL NOT NULL,
            memory_usage REAL NOT NULL,
            memory_total INTEGER NOT NULL,
            memory_used INTEGER NOT NULL,
            disk_usage REAL NOT NULL,
            network_in INTEGER NOT NULL,
            network_out INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            real_data BOOLEAN NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引以提高查询性能
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_host_id ON monitoring_data(host_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON monitoring_data(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_host_timestamp ON monitoring_data(host_id, timestamp)')
    
    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def save_monitoring_data(monitoring_data):
    """保存监控数据到数据库"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for host_data in monitoring_data:
            metrics = host_data['metrics']
            cursor.execute('''
                INSERT INTO monitoring_data 
                (host_id, host_ip, status, cpu_usage, memory_usage, memory_total, memory_used, 
                 disk_usage, network_in, network_out, timestamp, real_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                host_data['hostId'],
                host_data['hostIp'],
                host_data['status'],
                metrics['cpu']['usage'],
                metrics['memory']['usage'],
                metrics['memory']['total'],
                metrics['memory']['used'],
                metrics['disk']['usage'],
                metrics['network']['in'],
                metrics['network']['out'],
                host_data['timestamp'],
                host_data['realData']
            ))
        
        conn.commit()

def get_historical_data(host_id=None, hours=24, limit=1000):
    """获取历史监控数据"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM monitoring_data 
            WHERE timestamp >= datetime('now', ?)
        '''
        params = [f'-{hours} hours']
        
        if host_id:
            query += ' AND host_id = ?'
            params.append(host_id)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 转换为字典列表
        return [dict(row) for row in rows]

def get_latest_data(host_id=None):
    """获取最新的监控数据"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if host_id:
            cursor.execute('''
                SELECT * FROM monitoring_data 
                WHERE host_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (host_id,))
        else:
            cursor.execute('''
                SELECT md1.* FROM monitoring_data md1
                INNER JOIN (
                    SELECT host_id, MAX(timestamp) as max_timestamp
                    FROM monitoring_data
                    GROUP BY host_id
                ) md2 ON md1.host_id = md2.host_id AND md1.timestamp = md2.max_timestamp
            ''')
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def load_hosts():
    """加载主机数据"""
    if os.path.exists(HOSTS_FILE):
        with open(HOSTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_hosts(hosts):
    """保存主机数据"""
    with open(HOSTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(hosts, f, ensure_ascii=False, indent=2)

def get_real_metrics(host):
    """
    通过SSH连接到服务器获取真实监控数据
    返回: 包含CPU和内存使用率的字典，如果失败返回None
    """
    try:
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 连接参数
        hostname = host['hostIp']
        username = host['sshUser']
        password = host['sshPassword']
        port = int(host.get('sshPort', 22))
        
        # 设置连接超时
        ssh.connect(hostname, port=port, username=username, password=password, timeout=10)
        
        metrics = {}
        
        # 1. 获取CPU使用率
        stdin, stdout, stderr = ssh.exec_command("top -bn1 | grep '%Cpu'")
        cpu_output = stdout.read().decode('utf-8')
        
        cpu_match = re.search(r'%Cpu\(s\):\s+([\d.]+)\s+us,\s+([\d.]+)\s+sy', cpu_output)
        if cpu_match:
            cpu_usage = float(cpu_match.group(1)) + float(cpu_match.group(2))
            metrics['cpu_usage'] = round(cpu_usage, 1)
        else:
            stdin, stdout, stderr = ssh.exec_command("cat /proc/stat | grep '^cpu '")
            cpu_stat = stdout.read().decode('utf-8').strip().split()
            
            if len(cpu_stat) >= 8:
                total_time = sum(map(int, cpu_stat[1:8]))
                idle_time = int(cpu_stat[4])
                cpu_usage = 100.0 * (1 - idle_time / total_time) if total_time > 0 else 0
                metrics['cpu_usage'] = round(cpu_usage, 1)
            else:
                metrics['cpu_usage'] = 0
        
        # 2. 获取内存使用率
        stdin, stdout, stderr = ssh.exec_command("free | grep Mem")
        mem_output = stdout.read().decode('utf-8')
        
        mem_match = re.search(r'Mem:\s+(\d+)\s+(\d+)\s+(\d+)', mem_output)
        if mem_match:
            total_mem = int(mem_match.group(1))
            used_mem = int(mem_match.group(2))
            mem_usage = 100.0 * used_mem / total_mem if total_mem > 0 else 0
            metrics['mem_usage'] = round(mem_usage, 1)
            metrics['mem_total'] = total_mem
            metrics['mem_used'] = used_mem
        else:
            metrics['mem_usage'] = 0
            metrics['mem_total'] = 0
            metrics['mem_used'] = 0
        
        # 3. 获取磁盘使用率
        stdin, stdout, stderr = ssh.exec_command("df / | tail -1")
        disk_output = stdout.read().decode('utf-8')
        
        disk_match = re.search(r'(\d+)%\s+/', disk_output)
        if disk_match:
            metrics['disk_usage'] = int(disk_match.group(1))
        else:
            metrics['disk_usage'] = 0
        
        # 4. 获取网络流量（可选）
        stdin, stdout, stderr = ssh.exec_command("cat /proc/net/dev | grep -E '(eth0|ens|enp)' | head -1")
        net_output = stdout.read().decode('utf-8')
        
        if net_output:
            net_data = net_output.split()
            metrics['net_in'] = int(net_data[1]) // 1024 // 1024
            metrics['net_out'] = int(net_data[9]) // 1024 // 1024
        else:
            metrics['net_in'] = 0
            metrics['net_out'] = 0
        
        ssh.close()
        return metrics
        
    except Exception as e:
        print(f"SSH连接错误 ({host['hostIp']}): {str(e)}")
        try:
            ssh.close()
        except:
            pass
        return None

def generate_real_monitoring_data():
    """生成真实监控数据并保存到数据库"""
    hosts = load_hosts()
    monitoring_data = []
    
    for host in hosts:
        ping_status = subprocess.call(
            ['ping', '-c', '1', '-W', '2', host['hostIp']], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        ) == 0
        
        if ping_status:
            real_metrics = get_real_metrics(host)
            
            if real_metrics:
                host_data = {
                    'hostId': host['id'],
                    'hostIp': host['hostIp'],
                    'status': 'online',
                    'timestamp': datetime.now().isoformat(),
                    'realData': True,
                    'metrics': {
                        'cpu': {
                            'usage': real_metrics['cpu_usage'],
                            'temperature': 40
                        },
                        'memory': {
                            'usage': real_metrics['mem_usage'],
                            'total': real_metrics['mem_total'],
                            'used': real_metrics['mem_used']
                        },
                        'disk': {
                            'usage': real_metrics['disk_usage'],
                            'total': 100,
                            'used': 0
                        },
                        'network': {
                            'in': real_metrics['net_in'],
                            'out': real_metrics['net_out']
                        }
                    }
                }
                monitoring_data.append(host_data)
            else:
                monitoring_data.append(generate_mock_data(host, False))
        else:
            monitoring_data.append(generate_mock_data(host, False))
    
    # 保存监控数据到数据库
    save_monitoring_data(monitoring_data)
    
    return monitoring_data

def generate_mock_data(host, online=True):
    """生成模拟监控数据（备用）"""
    return {
        'hostId': host['id'],
        'hostIp': host['hostIp'],
        'status': 'online' if online else 'offline',
        'timestamp': datetime.now().isoformat(),
        'realData': False,
        'metrics': {
            'cpu': {
                'usage': min(100, max(5, abs(hash(f"{host['id']}{int(time.time()/10)}")) % 100)),
                'temperature': 40 + abs(hash(f"temp{host['id']}")) % 40
            },
            'memory': {
                'usage': min(100, max(10, abs(hash(f"mem{host['id']}{int(time.time()/8)}")) % 100)),
                'total': 16,
                'used': 0
            },
            'disk': {
                'usage': min(100, max(5, abs(hash(f"disk{host['id']}{int(time.time()/12)}")) % 100)),
                'total': 500,
                'used': 0
            },
            'network': {
                'in': abs(hash(f"net_in{host['id']}")) % 100,
                'out': abs(hash(f"net_out{host['id']}")) % 50
            }
        }
    }

# 前端页面路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/host-management')
def host_management():
    return render_template('host-management.html')

@app.route('/data-history')
def data_history():
    return render_template('data-history.html')

# API 路由
@app.route('/api/hosts', methods=['GET'])
def get_hosts():
    """获取所有主机"""
    return jsonify(load_hosts())

@app.route('/api/hosts', methods=['POST'])
def add_host():
    """添加新主机"""
    data = request.json
    
    required_fields = ['hostIp', 'sshUser', 'sshPassword']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'缺少必要字段: {field}'}), 400
    
    if not is_valid_ip(data['hostIp']):
        return jsonify({'error': '无效的IP地址格式'}), 400
    
    hosts = load_hosts()
    
    if any(host['hostIp'] == data['hostIp'] for host in hosts):
        return jsonify({'error': '该IP地址的主机已存在'}), 400
    
    test_result = test_ssh_connection(
        data['hostIp'], 
        data['sshUser'], 
        data['sshPassword'], 
        data.get('sshPort', '22')
    )
    
    if not test_result['success']:
        return jsonify({'error': f'SSH连接测试失败: {test_result["message"]}'}), 400
    
    new_host = {
        'id': int(time.time() * 1000),
        'hostIp': data['hostIp'],
        'sshUser': data['sshUser'],
        'sshPassword': data['sshPassword'],
        'sshPort': data.get('sshPort', '22'),
        'createdAt': datetime.now().isoformat()
    }
    
    hosts.append(new_host)
    save_hosts(hosts)
    
    return jsonify(new_host)

@app.route('/api/hosts/<int:host_id>', methods=['DELETE'])
def delete_host(host_id):
    """删除主机"""
    hosts = load_hosts()
    filtered_hosts = [host for host in hosts if host['id'] != host_id]
    
    if len(filtered_hosts) == len(hosts):
        return jsonify({'error': '主机不存在'}), 404
    
    save_hosts(filtered_hosts)
    return jsonify({'message': '主机删除成功'})

@app.route('/api/monitoring/data', methods=['GET'])
def get_monitoring_data():
    """获取监控数据（优先使用真实数据）"""
    return jsonify(generate_real_monitoring_data())

@app.route('/api/history/data', methods=['GET'])
def get_history_data():
    """获取历史监控数据"""
    host_id = request.args.get('host_id', type=int)
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 1000, type=int)
    
    try:
        data = get_historical_data(host_id, hours, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': f'获取历史数据失败: {str(e)}'}), 500

@app.route('/api/history/hosts', methods=['GET'])
def get_history_hosts():
    """获取有历史数据的主机列表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT host_id, host_ip 
            FROM monitoring_data 
            ORDER BY host_ip
        ''')
        hosts = [dict(row) for row in cursor.fetchall()]
        return jsonify(hosts)

@app.route('/api/test-ssh', methods=['POST'])
def test_ssh():
    """测试SSH连接"""
    data = request.json
    result = test_ssh_connection(
        data['hostIp'],
        data['sshUser'],
        data['sshPassword'],
        data.get('sshPort', '22')
    )
    return jsonify(result)

def test_ssh_connection(host_ip, username, password, port='22'):
    """测试SSH连接"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host_ip, port=int(port), username=username, password=password, timeout=10)
        
        stdin, stdout, stderr = ssh.exec_command('echo "SSH连接测试成功"')
        output = stdout.read().decode('utf-8').strip()
        
        ssh.close()
        return {'success': True, 'message': 'SSH连接测试成功'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def is_valid_ip(ip):
    """验证IP地址格式"""
    import re
    pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
    if not re.match(pattern, ip):
        return False
    
    return all(0 <= int(segment) <= 255 for segment in ip.split('.'))

if __name__ == '__main__':
    # 初始化数据库
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=False)