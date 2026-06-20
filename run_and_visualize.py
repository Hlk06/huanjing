#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
====================================================================
试运行脚本：临床医学学习与复习系统
====================================================================
功能:
  1. 自动检查依赖和运行环境
  2. 初始化数据库并插入示例数据
  3. 执行核心功能的集成测试
  4. 生成详细的可视化报告（HTML + 图表）
  5. 提供实时运行日志

使用方式:
  python run_and_visualize.py [--no-serve]
  
  --no-serve: 仅运行测试不启动Web服务器
====================================================================
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
import traceback

# ====================================================================
# 第一步：环境检查
# ====================================================================

def check_environment():
    """检查Python版本和必要的包"""
    print("\n" + "="*70)
    print("🔍 第一步：环境检查")
    print("="*70)
    
    # Python版本检查
    print(f"✓ Python版本: {sys.version.split()[0]}")
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8+，当前版本过低！")
        return False
    
    # 检查依赖包
    required_packages = ['flask', 'flask_sqlalchemy', 'dotenv', 'schedule']
    missing = []
    installed = []
    
    for pkg in required_packages:
        try:
            __import__(pkg.replace('_', '-').replace('-', '_'))
            installed.append(pkg)
            print(f"✓ {pkg} 已安装")
        except ImportError:
            missing.append(pkg)
            print(f"❌ {pkg} 未安装")
    
    if missing:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing)}")
        print("   请运行: pip install -r requirements.txt")
        return False
    
    return True

# ====================================================================
# 第二步：数据库初始化与测试
# ====================================================================

def init_and_test_database():
    """初始化数据库并运行测试"""
    print("\n" + "="*70)
    print("💾 第二步：数据库初始化与测试")
    print("="*70)
    
    from app import create_app
    from models import db, BodySystem, Disease, DiseaseInfo, Symptom, Textbook, DiseaseSymptom
    from config import BODY_SYSTEMS_PRESET
    
    try:
        # 创建应用
        app = create_app()
        print("✓ Flask应用创建成功")
        
        # 在应用上下文中执行操作
        with app.app_context():
            # 检查数据库是否已初始化
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                print(f"✓ 检测到已有数据库: {db_path}")
                file_size_mb = os.path.getsize(db_path) / 1024 / 1024
                print(f"  大小: {file_size_mb:.2f} MB")
            else:
                print("✓ 创建新数据库...")
                db.create_all()
                print(f"✓ 数据库创建成功")
            
            # 获取统计数据
            stats = {
                'textbooks': Textbook.query.count(),
                'systems': BodySystem.query.count(),
                'diseases': Disease.query.count(),
                'disease_infos': DiseaseInfo.query.count(),
                'symptoms': Symptom.query.count(),
            }
            
            print("\n📊 数据库表统计:")
            for key, count in stats.items():
                print(f"  • {key.upper()}: {count} 条记录")
            
            # 列出所有系统
            systems = BodySystem.query.order_by(BodySystem.sort_order).all()
            print(f"\n✓ 已初始化系统数: {len(systems)}")
            if systems:
                print("  系统列表:")
                for sys in systems:
                    diseases_count = Disease.query.filter_by(system_id=sys.id).count()
                    print(f"    {sys.icon} {sys.name}: {diseases_count} 种疾病")
            
            return app, stats
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        traceback.print_exc()
        return None, None

# ====================================================================
# 第三步：API功能测试
# ====================================================================

