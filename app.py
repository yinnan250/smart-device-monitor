from flask import Flask, render_template, request, jsonify
import json
import os
import time
from datetime import datetime

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

def generate_mock_monitoring_data():
    """生成模拟监控数据"""
    hosts = load_hosts()
    monitoring_data = []
    
    for host in hosts:
        monitoring_data.append({
            'hostId': host['id'],
            'hostIp': host['hostIp'],
            'status': 'online' if os.system(f"ping -c 1 -W 1 {host['hostIp']}") == 0 else 'offline',
            'timestamp': datetime.now().isoformat(),
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
        })
    
    return monitoring_data

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
    """获取监控数据"""
    return jsonify(generate_mock_monitoring_data())

def is_valid_ip(ip):
    """验证IP地址格式"""
    import re
    pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
    if not re.match(pattern, ip):
        return False
    
    return all(0 <= int(segment) <= 255 for segment in ip.split('.'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)