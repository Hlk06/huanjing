# ============================================
# models.py — 数据库模型定义
# 作用: 使用SQLAlchemy ORM定义所有数据库表结构
# 每个类对应一张数据库表，属性对应字段
# 通过ORM操作数据库，避免手写SQL，减少注入风险
# ============================================

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# db: SQLAlchemy实例，由app.py在创建Flask应用时初始化
# 此处创建对象，稍后在app.py中调用 db.init_app(app) 完成绑定
db = SQLAlchemy()


# ============================================
# Textbook — 教材信息表
# 作用: 存储所有收录教材的元信息（书名、作者、版次等）
# 每本教材属于本科或研究生两个板块之一
# ============================================
class Textbook(db.Model):
    __tablename__ = 'textbooks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)       # 书名，如《内科学》
    author = db.Column(db.String(100))                       # 作者/主编
    edition = db.Column(db.String(50))                       # 版次，如"第九版"
    publisher = db.Column(db.String(100))                    # 出版社
    year = db.Column(db.Integer)                             # 出版年份
    level = db.Column(db.String(20), nullable=False)         # 板块: undergraduate(本科) | graduate(研究生)
    isbn = db.Column(db.String(20))                          # ISBN号
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联: 一本教材下有多条疾病信息记录
    # backref='textbook' 使得在DiseaseInfo对象上可通过 .textbook 访问所属教材
    disease_infos = db.relationship('DiseaseInfo', backref='textbook', lazy='dynamic')

    def to_dict(self):
        """将教材对象序列化为字典，供API返回JSON使用"""
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'edition': self.edition,
            'publisher': self.publisher,
            'year': self.year,
            'level': self.level,
            'isbn': self.isbn,
        }

    def citation(self):
        """生成完整的引用字符串，如: 《内科学》第九版，人民卫生出版社"""
        parts = [f'《{self.title}》']
        if self.edition:
            parts.append(self.edition)
        if self.publisher:
            parts.append(self.publisher)
        return '，'.join(parts)


# ============================================
# BodySystem — 人体系统表
# 作用: 存储12个人体系统分类，所有疾病按系统组织
# 预置数据在app初始化时自动插入
# ============================================
class BodySystem(db.Model):
    __tablename__ = 'body_systems'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # 系统中文名
    name_en = db.Column(db.String(100))                            # 系统英文名
    description = db.Column(db.Text)                               # 系统简介
    icon = db.Column(db.String(50))                                # 图标emoji
    sort_order = db.Column(db.Integer, default=0)                  # 排序权重（数字越小越靠前）

    # 关联: 一个系统下有多个疾病
    diseases = db.relationship('Disease', backref='system', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
            'description': self.description,
            'icon': self.icon,
            'sort_order': self.sort_order,
        }


# ============================================
# Disease — 疾病表
# 作用: 存储所有疾病信息，关联到所属人体系统
# 通过level字段区分本科/研究生难度
# ============================================
class Disease(db.Model):
    __tablename__ = 'diseases'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)            # 疾病中文名
    name_en = db.Column(db.String(200))                          # 疾病英文名
    system_id = db.Column(db.Integer, db.ForeignKey('body_systems.id'), nullable=False)
    level = db.Column(db.String(20), default='undergraduate')    # 本科/研究生
    overview = db.Column(db.Text)                                # 疾病概述/摘要

    # 关联: 一个疾病有多条详细信息条目（定义、机制等）
    disease_infos = db.relationship('DiseaseInfo', backref='disease', lazy='dynamic',
                                    cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
            'system_id': self.system_id,
            'system_name': self.system.name if self.system else None,
            'level': self.level,
            'overview': self.overview,
        }

    def get_symptoms(self):
        """获取该疾病的所有关联症状名称列表（用于搜索和展示）"""
        # DiseaseSymptom关联表中查找，返回症状名列表
        links = DiseaseSymptom.query.filter_by(disease_id=self.id).all()
        result = []
        for link in links:
            symptom = Symptom.query.get(link.symptom_id)
            if symptom:
                result.append({
                    'name': symptom.name,
                    'name_en': symptom.name_en,
                    'relevance': link.relevance,
                })
        return result

    def get_main_symptoms(self):
        """仅获取主要症状（relevance='main'）"""
        return [s for s in self.get_symptoms() if s['relevance'] == 'main']


# ============================================
# DiseaseInfo — 疾病详细信息表（核心表）
# 作用: 存储疾病的各类详细信息（定义、机制、预防、治疗、鉴别）
# 每条信息必须关联到一个教材来源，确保内容可追溯
# is_verbatim: True=原文照录 False=人工整理
# page_id: 精确到页面的引用
# ============================================
class DiseaseInfo(db.Model):
    __tablename__ = 'disease_infos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), nullable=False)
    info_type = db.Column(db.String(30), nullable=False)          # 信息类型
    content = db.Column(db.Text, nullable=False)                  # 正文内容
    textbook_id = db.Column(db.Integer, db.ForeignKey('textbooks.id'), nullable=False)
    page_ref = db.Column(db.String(50))                           # 页码，如"P234-240"
    chapter_ref = db.Column(db.String(100))                       # 章节，如"第8章 第3节"
    page_id = db.Column(db.Integer, db.ForeignKey('textbook_pages.id'))  # 精确到页
    is_verbatim = db.Column(db.Boolean, default=True)             # 是否原文照录

    def to_dict(self):
        result = {
            'id': self.id,
            'disease_id': self.disease_id,
            'info_type': self.info_type,
            'content': self.content,
            'textbook_id': self.textbook_id,
            'page_ref': self.page_ref,
            'chapter_ref': self.chapter_ref,
            'page_id': self.page_id,
            'is_verbatim': self.is_verbatim,
        }
        if self.textbook:
            result['citation'] = self.get_citation()
        if self.page:
            result['page_number'] = self.page.page_number
        return result

    def get_citation(self):
        """生成完整引用字符串，格式: 《内科学》第九版，人民卫生出版社，第8章 第3节，P234-240"""
        if not self.textbook:
            return '来源未知'
        parts = [self.textbook.citation()]
        if self.chapter_ref:
            parts.append(self.chapter_ref)
        if self.page_ref:
            parts.append(self.page_ref)
        return '，'.join(parts)

    # 关联: 精确到页
    page = db.relationship('TextbookPage', backref='disease_infos')


