# 临床医学学习与复习系统 v1.0

## 📖 项目简介

一个本地运行的临床医学学习软件，覆盖**本科5年 + 研究生3年**的医学教材内容。按**12个人体系统**分类组织疾病，支持通过**临床症状**搜索疾病，展示完整的疾病信息（定义、发病机制、预防原则、治疗方案、鉴别诊断），每项内容**强制标注出处**（教材名+版次+章节+页码），方便医学学习和复习。

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🎓🔬 **双板块** | 本科板块 + 研究生板块，内容按难度分层 |
| 🧠 **系统分类** | 12个人体系统（心血管、呼吸、消化...），层级浏览 |
| 🔍 **症状搜索** | 多症状组合搜索（如"胸痛 呼吸困难"），自动匹配疾病 |
| 📋 **完整信息** | 定义 → 发病机制 → 预防 → 治疗 → 鉴别诊断，5类Tab切换 |
| 📚 **来源引用** | 每条内容强制标注出处（教材名、版次、出版社、章节、页码） |
| ⚙️ **管理后台** | 教材管理、疾病增删改查、Markdown批量导入 |
| 🔄 **定时更新** | 自动检测data/目录新文件并导入 |

---

## 🛠️ 技术栈

| 层面 | 技术 |
|------|------|
| 后端 | Python 3 + Flask |
| 数据库 | SQLite（零配置本地数据库） |
| ORM | Flask-SQLAlchemy |
| 前端 | HTML5 + Bootstrap 5 + Vanilla JS |
| 搜索 | SQLite LIKE + 多路径匹配算法 |
| 导入 | Markdown/JSON 解析器 |
| 定时 | schedule（后台线程） |

---

## 🚀 快速开始

### 1. 环境要求
- Python 3.8+
- Windows / macOS / Linux

### 2. 安装依赖
```bash
cd d:\医疗
pip install -r requirements.txt
```

### 3. 启动应用
```bash
python app.py
```

### 4. 访问系统
浏览器打开 **http://127.0.0.1:5000**

### 5. 导入示例数据
启动后，进入「管理后台」→「批量导入」→ 点击「开始导入」，系统将自动导入 `data/sample/` 下的示例数据。

或通过命令行：
```python
# 在Python交互环境中
from app import create_app
from data_importer import DataImporter
app = create_app()
with app.app_context():
    importer = DataImporter()
    result = importer.import_from_data_dir()
    print(result)
```

---

## 📁 项目结构

```
d:\医疗\
├── app.py                    # Flask主应用入口（路由、配置）
├── models.py                 # 数据库模型定义（ORM）
├── search_engine.py          # 全文搜索引擎
├── data_importer.py          # 教材内容导入工具（Markdown/JSON）
├── updater.py                # 定时更新调度器
├── config.py                 # 全局配置
├── requirements.txt          # Python依赖清单
├── medical.db                # SQLite数据库（启动后自动生成）
├── README.md                 # 本文件
├── static/
│   ├── css/style.css         # 自定义样式
│   └── js/
│       ├── common.js         # 公共工具函数
│       ├── search.js         # 搜索页交互
│       └── browse.js         # 浏览页交互
├── templates/
│   ├── base.html             # 基础模板（导航+页脚）
│   ├── index.html            # 首页（双板块入口+搜索）
│   ├── browse.html           # 按系统浏览页
│   ├── disease_detail.html   # 疾病详情页（Tab切换）
│   ├── search.html           # 症状搜索页
│   └── admin.html            # 管理后台
└── data/
    ├── import_log.md         # 导入日志（自动生成）
    └── sample/               # 示例数据
        ├── cardiovascular.md # 心血管系统（冠心病、高血压、心衰）
        └── respiratory.md    # 呼吸系统（COPD、肺炎）
```

---

## 📝 数据导入格式

### Markdown格式示例

```markdown
## 教材: 内科学
作者: 葛均波
版次: 第九版
出版社: 人民卫生出版社
年份: 2018
层次: undergraduate

### 疾病: 冠心病
英文名: Coronary Heart Disease
系统: 心血管系统
层次: undergraduate
关联症状: 胸痛(main), 呼吸困难(common), 心悸(common)
概述: 冠状动脉粥样硬化导致...

#### 定义
正文内容...
出处页码: P234-240
出处章节: 第8章 第3节

#### 发病机制
正文内容...
出处页码: P220-225
出处章节: 第8章 第1节
```