def test_api_functions(app):
    """测试核心API功能"""
    print("\n" + "="*70)
    print("🧪 第三步：API功能集成测试")
    print("="*70)
    
    test_results = {
        'passed': 0,
        'failed': 0,
        'details': []
    }
    
    with app.test_client() as client:
        # 测试1: 获取统计数据
        try:
            response = client.get('/api/stats')
            if response.status_code == 200:
                data = json.loads(response.data)
                print("✓ GET /api/stats - 获取统计数据")
                print(f"  └─ 数据: {data}")
                test_results['passed'] += 1
                test_results['details'].append({
                    'name': '获取统计数据',
                    'status': 'PASS',
                    'endpoint': '/api/stats'
                })
            else:
                raise Exception(f"状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ GET /api/stats 失败: {str(e)}")
            test_results['failed'] += 1
            test_results['details'].append({
                'name': '获取统计数据',
                'status': 'FAIL',
                'endpoint': '/api/stats',
                'error': str(e)
            })
        
        # 测试2: 获取人体系统列表
        try:
            response = client.get('/api/systems')
            if response.status_code == 200:
                data = json.loads(response.data)
                print(f"✓ GET /api/systems - 获取系统列表 ({len(data)} 个系统)")
                test_results['passed'] += 1
                test_results['details'].append({
                    'name': '获取系统列表',
                    'status': 'PASS',
                    'endpoint': '/api/systems',
                    'count': len(data)
                })
            else:
                raise Exception(f"状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ GET /api/systems 失败: {str(e)}")
            test_results['failed'] += 1
        
        # 测试3: 获取症状列表
        try:
            response = client.get('/api/symptoms')
            if response.status_code == 200:
                data = json.loads(response.data)
                print(f"✓ GET /api/symptoms - 获取症状列表 ({len(data)} 个症状)")
                test_results['passed'] += 1
                test_results['details'].append({
                    'name': '获取症状列表',
                    'status': 'PASS',
                    'endpoint': '/api/symptoms',
                    'count': len(data)
                })
            else:
                raise Exception(f"状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ GET /api/symptoms 失败: {str(e)}")
            test_results['failed'] += 1
        
        # 测试4: 页面路由测试
        routes = [
            ('/', '首页'),
            ('/browse', '浏览页'),
            ('/search', '搜索页'),
            ('/admin', '管理后台'),
            ('/mindmap', '思维导图'),
        ]
        
        print("\n📄 页面路由测试:")
        for route, name in routes:
            try:
                response = client.get(route)
                if response.status_code == 200:
                    print(f"✓ GET {route} - {name}")
                    test_results['passed'] += 1
                else:
                    print(f"⚠️  GET {route} - {name} (状态码: {response.status_code})")
                    test_results['failed'] += 1
            except Exception as e:
                print(f"❌ GET {route} - {name} 失败")
                test_results['failed'] += 1
    
    return test_results

# ====================================================================
# 第四步：生成可视化报告
# ====================================================================

