from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>服务器监控系统</title></head>
    <body>
        <h1>服务器监控数据大屏</h1>
        <h2>主机管理</h2>
        <form action="/add_host" method="post">
            IP: <input name="ip" required><br>
            用户: <input name="user" required><br>
            密码: <input type="password" name="pwd" required><br>
            端口: <input name="port" value="22"><br>
            <button type="submit">添加主机</button>
        </form>
        <h3>已添加主机</h3>
        <table border="1">
            <tr><th>IP</th><th>用户</th><th>操作</th></tr>
            <tr><td>示例主机</td><td>root</td><td><a href="/delete?ip=示例">删除</a></td></tr>
        </table>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)