# ============================================
# TextbookPage — 教材原文逐页存储表（新增核心表）
# 作用: 存储每本教材每一页的完整原始文本，一字不改
# 这是"原文不修改"机制的核心保障
# ============================================
class TextbookPage(db.Model):
    __tablename__ = 'textbook_pages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    textbook_id = db.Column(db.Integer, db.ForeignKey('textbooks.id'), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)          # PDF内部页码
    raw_text = db.Column(db.Text, nullable=False)                # 该页完整原文（逐页存储，不修改）
    char_count = db.Column(db.Integer)                            # 字符数
    __table_args__ = (db.UniqueConstraint('textbook_id', 'page_number'),)

    textbook = db.relationship('Textbook', backref='pages')

    def to_dict(self):
        return {
            'id': self.id,
            'textbook_id': self.textbook_id,
            'page_number': self.page_number,
            'raw_text': self.raw_text,
            'char_count': self.char_count,
        }

    def get_citation(self):
        """获取精确引用"""
        if self.textbook:
            return f'{self.textbook.citation()}，第{self.page_number}页'
        return f'第{self.page_number}页'


# ============================================
# TextbookChapter — 教材章节结构表（新增）
# 作用: 记录教材的章节结构，用于导航和系统映射
# ============================================
class TextbookChapter(db.Model):
    __tablename__ = 'textbook_chapters'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    textbook_id = db.Column(db.Integer, db.ForeignKey('textbooks.id'), nullable=False)
    chapter_title = db.Column(db.String(300), nullable=False)     # 如"第四章 冠心病"
    level = db.Column(db.Integer, default=1)                      # 层级: 1=章 2=节
    parent_id = db.Column(db.Integer, db.ForeignKey('textbook_chapters.id'))
    start_page = db.Column(db.Integer)                            # 起始页码
    end_page = db.Column(db.Integer)                              # 结束页码
    body_system_id = db.Column(db.Integer, db.ForeignKey('body_systems.id'))

    textbook = db.relationship('Textbook', backref='chapters')
    body_system = db.relationship('BodySystem', backref='chapters')

    def to_dict(self):
        return {
            'id': self.id,
            'textbook_id': self.textbook_id,
            'chapter_title': self.chapter_title,
            'level': self.level,
            'parent_id': self.parent_id,
            'start_page': self.start_page,
            'end_page': self.end_page,
            'body_system_id': self.body_system_id,
            'body_system_name': self.body_system.name if self.body_system else None,
        }


# ============================================
# KnowledgeRef — 知识点精确引用表（新增）
# 作用: 记录每个知识点在原文中的精确位置
# 包含char_start/char_end用于页面内精确定位
# ============================================
class KnowledgeRef(db.Model):
    __tablename__ = 'knowledge_refs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), nullable=False)
    page_id = db.Column(db.Integer, db.ForeignKey('textbook_pages.id'), nullable=False)
    info_type = db.Column(db.String(30), nullable=False)
    context_snippet = db.Column(db.Text)                          # 该知识点在页中的原文片段
    char_start = db.Column(db.Integer)                            # 在raw_text中的起始位置
    char_end = db.Column(db.Integer)                              # 在raw_text中的结束位置

    disease = db.relationship('Disease', backref='knowledge_refs')
    page = db.relationship('TextbookPage', backref='knowledge_refs')

    def to_dict(self):
        return {
            'id': self.id,
            'disease_id': self.disease_id,
            'page_id': self.page_id,
            'info_type': self.info_type,
            'context_snippet': self.context_snippet,
            'char_start': self.char_start,
            'char_end': self.char_end,
            'page_number': self.page.page_number if self.page else None,
            'textbook_title': self.page.textbook.title if self.page and self.page.textbook else None,
        }


# ============================================
# Symptom — 症状表
# 作用: 存储所有临床症���词汇，作为搜索的入口
# 通过disease_symptoms关联表与疾病建立多对多关系
# ============================================
class Symptom(db.Model):
    __tablename__ = 'symptoms'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # 症状名，如"胸痛"
    name_en = db.Column(db.String(100))                            # 英文名
    category = db.Column(db.String(50))                            # 症状分类

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_en': self.name_en,
            'category': self.category,
        }


# ============================================
# DiseaseSymptom — 疾病-症状关联表（多对多中间表）
# 作用: 建立疾病与症状的多对多关系，并记录关联强度
# relevance字段表示该症状在疾病中的重要性
# ============================================
class DiseaseSymptom(db.Model):
    __tablename__ = 'disease_symptoms'

    disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), primary_key=True)
    symptom_id = db.Column(db.Integer, db.ForeignKey('symptoms.id'), primary_key=True)
    relevance = db.Column(db.String(20), default='common')  # main | common | rare

    disease = db.relationship('Disease', backref='symptom_links')
    symptom = db.relationship('Symptom', backref='disease_links')
