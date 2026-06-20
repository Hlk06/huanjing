# ============================================
# data_importer.py — 教材内容批量导入工具
# 作用:
#   1. 扫描data/目录下的Markdown/JSON文件
#   2. 按约定格式解析医学教材内容
#   3. 自动写入数据库（教材→疾病→症状→详细信息）
#   4. 记录导入日志，支持增量更新（跳过已存在的内容）
#
# Markdown导入格式约定:
#   每个文件以 ## 开头定义教材信息
#   以 ### 开头定义疾病
#   以 #### 开头定义信息类型
#   正文为markdown普通段落
#   症状在疾病段落的"关联症状:"行指定
# ============================================

import os
import re
import json
from datetime import datetime
from config import DATA_DIR, IMPORT_LOG


class DataImporter:
    """教材内容导入器，支持Markdown和JSON格式"""

    def __init__(self, data_dir=None):
        """初始化导入器
        Args:
            data_dir: 数据源目录路径，默认为config中的DATA_DIR
        """
        self.data_dir = data_dir or DATA_DIR
        self.import_log_path = IMPORT_LOG
        self.stats = {
            'textbooks_added': 0,
            'diseases_added': 0,
            'disease_infos_added': 0,
            'symptoms_added': 0,
            'files_processed': 0,
            'errors': [],
        }

    # ============================================
    # import_from_data_dir() — 从数据目录批量导入
    # 作用: 扫描data/目录，导入所有支持的格式文件
    # 返回: 导入统计信息字典
    # ============================================
    def import_from_data_dir(self):
        """扫描数据目录并导入所有支持的文件"""
        # 延迟导入，避免在模块加载时依赖app context
        from models import db
        from models import Textbook, BodySystem, Disease, DiseaseInfo, Symptom, DiseaseSymptom

        self.stats = {
            'textbooks_added': 0,
            'diseases_added': 0,
            'disease_infos_added': 0,
            'symptoms_added': 0,
            'files_processed': 0,
            'errors': [],
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            self._log(f'创建数据目录: {self.data_dir}')
            return self.stats

        # 递归遍历数据目录中的所有文件
        for root, dirs, files in os.walk(self.data_dir):
            for filename in files:
                # 跳过导入日志文件
                if filename == 'import_log.md':
                    continue
                filepath = os.path.join(root, filename)
                relpath = os.path.relpath(filepath, self.data_dir)

                try:
                    if filename.endswith('.md'):
                        self._import_markdown(filepath)
                    elif filename.endswith('.json'):
                        self._import_json(filepath)
                    else:
                        continue
                    self.stats['files_processed'] += 1
                except Exception as e:
                    error_msg = f'导入文件 {relpath} 失败: {str(e)}'
                    self.stats['errors'].append(error_msg)
                    self._log(f'[ERROR] {error_msg}')

        self.stats['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._log_import_summary()
        return self.stats

    # ============================================
    # _import_markdown() — 导入Markdown格式文件
    # 作用: 解析约定格式的Markdown文件并写入数据库
    #
    # 格式示例:
    #   ## 教材: 内科学
    #   作者: 葛均波
    #   版次: 第九版
    #   出版社: 人民卫生出版社
    #   年份: 2018
    #   层次: undergraduate
    #
    #   ### 疾病: 冠心病
    #   英文名: Coronary Heart Disease
    #   系统: 心血管系统
    #   层次: undergraduate
    #   关联症状: 胸痛(main), 呼吸困难(common), 心悸(common)
    #   概述: 冠状动脉粥样硬化导致...
    #
    #   #### 定义
    #   正文内容...
    #   出处页码: P234-240
    #   出处章节: 第8章 第3节
    #
    #   #### 发病机制
    #   正文内容...
    # ============================================
    def _import_markdown(self, filepath):
        """导入单个Markdown文件"""
        from models import Textbook, BodySystem, Disease, DiseaseInfo, Symptom, DiseaseSymptom
        from models import db

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析教材信息
        textbook = None
        textbook_match = re.search(r'##\s*教材[:：]\s*(.+)', content)
        if textbook_match:
            textbook_title = textbook_match.group(1).strip()
            author_match = re.search(r'作者[:：]\s*(.+)', content)
            edition_match = re.search(r'版次[:：]\s*(.+)', content)
            publisher_match = re.search(r'出版社[:：]\s*(.+)', content)
            year_match = re.search(r'年份[:：]\s*(\d+)', content)
            level_match = re.search(r'层次[:：]\s*(.+)', content)

            level = 'undergraduate'
            if level_match:
                level_text = level_match.group(1).strip().lower()
                if level_text == 'graduate' or '研究生' in level_text:
                    level = 'graduate'

            # 检查教材是否已存在
            existing = Textbook.query.filter_by(title=textbook_title, level=level).first()
            if not existing:
                textbook = Textbook(
                    title=textbook_title,
                    author=author_match.group(1).strip() if author_match else None,
                    edition=edition_match.group(1).strip() if edition_match else None,
                    publisher=publisher_match.group(1).strip() if publisher_match else None,
                    year=int(year_match.group(1)) if year_match else None,
                    level=level,
                )
                db.session.add(textbook)
                db.session.commit()
                self.stats['textbooks_added'] += 1
                self._log(f'新增教材: {textbook_title}')
            else:
                textbook = existing
        else:
            raise ValueError('文件中未找到教材信息（需要以 ## 教材: 开头）')

        # 解析疾病信息
        disease_blocks = re.split(r'\n###\s+疾病[:：]', content)
        for block in disease_blocks[1:]:  # 跳过第一个（教材信息部分）
            self._parse_disease_block(block, textbook)

        db.session.commit()

    # ============================================
    # _parse_disease_block() — 解析单个疾病块
    # ============================================
    def _parse_disease_block(self, block, textbook):
        """解析Markdown中的单个疾病块"""
        from models import Disease, DiseaseInfo, Symptom, DiseaseSymptom, BodySystem
        from models import db

        lines = block.strip().split('\n')
        if not lines:
            return

        # 解析疾病基本信息
        disease_name = lines[0].strip()
        disease_data = {
            'name': disease_name,
            'level': textbook.level,
        }

        for line in lines[1:]:
            if line.startswith('####'):
                break  # 遇到第一个信息类型标题，退出元信息解析

            if '英文名:' in line or '英文名：' in line:
                disease_data['name_en'] = line.split(':', 1)[-1].split('：', 1)[-1].strip()
            elif '系统:' in line or '系统：' in line:
                system_name = line.split(':', 1)[-1].split('：', 1)[-1].strip()
                system = BodySystem.query.filter_by(name=system_name).first()
                if system:
                    disease_data['system_id'] = system.id
            elif '层次:' in line or '层次：' in line:
                level_text = line.split(':', 1)[-1].split('：', 1)[-1].strip().lower()
                if level_text == 'graduate' or '研究生' in level_text:
                    disease_data['level'] = 'graduate'
            elif '概述:' in line or '概述：' in line:
                disease_data['overview'] = line.split(':', 1)[-1].split('：', 1)[-1].strip()
            elif '关联症状:' in line or '关联症状：' in line:
                disease_data['_symptoms'] = self._parse_symptom_list(
                    line.split(':', 1)[-1].split('：', 1)[-1].strip())

        # 创建或获取疾病记录
        existing = Disease.query.filter_by(
            name=disease_data['name'],
            system_id=disease_data.get('system_id')
        ).first()

        if not existing:
            symptoms_data = disease_data.pop('_symptoms', [])
            if 'system_id' not in disease_data:
                self._log(f'[WARNING] 疾病"{disease_data["name"]}"缺少系统归属，跳过')
                return
            disease = Disease(**{k: v for k, v in disease_data.items() if not k.startswith('_')})
            db.session.add(disease)
            db.session.flush()  # 获取ID

            # 创建症状关联
            for s in symptoms_data:
                self._link_symptom(disease, s['name'], s.get('relevance', 'common'))
            self.stats['diseases_added'] += 1
        else:
            disease = existing
            symptoms_data = disease_data.get('_symptoms', [])
            if symptoms_data:
                for s in symptoms_data:
                    self._link_symptom(disease, s['name'], s.get('relevance', 'common'))

        # 解析详细信息块（定义、发病机制等）
        info_blocks = re.split(r'\n####\s+', block)
        for info_block in info_blocks[1:]:  # 跳过疾病元信息部分
            self._parse_info_block(info_block.strip(), disease, textbook)

    # ============================================
    # _parse_symptom_list() — 解析症状列表字符串
    # 格式: "胸痛(main), 呼吸困难(common), 心悸"
    # ============================================
    def _parse_symptom_list(self, text):
        """解析症状列表，返回 [{'name': '胸痛', 'relevance': 'main'}, ...]"""
        symptoms = []
        # 按逗号分隔
        parts = re.split(r'[,，、]', text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 提取症状名和关联度
            match = re.match(r'(.+?)\((main|common|rare)\)', part)
            if match:
                symptoms.append({
                    'name': match.group(1).strip(),
                    'relevance': match.group(2),
                })
            else:
                symptoms.append({
                    'name': part.strip(),
                    'relevance': 'common',
                })
        return symptoms

    # ============================================
    # _link_symptom() — 创建疾病与症状的关联
    # ============================================
    def _link_symptom(self, disease, symptom_name, relevance='common'):
        """创建或更新疾病-症状关联"""
        from models import Symptom, DiseaseSymptom
        from models import db

        # 查找或创建症状
        symptom = Symptom.query.filter_by(name=symptom_name).first()
        if not symptom:
            symptom = Symptom(name=symptom_name)
            db.session.add(symptom)
            db.session.flush()
            self.stats['symptoms_added'] += 1

        # 创建关联（检查是否已存在）
        existing_link = DiseaseSymptom.query.filter_by(
            disease_id=disease.id,
            symptom_id=symptom.id
        ).first()
        if not existing_link:
            link = DiseaseSymptom(
                disease_id=disease.id,
                symptom_id=symptom.id,
                relevance=relevance,
            )
            db.session.add(link)

    # ============================================
    # _parse_info_block() — 解析疾病详细信息块
    # ============================================
    def _parse_info_block(self, block, disease, textbook):
        """解析Markdown中的单个信息类型块"""
        from models import DiseaseInfo
        from models import db

        lines = block.strip().split('\n')
        if not lines:
            return

        # 第一行是信息类型标题
        info_type_name = lines[0].strip()

        # 映射中文标题到info_type枚举值（支持带括号的标题，如"解剖学基础（心脏发育与畸形位置）"）
        type_mapping = {
            '定义': 'definition',
            '定义与发病机制': 'definition',
            '发病机制': 'pathogenesis',
            '预防原则': 'prevention',
            '治疗方案': 'treatment',
            '治疗原则': 'treatment',
            '治疗与预防': 'treatment',
            '预防与治疗': 'treatment',
            '治疗': 'treatment',
            '诊断与治疗': 'clinical_diagnosis',
            '发病机制与诊断': 'pathogenesis',
            '定义与分型': 'definition',
            '定义与分类': 'definition',
            '定义与分期': 'definition',
            '定义与筛查': 'definition',
            '临床与诊断': 'clinical_diagnosis',
            '分型与诊断': 'clinical_diagnosis',
            '诊断与心肺复苏': 'clinical_diagnosis',
            '预防与预后': 'prevention',
            '定义与诊断': 'definition',
            '慢性胃炎': 'pathology',
            '发病机制与治疗': 'pathogenesis',
            '临床与诊断': 'clinical_diagnosis',
            '临床表现与诊断': 'clinical_diagnosis',
            '并发症与治疗': 'treatment',
            '分期与治疗': 'staging',
            '治疗与预后': 'treatment',
            '预防': 'prevention',
            '鉴别诊断': 'differential_diagnosis',
            '鉴别、预后与预防': 'differential_diagnosis',
            '鉴别诊断与预后': 'differential_diagnosis',
            '解剖学基础': 'anatomy',
            '生理学基础': 'physiology',
            '生物化学基础': 'biochemistry',
            '病理学改变': 'pathology',
            '病理生理学改变': 'pathophysiology',
            '临床表现与诊断依据': 'clinical_diagnosis',
            '临床表现与诊断': 'clinical_diagnosis',
            '临床表现': 'clinical_manifestation',
            '检查方式': 'examination',
            '疾病分级分期': 'staging',
            '预后': 'prognosis',
            # Additional Chinese types
            '发病机制与分期': 'pathogenesis',
            '分类与治疗': 'treatment',
            '诊断与筛查': 'clinical_diagnosis',
            '定义与鉴别': 'definition',
            '定义与病因': 'definition',
            '诊断': 'clinical_diagnosis',
            '脊髓压迫症': 'pathogenesis',
            '诊断与治疗': 'clinical_diagnosis',
            '定义与诊断': 'definition',
            '诊断与治疗': 'clinical_diagnosis',
            '发病机制与诊断': 'pathogenesis',
            '分期与治疗': 'staging',
            '治疗与预后': 'treatment',
            '鉴别诊断与预后': 'differential_diagnosis',
            # 卫生法专用类型
            '医疗机构管理法律制度': 'treatment',
            '执业医师法律制度': 'treatment',
            '药品管理法律制度': 'treatment',
            '传染病防治法律制度': 'prevention',
            '医疗事故处理法律制度': 'differential_diagnosis',
            '食品安全法律制度': 'prevention',
            # English
            'Definition': 'definition',
            'Pathogenesis': 'pathogenesis',
            'Prevention': 'prevention',
            'Treatment': 'treatment',
            'Differential Diagnosis': 'differential_diagnosis',
            'Anatomy': 'anatomy',
            'Physiology': 'physiology',
            'Biochemistry': 'biochemistry',
            'Pathology': 'pathology',
            'Prognosis': 'prognosis',
        }
        # Try exact match first, then try stripping parenthetical subheading
        info_type = type_mapping.get(info_type_name)
        if not info_type:
            # Strip parenthetical subheadings like "解剖学基础（心脏发育与畸形位置）" → "解剖学基础"
            import re
            base = re.sub(r'[（(][^)）]*[)）]', '', info_type_name).strip()
            info_type = type_mapping.get(base)
        if not info_type:
            self._log(f'[WARNING] 未知的信息类型: {info_type_name}，跳过')
            return

        # 解析正文内容和引用信息
        content_lines = []
        page_ref = None
        chapter_ref = None

        for line in lines[1:]:
            line_stripped = line.strip()
            if '出处页码:' in line_stripped or '出处页码：' in line_stripped or '页码:' in line_stripped:
                page_ref = line_stripped.split(':', 1)[-1].split('：', 1)[-1].strip()
            elif '出处章节:' in line_stripped or '出处章节：' in line_stripped or '章节:' in line_stripped:
                chapter_ref = line_stripped.split(':', 1)[-1].split('：', 1)[-1].strip()
            else:
                content_lines.append(line)

        content = '\n'.join(content_lines).strip()
        if not content:
            return

        # 检查是否已存在相同内容（避免重复导入）
        existing = DiseaseInfo.query.filter_by(
            disease_id=disease.id,
            info_type=info_type,
            textbook_id=textbook.id,
        ).first()

        if not existing:
            info = DiseaseInfo(
                disease_id=disease.id,
                info_type=info_type,
                content=content,
                textbook_id=textbook.id,
                page_ref=page_ref,
                chapter_ref=chapter_ref,
            )
            db.session.add(info)
            self.stats['disease_infos_added'] += 1
        else:
            # 更新已有内容
            existing.content = content
            existing.page_ref = page_ref or existing.page_ref
            existing.chapter_ref = chapter_ref or existing.chapter_ref

    # ============================================
    # _import_json() — 导入JSON格式文件
    # 作用: 支持结构化JSON数据的批量导入
    # JSON格式:
    #   {
    #     "textbook": { ... },
    #     "diseases": [
    #       { "name": "...", "symptoms": [...], "infos": [...] }
    #     ]
    #   }
    # ============================================
    def _import_json(self, filepath):
        """导入JSON格式的数据文件"""
        from models import Textbook, BodySystem, Disease, DiseaseInfo, Symptom, DiseaseSymptom
        from models import db

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 解析教材
        tb_data = data.get('textbook', {})
        textbook = None
        if tb_data:
            existing = Textbook.query.filter_by(
                title=tb_data.get('title'),
                level=tb_data.get('level', 'undergraduate')
            ).first()
            if not existing:
                textbook = Textbook(
                    title=tb_data.get('title'),
                    author=tb_data.get('author'),
                    edition=tb_data.get('edition'),
                    publisher=tb_data.get('publisher'),
                    year=tb_data.get('year'),
                    level=tb_data.get('level', 'undergraduate'),
                    isbn=tb_data.get('isbn'),
                )
                db.session.add(textbook)
                db.session.flush()
                self.stats['textbooks_added'] += 1
            else:
                textbook = existing

        if not textbook:
            raise ValueError('JSON文件中未找到教材信息')

        # 解析疾病
        for disease_entry in data.get('diseases', []):
            # 查找系统
            system = BodySystem.query.filter_by(
                name=disease_entry.get('system_name', '')
            ).first()
            if not system:
                self._log(f'[WARNING] 系统"{disease_entry.get("system_name")}"不存在，跳过疾病"{disease_entry.get("name")}"')
                continue

            # 创建疾病
            existing_disease = Disease.query.filter_by(
                name=disease_entry['name'],
                system_id=system.id,
            ).first()
            if not existing_disease:
                disease = Disease(
                    name=disease_entry['name'],
                    name_en=disease_entry.get('name_en'),
                    system_id=system.id,
                    level=disease_entry.get('level', textbook.level),
                    overview=disease_entry.get('overview'),
                )
                db.session.add(disease)
                db.session.flush()
                self.stats['diseases_added'] += 1

                # 关联症状
                for s in disease_entry.get('symptoms', []):
                    self._link_symptom(disease, s['name'], s.get('relevance', 'common'))
            else:
                disease = existing_disease

            # 导入详细信息
            for info_entry in disease_entry.get('infos', []):
                existing_info = DiseaseInfo.query.filter_by(
                    disease_id=disease.id,
                    info_type=info_entry['info_type'],
                    textbook_id=textbook.id,
                ).first()
                if not existing_info:
                    info = DiseaseInfo(
                        disease_id=disease.id,
                        info_type=info_entry['info_type'],
                        content=info_entry['content'],
                        textbook_id=textbook.id,
                        page_ref=info_entry.get('page_ref'),
                        chapter_ref=info_entry.get('chapter_ref'),
                    )
                    db.session.add(info)
                    self.stats['disease_infos_added'] += 1

        db.session.commit()

    # ============================================
    # _log() — 写入导入日志
    # ============================================
    def _log(self, message):
        """记录导入日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f'[{timestamp}] {message}\n'

        # 确保日志目录存在
        log_dir = os.path.dirname(self.import_log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        with open(self.import_log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        # 安全打印（避免终端编码问题）
        try:
            print(log_entry.strip())
        except UnicodeEncodeError:
            print(log_entry.encode('ascii', errors='replace').decode('ascii').strip())

    # ============================================
    # _log_import_summary() — 写入导入汇总
    # ============================================
    def _log_import_summary(self):
        """记录本次导入的汇总统计"""
        summary = f'''
{'=' * 50}
导入汇总 - {self.stats['start_time']}
处理文件数: {self.stats['files_processed']}
新增教材: {self.stats['textbooks_added']}
新增疾病: {self.stats['diseases_added']}
新增信息条目: {self.stats['disease_infos_added']}
新增症状: {self.stats['symptoms_added']}
错误数: {len(self.stats['errors'])}
{'=' * 50}
'''
        self._log(summary)
