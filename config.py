# ============================================
# config.py — 应用配置文件
# 作用: 集中管理所有配置常量（数据库路径、应用密钥、定时任务间隔等）
# 修改此处即可调整整个应用的行为，无需改动业务代码
# ============================================

import os

# --- 基础路径配置 ---
# BASE_DIR: 项目根目录（当前文件所在目录）
# 所有其他路径都基于此计算，确保应用可在任意位置运行
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# --- Flask核心配置 ---
# SECRET_KEY: Flask会话加密密钥，生产环境应改为随机字符串
SECRET_KEY = os.environ.get('SECRET_KEY', 'medical-study-app-secret-key-2024')

# --- 数据库配置 ---
# DATABASE_FILE: SQLite数据库文件名，存储在项目根目录
DATABASE_FILE = os.path.join(BASE_DIR, 'medical.db')
# SQLALCHEMY_DATABASE_URI: SQLAlchemy连接字符串
# 优先使用环境变量 DATABASE_URL（用于云平台），未设置则回退到本地 sqlite 文件
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{DATABASE_FILE}')
# SQLALCHEMY_TRACK_MODIFICATIONS: 关闭追踪以节省内存
SQLALCHEMY_TRACK_MODIFICATIONS = False

# --- 数据目录配置 ---
# DATA_DIR: 教材数据文件存放目录，data_importer.py扫描此目录
DATA_DIR = os.path.join(BASE_DIR, 'data')
# IMPORT_LOG: 导入操作日志文件路径
IMPORT_LOG = os.path.join(DATA_DIR, 'import_log.md')

# --- 定时更新配置 ---
# UPDATE_INTERVAL_HOURS: 自动检查数据更新的间隔（小时）
# 默认24小时检查一次，可根据需要调整
UPDATE_INTERVAL_HOURS = 24
# AUTO_IMPORT: 是否启用启动时自动导入data/目录中的新文件
AUTO_IMPORT = True

# --- 应用运行配置 ---
# HOST: 0.0.0.0 允许局域网内任意设备(手机/平板)访问
HOST = '0.0.0.0'
# PORT: 监听端口
PORT = 5000
# DEBUG: 调试模式开关（开发时True，生产时False）
DEBUG = True

# --- 预定义常量 ---
# LEVEL_OPTIONS: 学历层次选项
LEVEL_OPTIONS = {
    'undergraduate': {'label': '本科', 'icon': '🎓', 'color': 'primary'},
    'graduate': {'label': '研究生', 'icon': '🔬', 'color': 'purple'},
}

# INFO_TYPE_OPTIONS: 疾病信息类型（对应disease_infos表的info_type字段）
INFO_TYPE_OPTIONS = {
    'definition': {'label': '定义', 'icon': '📖', 'order': 1},
    'anatomy': {'label': '解剖学基础', 'icon': '🦴', 'order': 2},
    'physiology': {'label': '生理学基础', 'icon': '⚡', 'order': 3},
    'biochemistry': {'label': '生物化学基础', 'icon': '🧪', 'order': 4},
    'pathology': {'label': '病理学改变', 'icon': '🔬', 'order': 5},
    'pathophysiology': {'label': '病理生理学机制', 'icon': '🧬', 'order': 6},
    'pathogenesis': {'label': '发病机制', 'icon': '🔄', 'order': 7},
    'clinical_manifestation': {'label': '临床表现', 'icon': '🩺', 'order': 8},
    'clinical_diagnosis': {'label': '临床表现与诊断依据', 'icon': '📋', 'order': 9},
    'examination': {'label': '检查方式', 'icon': '🔍', 'order': 10},
    'differential_diagnosis': {'label': '鉴别诊断', 'icon': '⚖️', 'order': 11},
    'staging': {'label': '疾病分级分期', 'icon': '📊', 'order': 12},
    'prevention': {'label': '预防原则', 'icon': '🛡️', 'order': 13},
    'treatment': {'label': '治疗方案', 'icon': '💊', 'order': 14},
    'prognosis': {'label': '预后', 'icon': '📈', 'order': 15},
}

# BODY_SYSTEMS_PRESET: 9大系统预置数据
# 应用首次启动时自动插入数据库
BODY_SYSTEMS_PRESET = [
    {'name': '循环系统', 'name_en': 'Circulatory System', 'icon': '❤️', 'sort_order': 1,
     'description': '包括心脏、血管、血液和淋巴循环相关疾病'},
    {'name': '呼吸系统', 'name_en': 'Respiratory System', 'icon': '🫁', 'sort_order': 2,
     'description': '包括鼻、咽、喉、气管、支气管、肺和胸膜相关疾病'},
    {'name': '消化系统', 'name_en': 'Digestive System', 'icon': '🔬', 'sort_order': 3,
     'description': '包括口腔、食管、胃、肠、肝、胆、胰及腹膜相关疾病'},
    {'name': '泌尿系统', 'name_en': 'Urinary System', 'icon': '💧', 'sort_order': 4,
     'description': '包括肾脏、输尿管、膀胱、尿道相关疾病'},
    {'name': '内分泌系统', 'name_en': 'Endocrine System', 'icon': '⚡', 'sort_order': 5,
     'description': '包括垂体、甲状腺、甲状旁腺、肾上腺、胰岛、性腺等内分泌腺及代谢性疾病'},
    {'name': '神经系统', 'name_en': 'Nervous System', 'icon': '🧠', 'sort_order': 6,
     'description': '包括中枢神经（脑、脊髓）、周围神经、神经肌肉接头及精神心理相关疾病'},
    {'name': '免疫系统', 'name_en': 'Immune System', 'icon': '🛡️', 'sort_order': 7,
     'description': '包括免疫缺陷、自身免疫病、过敏性疾病、风湿免疫病'},
    {'name': '生殖系统', 'name_en': 'Reproductive System', 'icon': '🧬', 'sort_order': 8,
     'description': '包括女性生殖（子宫、卵巢、输卵管、阴道）、男性生殖（睾丸、附睾、前列腺）及乳腺相关疾病'},
    {'name': '运动系统', 'name_en': 'Musculoskeletal System', 'icon': '🦴', 'sort_order': 9,
     'description': '包括骨骼、关节、肌肉、肌腱、韧带、脊柱及相关结缔组织疾病'},
]

# SYMPTOM_CATEGORIES: 症状分类
SYMPTOM_CATEGORIES = ['全身性症状', '局部症状', '功能性症状', '器质性症状']