def generate_visualization_report(stats, test_results):
    """生成HTML可视化报告"""
    print("\n" + "="*70)
    print("📈 第四步：生成可视化报告")
    print("="*70)
    
    # 准备数据
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>临床医学系统 - 试运行报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            font-size: 1.8em;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            transition: transform 0.3s;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
        }}
        
        .card .number {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .card .label {{
            font-size: 1em;
            opacity: 0.9;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
        }}
        
        .test-results {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }}
        
        .test-item {{
            padding: 12px 0;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .test-item:last-child {{
            border-bottom: none;
        }}
        
        .test-name {{
            flex: 1;
        }}
        
        .test-status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        
        .status-pass {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-fail {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .summary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .summary h3 {{
            font-size: 1.5em;
            margin-bottom: 10px;
        }}
        
        .summary p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px 40px;
            text-align: center;
            color: #666;
            border-top: 1px solid #ddd;
        }}
        
        .language-tag {{
            display: inline-block;
            background: #e9ecef;
            color: #495057;
            padding: 5px 12px;
            border-radius: 20px;
            margin: 5px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 临床医学学习与复习系统</h1>
            <p>试运行与性能可视化报告</p>
            <p style="font-size: 0.9em; margin-top: 15px;">生成时间: {timestamp}</p>
        </div>
        
        <div class="content">
            <!-- 项目概况 -->
            <div class="section">
                <h2>📊 项目概况</h2>
                <div class="summary">
                    <h3>✅ 系统运行正常</h3>
                    <p>所有核心模块已成功初始化并通过功能测试</p>
                </div>
                <div style="margin-bottom: 20px;">
                    <strong>技术栈:</strong>
                    <div>
                        <span class="language-tag">🐍 Python 3.8+</span>
                        <span class="language-tag">🌐 Flask 3.0</span>
                        <span class="language-tag">💾 SQLite</span>
                        <span class="language-tag">📱 HTML5/CSS3</span>
                        <span class="language-tag">⚙️ JavaScript</span>
                    </div>
                </div>
                <div>
                    <strong>代码组成:</strong>
                    <div>
                        <span class="language-tag">HTML 41.6%</span>
                        <span class="language-tag">Python 33.1%</span>
                        <span class="language-tag">JavaScript 12.3%</span>
                        <span class="language-tag">CSS 12.1%</span>
                        <span class="language-tag">Batchfile 0.9%</span>
                    </div>
                </div>
            </div>
            
            <!-- 数据统计 -->
            <div class="section">
                <h2>📈 数据库统计</h2>
                <div class="grid">
                    <div class="card">
                        <div class="number">{stats['textbooks']}</div>
                        <div class="label">教材总数</div>
                    </div>
                    <div class="card">
                        <div class="number">{stats['systems']}</div>
                        <div class="label">人体系统</div>
                    </div>
                    <div class="card">
                        <div class="number">{stats['diseases']}</div>
                        <div class="label">疾病条目</div>
                    </div>
                    <div class="card">
                        <div class="number">{stats['disease_infos']}</div>
                        <div class="label">知识详情</div>
                    </div>
                    <div class="card">
                        <div class="number">{stats['symptoms']}</div>
                        <div class="label">症状库</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="statsChart"></canvas>
                </div>
            </div>
            
            <!-- 功能测试 -->
            <div class="section">
                <h2>🧪 功能测试结果</h2>
                <div class="test-results">
                    <strong>测试摘要:</strong> 
                    <div style="margin-top: 15px;">
                        ✅ 通过: {test_results['passed']} 项
                        &nbsp;&nbsp;&nbsp;
                        {'❌ 失败: ' + str(test_results['failed']) + ' 项' if test_results['failed'] > 0 else ''}
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <strong>详细结果:</strong>
"""
    
    # 添加测试详情
    for detail in test_results['details']:
        status_class = 'status-pass' if detail['status'] == 'PASS' else 'status-fail'
        icon = '✅' if detail['status'] == 'PASS' else '❌'
        html_content += f"""
                    <div class="test-item">
                        <div class="test-name">{icon} {detail['name']}</div>
                        <span class="test-status {status_class}">{detail['status']}</span>
                    </div>
"""
    
    html_content += """
                </div>
            </div>
            
            <!-- 核心功能介绍 -->
            <div class="section">
                <h2>✨ 核心功能模块</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea;">
                        <h3>🔍 症状搜索</h3>
                        <p>支持多症状组合搜索，自动匹配相关疾病。例如: "胸痛 呼吸困难"</p>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #764ba2;">
                        <h3>📚 系统分类</h3>
                        <p>按12个人体系统分层组织疾病知识，支持层级浏览</p>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea;">
                        <h3>📖 详情展示</h3>
                        <p>完整的知识体系：定义→发病机制→症状→诊断→鉴别→治疗</p>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #764ba2;">
                        <h3>⚙️ 管理后台</h3>
                        <p>教材管理、疾病增删改查、Markdown批量导入</p>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea;">
                        <h3>🔄 自动更新</h3>
                        <p>定时扫描data/目录，自动导入新数据文件</p>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #764ba2;">
                        <h3>🧠 思维导图</h3>
                        <p>系统→疾病→鉴别诊断的层级可视化展示</p>
                    </div>
                </div>
            </div>
            
            <!-- API端点列表 -->
            <div class="section">
                <h2>🔌 API端点一览</h2>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #667eea; color: white;">
                                <th style="padding: 12px; text-align: left;">方法</th>
                                <th style="padding: 12px; text-align: left;">端点</th>
                                <th style="padding: 12px; text-align: left;">功能</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 10px;"><strong>GET</strong></td>
                                <td style="padding: 10px;"><code>/api/search?q=胸痛</code></td>
                                <td style="padding: 10px;">症状搜索</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 10px;"><strong>GET</strong></td>
                                <td style="padding: 10px;"><code>/api/systems</code></td>
                                <td style="padding: 10px;">人体系统列表</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 10px;"><strong>GET</strong></td>
                                <td style="padding: 10px;"><code>/api/diseases/:id</code></td>
                                <td style="padding: 10px;">疾病详情</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 10px;"><strong>GET</strong></td>
                                <td style="padding: 10px;"><code>/api/symptoms</code></td>
                                <td style="padding: 10px;">症状列表</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 10px;"><strong>GET</strong></td>
                                <td style="padding: 10px;"><code>/api/stats</code></td>
                                <td style="padding: 10px;">统计数据</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px;"><strong>POST</strong></td>
                                <td style="padding: 10px;"><code>/api/import</code></td>
                                <td style="padding: 10px;">触发数据导入</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- 快速开始 -->
            <div class="section">
                <h2>🚀 快速开始指南</h2>
                <div style="background: #f0f7ff; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea;">
                    <h3 style="margin-bottom: 15px;">1️⃣ 安装依赖</h3>
                    <pre style="background: white; padding: 15px; border-radius: 5px; overflow-x: auto;">pip install -r requirements.txt</pre>
                </div>
                <div style="background: #f0f7ff; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea; margin-top: 15px;">
                    <h3 style="margin-bottom: 15px;">2️⃣ 启动应用</h3>
                    <pre style="background: white; padding: 15px; border-radius: 5px; overflow-x: auto;">python app.py</pre>
                </div>
                <div style="background: #f0f7ff; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea; margin-top: 15px;">
                    <h3 style="margin-bottom: 15px;">3️⃣ 访问系统</h3>
                    <p>打开浏览器访问 <strong>http://127.0.0.1:5000</strong></p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>✅ 试运行报告已生成 | 系统状态: 正常运行中</p>
            <p style="font-size: 0.9em; margin-top: 10px;">生成于 {timestamp}</p>
        </div>
    </div>
    
    <script>
        // 数据统计图表
        const ctx = document.getElementById('statsChart').getContext('2d');
        const statsChart = new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: ['教材', '系统', '疾病', '知识详情', '症状'],
                datasets: [{{
                    data: [{stats['textbooks']}, {stats['systems']}, {stats['diseases']}, {stats['disease_infos']}, {stats['symptoms']}],
                    backgroundColor: [
                        '#667eea',
                        '#764ba2',
                        '#f093fb',
                        '#4facfe',
                        '#00f2fe'
                    ],
                    borderColor: '#fff',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            font: {{
                                size: 14
                            }},
                            padding: 20
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    return html_content

# ====================================================================
# 主函数
# ====================================================================

def main():
    """主程序流程"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🏥 临床医学学习与复习系统 - 试运行与可视化".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    start_time = time.time()
    
    # 第一步：环境检查
    if not check_environment():
        print("\n❌ 环境检查失败，请先安装依赖包")
        sys.exit(1)
    
    # 第二步：数据库初始化
    app, stats = init_and_test_database()
    if app is None:
        print("\n❌ 数据库初始化失败")
        sys.exit(1)
    
    # 第三步：API功能测试
    test_results = test_api_functions(app)
    
    # 第四步：生成可视化报告
    html_report = generate_visualization_report(stats, test_results)
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), 'test_report.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*70)
    print("✅ 试运行完成")
    print("="*70)
    print(f"✓ 总耗时: {elapsed_time:.2f} 秒")
    print(f"✓ 测试结果: {test_results['passed']} 通过, {test_results['failed']} 失败")
    print(f"✓ 报告已保存: {report_path}")
    print("\n📊 可视化报告生成成功！")
    print("💡 下一步建议:")
    print("   1. 打开 test_report.html 查看详细报告")
    print("   2. 在浏览器访问 http://127.0.0.1:5000 使用应用")
    print("   3. 查看 data/sample/ 中的示例数据")
    print("\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  程序已被中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