### JSON格式示例

```json
{
  "textbook": {
    "title": "内科学",
    "author": "葛均波",
    "edition": "第九版",
    "publisher": "人民卫生出版社",
    "year": 2018,
    "level": "undergraduate"
  },
  "diseases": [
    {
      "name": "冠心病",
      "name_en": "Coronary Heart Disease",
      "system_name": "心血管系统",
      "level": "undergraduate",
      "overview": "冠状动脉粥样硬化导致...",
      "symptoms": [
        {"name": "胸痛", "relevance": "main"},
        {"name": "呼吸困难", "relevance": "common"}
      ],
      "infos": [
        {
          "info_type": "definition",
          "content": "正文内容...",
          "page_ref": "P234-240",
          "chapter_ref": "第8章 第3节"
        }
      ]
    }
  ]
}
```

---

## 🔧 配置说明

编辑 `config.py` 可调整以下配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_FILE` | `medical.db` | 数据库文件路径 |
| `HOST` | `127.0.0.1` | 监听地址 |
| `PORT` | `5000` | 监听端口 |
| `DEBUG` | `True` | 调试模式 |
| `UPDATE_INTERVAL_HOURS` | `24` | 自动更新检查间隔（小时） |
| `AUTO_IMPORT` | `True` | 启动时是否自动导入新数据 |

---

## 📊 数据库表说明

| 表名 | 作用 | 核心字段 |
|------|------|----------|
| `textbooks` | 教材元信息 | title, author, edition, level |
| `body_systems` | 人体系统分类 | name, name_en, icon |
| `diseases` | 疾病基本信息 | name, system_id, level, overview |
| `disease_infos` | 疾病详细信息（核心） | disease_id, info_type, content, textbook_id, page_ref |
| `symptoms` | 症状词汇库 | name, name_en, category |
| `disease_symptoms` | 疾病-症状关联 | disease_id, symptom_id, relevance |

---

## 🔄 数据更新机制

1. **手动导入**：管理后台 → 批量导入，或命令行执行导入
2. **自动检测**：`updater.py` 每24小时扫描 `data/` 目录
3. **增量更新**：已存在的内容不会被重复导入，新内容自动追加
4. **导入日志**：所有操作记录在 `data/import_log.md`

---

## 📋 API接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/search?q=胸痛` | 症状搜索 |
| GET | `/api/symptoms` | 症状列表 |
| GET | `/api/symptoms/search?q=胸` | 症状模糊搜索（自动补全） |
| GET | `/api/systems` | 人体系统列表 |
| GET | `/api/systems/:id/diseases` | 系统下的疾病 |
| GET | `/api/diseases/:id` | 疾病详情（含完整信息） |
| GET/POST | `/api/textbooks` | 教材列表/新增 |
| GET/POST | `/api/diseases` | 疾病列表/新增 |
| GET/POST | `/api/disease-infos` | 信息条目列表/新增 |
| GET/POST | `/api/symptoms/manage` | 症状列表/新增 |
| POST | `/api/import` | 触发数据导入 |
| GET | `/api/stats` | 统计数据 |

---

## ⚠️ 注意事项

- 本系统内容仅供**学习参考**，具体诊疗请以临床指南为准
- 教材内容版权归原作者及出版社所有，请**仅用于个人学习**
- 数据存储在本地SQLite文件，建议**定期备份** `medical.db`
- 首次使用建议先导入 `data/sample/` 中的示例数据体验功能

---

## 🛣️ 后续扩展建议

- [ ] 添加用户登录和个人笔记功能
- [ ] 集成jieba分词提升中文搜索精度
- [ ] 支持PDF教材内容自动提取
- [ ] 添加学习进度追踪和间隔复习提醒（Anki-like）
- [ ] 支持图片和表格内容展示
- [ ] 移动端PWA适配
- [ ] 添加内容导出（PDF/打印笔记）
