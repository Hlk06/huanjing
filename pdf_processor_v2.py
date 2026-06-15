# ============================================
# pdf_processor_v2.py — PDF逐页原文处理器（v2重写版）
# 核心原则:
#   1. 逐页提取原文，一字不改，完整存储到textbook_pages表
#   2. 检测章节/节标题→存储到textbook_chapters表
#   3. 章节→人体系统自动映射
#   4. 按章节范围检测疾病名称→建立knowledge_refs
#   5. 每条知识点精确到 教材+章+节+页码
# ============================================

import os
import re
import sys
from datetime import datetime
from pypdf import PdfReader

# 源目录和输出目录
PDF_SOURCE_DIR = r"D:\第10版资料"


class VerbatimPdfProcessor:
    """PDF逐页原文处理器 — 不修改原文，精确溯源"""

    # 章节标题检测模式（更精确的版本）
    CHAPTER_PATTERNS = [
        # 模式1: "第X章 XXX" 格式 - 最可靠
        re.compile(r'第[一二三四五六七八九十\d]{1,3}章\s*.{2,80}$', re.MULTILINE),
        # 模式2: "第X节 XXX" 格式
        re.compile(r'第[一二三四五六七八九十\d]{1,3}节\s*.{2,80}$', re.MULTILINE),
        # 模式3: "第X篇 XXX" 格式
        re.compile(r'第[一二三四五六七八九十\d]{1,3}篇\s*.{2,80}$', re.MULTILINE),
    ]

    # 章节标题→人体系统映射
    CHAPTER_SYSTEM_MAP = {
        '循环系统': '心血管系统', '心血管': '心血管系统', '心脏': '心血管系统',
        '血管': '心血管系统', '血压': '心血管系统',
        '呼吸系统': '呼吸系统', '呼吸': '呼吸系统', '肺': '呼吸系统',
        '胸膜': '呼吸系统', '气管': '呼吸系统', '支气管': '呼吸系统',
        '消化系统': '消化系统', '消化': '消化系统', '胃': '消化系统',
        '肠': '消化系统', '肝': '消化系统', '胆': '消化系统',
        '胰腺': '消化系统', '食管': '消化系统',
        '泌尿系统': '泌尿系统', '泌尿': '泌尿系统', '肾': '泌尿系统',
        '膀胱': '泌尿系统', '尿路': '泌尿系统',
        '生殖系统': '生殖系统', '生殖': '生殖系统', '子宫': '生殖系统',
        '卵巢': '生殖系统', '睾丸': '生殖系统', '妊娠': '生殖系统',
        '妇产': '生殖系统', '产科': '生殖系统', '妇科': '生殖系统',
        '神经系统': '神经系统', '神经': '神经系统', '脑': '神经系统',
        '脊髓': '神经系统', '周围神经': '神经系统',
        '内分泌': '内分泌系统', '代谢': '内分泌系统', '甲状腺': '内分泌系统',
        '肾上腺': '内分泌系统', '垂体': '内分泌系统', '糖尿病': '内分泌系统',
        '血液系统': '血液系统', '血液': '血液系统', '造血': '血液系统',
        '贫血': '血液系统', '白血病': '血液系统', '凝血': '血液系统',
        '运动系统': '运动系统', '骨': '运动系统', '关节': '运动系统',
        '肌肉': '运动系统', '骨折': '运动系统', '骨科': '运动系统',
        '免疫': '免疫系统', '风湿': '免疫系统', '自身免疫': '免疫系统',
        '过敏': '免疫系统', '免疫缺陷': '免疫系统',
        '皮肤': '皮肤系统', '性病': '皮肤系统', '皮': '皮肤系统',
        '眼': '感官系统', '耳': '感官系统', '耳鼻咽喉': '感官系统',
        '口腔': '感官系统', '鼻': '感官系统', '喉': '感官系统',
        '感染': '呼吸系统', '传染': '呼吸系统', '发热': '全身性',
        '理化因素': '中毒急救', '中毒': '中毒急救', '危重': '急危重症',
    }

    # 疾病关键词（用于在章节中检测疾病引用）
    DISEASE_KEYWORDS = [
        '病', '症', '炎', '瘤', '癌', '综合征', '衰竭', '梗死',
        '出血', '中毒', '休克', '水肿', '贫血', '肥大', '硬化',
        '狭窄', '栓塞', '感染', '绞痛', '坏死', '穿孔', '梗阻',
    ]

    def __init__(self, pdf_dir=PDF_SOURCE_DIR):
        self.pdf_dir = pdf_dir
        self.stats = {
            'pages_stored': 0,
            'chapters_found': 0,
            'knowledge_refs': 0,
            'errors': [],
            'start_time': None,
            'end_time': None,
        }

    # ============================================================
    # discover_pdfs() — 扫描PDF源目录
    # ============================================================
    def discover_pdfs(self):
        """扫描PDF源目录，返回教材文件列表"""
        if not os.path.exists(self.pdf_dir):
            return []
        pdfs = []
        for f in os.listdir(self.pdf_dir):
            if f.endswith('.pdf'):
                name = re.sub(r'\s*第\d+版\s*', '', f.replace('.pdf', '')).strip()
                name = re.sub(r'\s*目录校对版\s*', '', name).strip()
                filepath = os.path.join(self.pdf_dir, f)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                pdfs.append({'filename': f, 'name': name, 'path': filepath, 'size_mb': round(size_mb, 1)})
        return sorted(pdfs, key=lambda x: x['name'])

    # ============================================================
    # extract_all_pages() — 逐页提取全部原文（核心方法）
    # 作用: 将PDF每一页的原始文本完整提取，不做任何修改
    # 返回: list[{page_number, raw_text, char_count}, ...]
    # ============================================================
    def extract_all_pages(self, pdf_path, max_pages=None):
        """逐页提取PDF原文，一字不改"""
        reader = PdfReader(pdf_path)
        total = len(reader.pages)
        if max_pages:
            total = min(total, max_pages)

        pages = []
        for i in range(total):
            try:
                page = reader.pages[i]
                text = page.extract_text()
                if text:
                    clean_text = text.strip()
                    if clean_text:
                        pages.append({
                            'page_number': i + 1,
                            'raw_text': clean_text,  # 完整原文，不修改
                            'char_count': len(clean_text),
                        })
            except Exception as e:
                self.stats['errors'].append(f'第{i+1}页提取失败: {str(e)}')

        return pages

    # ============================================================
    # detect_chapters() — 检测章节结构
    # 作用: 在所有页面文本中扫描章节标题，构建章节树
    # 返回: list[{title, level, start_page, end_page, body_system}]
    # ============================================================
    def detect_chapters(self, pages):
        """检测教材的章节结构"""
        chapters = []

        for page_data in pages:
            text = page_data['raw_text']
            page_num = page_data['page_number']

            for pattern in self.CHAPTER_PATTERNS:
                for match in pattern.finditer(text):
                    title = match.group(0).strip()
                    # 过滤过短/过长的标题
                    if len(title) < 3 or len(title) > 150:
                        continue

                    # 判断层级
                    level = 1  # 默认章节级
                    if '节' in title and '章' not in title:
                        level = 2
                    elif '篇' in title:
                        level = 1

                    # 检测人体系统归属
                    chapter_title = title.lstrip('0123456789一二三四五六七八九十、. ')
                    body_system = self._match_system(chapter_title)

                    chapters.append({
                        'chapter_title': title,
                        'level': level,
                        'start_page': page_num,
                        'end_page': None,  # 后续填充
                        'body_system': body_system,
                    })

        # 去重（同一章节可能在多页中出现）
        seen = set()
        unique = []
        for ch in chapters:
            key = ch['chapter_title'][:30]
            if key not in seen:
                seen.add(key)
                unique.append(ch)

        # 计算end_page（下一个同级章节的前一页）
        unique.sort(key=lambda x: x['start_page'])
        for i, ch in enumerate(unique):
            if i + 1 < len(unique):
                next_ch = unique[i + 1]
                if next_ch['level'] <= ch['level']:
                    ch['end_page'] = next_ch['start_page'] - 1
            if ch['end_page'] is None:
                ch['end_page'] = pages[-1]['page_number'] if pages else ch['start_page']

        return unique

    # ============================================================
    # _match_system() — 章节名→人体系统匹配
    # ============================================================
    def _match_system(self, chapter_title):
        """根据章节标题匹配人体系统"""
        for keyword, system_name in self.CHAPTER_SYSTEM_MAP.items():
            if keyword in chapter_title:
                return system_name
        return None

    # ============================================================
    # index_disease_knowledge() — 在章节中索引疾病知识点
    # 作用: 按章节范围扫描页面文本，检测疾病名称+定义/机制/治疗段落
    # 返回: list[{disease_name, info_type, page_id, snippet, char_start, char_end}]
    # ============================================================
    def index_disease_knowledge(self, pages, chapters):
        """索引疾病知识点，建立精确引用"""
        knowledge_refs = []
        all_text = '\n'.join([p['raw_text'] for p in pages])

        # 在每个章节范围内查找疾病
        for chapter in chapters:
            if not chapter['body_system']:
                continue  # 跳过未匹配到系统的章节

            start_page = chapter['start_page']
            end_page = chapter['end_page'] or pages[-1]['page_number']

            # 收集该章节范围内的所有页面文本
            chapter_pages = [p for p in pages if start_page <= p['page_number'] <= end_page]
            chapter_text = '\n'.join([p['raw_text'] for p in chapter_pages])

            # 在该章节中搜索可能的疾病名称
            found_diseases = self._extract_disease_names(chapter_text)

            for disease_name in found_diseases[:15]:  # 每章最多15个
                # 在章节文本中精确定位
                for page_data in chapter_pages:
                    idx = page_data['raw_text'].find(disease_name)
                    if idx < 0:
                        continue

                    # 获取该段的上下文
                    context_start = max(0, idx - 50)
                    context_end = min(len(page_data['raw_text']), idx + len(disease_name) + 200)
                    context = page_data['raw_text'][context_start:context_end]

                    # 检测知识点类型
                    info_type = self._detect_info_type(context)

                    if info_type:
                        knowledge_refs.append({
                            'disease_name': disease_name,
                            'info_type': info_type,
                            'page_number': page_data['page_number'],
                            'context_snippet': context[:300],
                            'char_start': idx,
                            'char_end': idx + len(disease_name),
                            'body_system': chapter['body_system'],
                            'chapter_title': chapter['chapter_title'],
                        })
                        break  # 每个疾病每章只取一个主要引用

        return knowledge_refs

    # ============================================================
    # _extract_disease_names() — 从文本中提取疾病名称
    # ============================================================
    def _extract_disease_names(self, text):
        """从文本中提取疾病名称"""
        disease_names = set()

        # 模式1: "XX病" "XX症"等
        pattern1 = re.compile(r'([^\s，。；、]{2,12}(?:病|症|炎|瘤|癌|综合征|衰竭|梗死))')
        for m in pattern1.finditer(text):
            name = m.group(1).strip()
            if self._is_valid_disease(name):
                disease_names.add(name)

        # 模式2: "急性/慢性 XX病"
        pattern2 = re.compile(r'((?:急性|慢性|原发|继发|获得性|先天性)[^\s，。；、]{2,10}(?:病|症|炎|瘤|癌|综合征))')
        for m in pattern2.finditer(text):
            name = m.group(1).strip()
            if self._is_valid_disease(name):
                disease_names.add(name)

        return list(disease_names)[:20]

    # ============================================================
    # _detect_info_type() — 检测知识点类型
    # ============================================================
    def _detect_info_type(self, context):
        """根据上下文检测知识点类型"""
        # 定义
        if re.search(r'(?:定义|概述|是指|概念|简称)', context):
            return 'definition'
        # 发病机制
        if re.search(r'(?:发病机制|病因|病理生理|发病原因|致病|机制)', context):
            return 'pathogenesis'
        # 预防
        if re.search(r'(?:预防|防治)', context):
            return 'prevention'
        # 治疗
        if re.search(r'(?:治疗|处理|疗法|方案)', context[:100]):
            return 'treatment'
        # 鉴别诊断
        if re.search(r'(?:鉴别|区别|区分|需与|应与)', context):
            return 'differential_diagnosis'
        return None

    # ============================================================
    # _is_valid_disease() — 验证疾病名有效性
    # ============================================================
    def _is_valid_disease(self, name):
        """验证疾病名称有效性"""
        if not name or len(name) < 2 or len(name) > 30:
            return False
        # 排除噪声
        noise = ['编委', '主编', '教授', '出版社', 'ISBN', '版权', '印刷',
                 '博士', '硕士', '医院', '医学院', '大学', '规划教材', '指导委员会']
        for n in noise:
            if n in name:
                return False
        # 必须包含医学术语特征
        medical = ['病', '症', '炎', '瘤', '癌', '综合征', '衰竭', '梗死',
                   '出血', '中毒', '休克']
        return any(m in name for m in medical)

    # ============================================================
    # save_to_database() — 将提取结果写入数据库
    # ============================================================
    def save_to_database(self, textbook, pages, chapters, knowledge_refs):
        """将提取结果写入数据库表"""
        from models import db, TextbookPage, TextbookChapter, KnowledgeRef, Disease, DiseaseInfo, BodySystem

        # Step 1: 逐页存储原文
        for page_data in pages:
            existing = (TextbookPage.query
                        .filter_by(textbook_id=textbook.id, page_number=page_data['page_number'])
                        .first())
            if not existing:
                tp = TextbookPage(
                    textbook_id=textbook.id,
                    page_number=page_data['page_number'],
                    raw_text=page_data['raw_text'],
                    char_count=page_data['char_count'],
                )
                db.session.add(tp)
                self.stats['pages_stored'] += 1

        db.session.commit()

        # Step 2: 存储章节结构
        for ch_data in chapters:
            system_id = None
            if ch_data.get('body_system'):
                system = BodySystem.query.filter_by(name=ch_data['body_system']).first()
                if system:
                    system_id = system.id

            existing_ch = (TextbookChapter.query
                           .filter_by(textbook_id=textbook.id,
                                      chapter_title=ch_data['chapter_title'])
                           .first())
            if not existing_ch:
                tc = TextbookChapter(
                    textbook_id=textbook.id,
                    chapter_title=ch_data['chapter_title'],
                    level=ch_data.get('level', 1),
                    start_page=ch_data['start_page'],
                    end_page=ch_data.get('end_page'),
                    body_system_id=system_id,
                )
                db.session.add(tc)
                self.stats['chapters_found'] += 1

        db.session.commit()

        # Step 3: 存储知识点引用
        for ref_data in knowledge_refs:
            page = TextbookPage.query.filter_by(
                textbook_id=textbook.id,
                page_number=ref_data['page_number']
            ).first()
            if not page:
                continue

            # 查找或创建疾病
            system = BodySystem.query.filter_by(name=ref_data['body_system']).first()
            if not system:
                continue

            disease = Disease.query.filter_by(
                name=ref_data['disease_name'],
                system_id=system.id,
            ).first()

            if not disease:
                disease = Disease(
                    name=ref_data['disease_name'],
                    system_id=system.id,
                    level=textbook.level,
                )
                db.session.add(disease)
                db.session.flush()

            # 创建精确引用
            kr = KnowledgeRef(
                disease_id=disease.id,
                page_id=page.id,
                info_type=ref_data['info_type'],
                context_snippet=ref_data['context_snippet'],
                char_start=ref_data['char_start'],
                char_end=ref_data['char_end'],
            )
            db.session.add(kr)

            # 同时创建DiseaseInfo（如果这个知识点是定义级别的重要内容）
            if ref_data['info_type'] == 'definition':
                existing_info = DiseaseInfo.query.filter_by(
                    disease_id=disease.id,
                    info_type='definition',
                    textbook_id=textbook.id,
                ).first()
                if not existing_info:
                    di = DiseaseInfo(
                        disease_id=disease.id,
                        info_type=ref_data['info_type'],
                        content=ref_data['context_snippet'],
                        textbook_id=textbook.id,
                        page_id=page.id,
                        page_ref=f'P{page.page_number}',
                        chapter_ref=ref_data.get('chapter_title', ''),
                        is_verbatim=True,
                    )
                    db.session.add(di)

            self.stats['knowledge_refs'] += 1

        db.session.commit()

    # ============================================================
    # process_textbook() — 处理单本教材的完整流水线
    # ============================================================
    def process_textbook(self, pdf_info, max_pages=None):
        """完整处理一本教材: 提取→检测→索引→存储"""
        from models import Textbook, db
        from config import DATA_DIR

        print(f'\n{"="*60}')
        print(f'📖 处理: {pdf_info["name"]}')
        print(f'   PDF: {pdf_info["filename"]} ({pdf_info["size_mb"]}MB)')
        print(f'{"="*60}')

        # Step 1: 创建/获取教材记录
        print('  [1/5] 创建教材记录...')
        textbook = Textbook.query.filter_by(title=pdf_info['name'], level='undergraduate').first()
        if not textbook:
            textbook = Textbook(
                title=pdf_info['name'],
                author='人民卫生出版社',
                edition='第10版',
                publisher='人民卫生出版社',
                year=2024,
                level='undergraduate',
            )
            db.session.add(textbook)
            db.session.commit()
            print(f'        新增教材: {pdf_info["name"]}')
        else:
            print(f'        教材已存在: {pdf_info["name"]}')

        # Step 2: 检查是否已处理过
        from models import TextbookPage
        existing_pages = TextbookPage.query.filter_by(textbook_id=textbook.id).count()
        if existing_pages > 0:
            print(f'        已存在 {existing_pages} 页，跳过')
            return {'textbook': pdf_info['name'], 'pages': existing_pages, 'skipped': True}

        # Step 3: 逐页提取原文
        print(f'  [2/5] 逐页提取原文...')
        pages = self.extract_all_pages(pdf_info['path'], max_pages=max_pages)
        print(f'        提取了 {len(pages)} 页原文（{sum(p["char_count"] for p in pages)} 字符）')

        if not pages:
            print('        ⚠️ 未提取到任何内容')
            return {'textbook': pdf_info['name'], 'pages': 0, 'error': 'No text extracted'}

        # Step 4: 检测章节结构
        print(f'  [3/5] 检测章节结构...')
        chapters = self.detect_chapters(pages)
        chapters_with_system = [c for c in chapters if c.get('body_system')]
        print(f'        检测到 {len(chapters)} 个章节')
        print(f'        其中 {len(chapters_with_system)} 个匹配到人体系统')

        # Step 5: 索引知识点
        print(f'  [4/5] 索引知识点...')
        knowledge_refs = self.index_disease_knowledge(pages, chapters)
        print(f'        索引了 {len(knowledge_refs)} 个知识点引用')

        # Step 6: 写入数据库
        print(f'  [5/5] 写入数据库...')
        self.save_to_database(textbook, pages, chapters, knowledge_refs)
        print(f'        存储 {self.stats["pages_stored"]} 页原文')
        print(f'        存储 {self.stats["chapters_found"]} 个章节')
        print(f'        建立 {self.stats["knowledge_refs"]} 个知识点引用')

        return {
            'textbook': pdf_info['name'],
            'pages': len(pages),
            'chapters': len(chapters),
            'knowledge_refs': len(knowledge_refs),
        }

    # ============================================================
    # run_batch() — 批量处理所有PDF
    # ============================================================
    def run_batch(self, max_pages_per_book=None):
        """批量处理所有教材"""
        pdfs = self.discover_pdfs()
        if not pdfs:
            print(f'未找到PDF文件 (源目录: {self.pdf_dir})')
            return []

        print(f'找到 {len(pdfs)} 本教材PDF')
        self.stats['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        results = []
        for pdf_info in pdfs:
            # 跳过目录校对版和重复文件
            if '目录校对' in pdf_info['filename']:
                print(f'\n  跳过: {pdf_info["filename"]} (目录校对版)')
                continue
            if '外科学 第10版' in pdf_info['filename'] and any(
                    r.get('skipped') and r.get('textbook') == '外科学'
                    for r in results):
                print(f'\n  跳过: {pdf_info["filename"]} (外科学已处理)')
                continue

            try:
                result = self.process_textbook(pdf_info, max_pages=max_pages_per_book)
                results.append(result)
            except Exception as e:
                error_msg = f'{pdf_info["name"]}: {str(e)}'
                self.stats['errors'].append(error_msg)
                print(f'  ❌ {error_msg}')
                import traceback
                traceback.print_exc()

        self.stats['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 汇总
        print(f'\n{"="*60}')
        print(f'📊 批处理完成')
        print(f'{"="*60}')
        print(f'处理教材: {len([r for r in results if not r.get("skipped") and not r.get("error")])}')
        print(f'总存储页数: {self.stats["pages_stored"]}')
        print(f'总章节数: {self.stats["chapters_found"]}')
        print(f'总知识点引用: {self.stats["knowledge_refs"]}')
        print(f'错误数: {len(self.stats["errors"])}')

        return results


# ============================================
# 独立运行入口
# ============================================
if __name__ == '__main__':
    # 需要在Flask应用上下文中运行
    from app import create_app
    app = create_app()
    with app.app_context():
        processor = VerbatimPdfProcessor()
        processor.run_batch(max_pages_per_book=None)  # None=不限页数，全部提取
