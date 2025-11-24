from flask import Flask, render_template, request, jsonify
import json
import os
import time
import paramiko
from datetime import datetime
import re
import subprocess

app = Flask(__name__)

# 数据文件路径
DATA_DIR = 'data'
HOSTS_FILE = os.path.join(DATA_DIR, 'hosts.json')

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

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
        # 执行top命令获取CPU信息
        stdin, stdout, stderr = ssh.exec_command("top -bn1 | grep '%Cpu'")
        cpu_output = stdout.read().decode('utf-8')
        
        # 解析CPU使用率 (用户态+系统态)
        cpu_match = re.search(r'%Cpu\(s\):\s+([\d.]+)\s+us,\s+([\d.]+)\s+sy', cpu_output)
        if cpu_match:
            cpu_usage = float(cpu_match.group(1)) + float(cpu_match.group(2))
            metrics['cpu_usage'] = round(cpu_usage, 1)
        else:
            # 备用方法：使用/proc/stat计算CPU使用率
            stdin, stdout, stderr = ssh.exec_command("cat /proc/stat | grep '^cpu '")
            cpu_stat = stdout.read().decode('utf-8').strip().split()
            
            if len(cpu_stat) >= 8:
                # 计算总CPU时间
                total_time = sum(map(int, cpu_stat[1:8]))
                idle_time = int(cpu_stat[4])
                cpu_usage = 100.0 * (1 - idle_time / total_time) if total_time > 0 else 0
                metrics['cpu_usage'] = round(cpu_usage, 1)
            else:
                metrics['cpu_usage'] = 0
        
        # 2. 获取内存使用率
        # 执行free命令获取内存信息
        stdin, stdout, stderr = ssh.exec_command("free | grep Mem")
        mem_output = stdout.read().decode('utf-8')
        
        # 解析内存使用率
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
        
        # 解析根分区磁盘使用率
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
            metrics['net_in'] = int(net_data[1]) // 1024 // 1024  # 转换为MB
            metrics['net_out'] = int(net_data[9]) // 1024 // 1024  # 转换为MB
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
    """生成真实监控数据"""
    hosts = load_hosts()
    monitoring_data = []
    
    for host in hosts:
        # 检查主机是否在线（ping测试）
        ping_status = subprocess.call(
            ['ping', '-c', '1', '-W', '2', host['hostIp']], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        ) == 0
        
        if ping_status:
            # 尝试通过SSH获取真实数据
            real_metrics = get_real_metrics(host)
            
            if real_metrics:
                # 使用真实数据
                monitoring_data.append({
                    'hostId': host['id'],
                    'hostIp': host['hostIp'],
                    'status': 'online',
                    'timestamp': datetime.now().isoformat(),
                    'realData': True,  # 标记为真实数据
                    'metrics': {
                        'cpu': {
                            'usage': real_metrics['cpu_usage'],
                            'temperature': 40  # 默认值，需要额外命令获取
                        },
                        'memory': {
                            'usage': real_metrics['mem_usage'],
                            'total': real_metrics['mem_total'],
                            'used': real_metrics['mem_used']
                        },
                        'disk': {
                            'usage': real_metrics['disk_usage'],
                            'total': 100,  # 默认值
                            'used': 0
                        },
                        'network': {
                            'in': real_metrics['net_in'],
                            'out': real_metrics['net_out']
                        }
                    }
                })
            else:
                # SSH连接失败，使用模拟数据但标记为离线
                monitoring_data.append(generate_mock_data(host, False))
        else:
            # 主机离线，使用模拟数据
            monitoring_data.append(generate_mock_data(host, False))
    
    return monitoring_data

def generate_mock_data(host, online=True):
    """生成模拟监控数据（备用）"""
    return {
        'hostId': host['id'],
        'hostIp': host['hostIp'],
        'status': 'online' if online else 'offline',
        'timestamp': datetime.now().isoformat(),
        'realData': False,  # 标记为模拟数据
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

# API 路由
@app.route('/api/hosts', methods=['GET'])
def get_hosts():
    """获取所有主机"""
    return jsonify(load_hosts())

@app.route('/api/hosts', methods=['POST'])
def add_host():
    """添加新主机"""
    data = request.json
    
    # 验证必要字段
    required_fields = ['hostIp', 'sshUser', 'sshPassword']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'缺少必要字段: {field}'}), 400
    
    # IP地址验证
    if not is_valid_ip(data['hostIp']):
        return jsonify({'error': '无效的IP地址格式'}), 400
    
    hosts = load_hosts()
    
    # 检查IP是否已存在
    if any(host['hostIp'] == data['hostIp'] for host in hosts):
        return jsonify({'error': '该IP地址的主机已存在'}), 400
    
    # 测试SSH连接
    test_result = test_ssh_connection(
        data['hostIp'], 
        data['sshUser'], 
        data['sshPassword'], 
        data.get('sshPort', '22')
    )
    
    if not test_result['success']:
        return jsonify({'error': f'SSH连接测试失败: {test_result["message"]}'}), 400
    
    # 添加新主机
    new_host = {
        'id': int(time.time() * 1000),  # 使用时间戳作为ID
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
        
        # 测试执行简单命令
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
    app.run(host='0.0.0.0', port=5000, debug=False)