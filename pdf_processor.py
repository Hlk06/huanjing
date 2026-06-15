# ============================================
# pdf_processor.py — PDF教材批量提取与结构化处理
# 作用:
#   1. 从第10版教材PDF中提取文字内容
#   2. 自动识别疾病章节、症状、定义等信息
#   3. 按人体系统分类生成Markdown导入文件
#   4. 支持增量处理，避免重复工作
# ============================================

import os
import re
import sys
from pypdf import PdfReader
from config import DATA_DIR

# --- 配置 ---
PDF_SOURCE_DIR = r"D:\第10版资料"
OUTPUT_DIR = os.path.join(DATA_DIR, "textbook_10th")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 教材与人体系统的映射
TEXTBOOK_SYSTEM_MAP = {
    '内科学': ['心血管系统', '呼吸系统', '消化系统', '泌尿系统', '血液系统',
               '内分泌系统', '免疫系统', '神经系统'],
    '外科学': ['消化系统', '泌尿系统', '神经系统', '运动系统', '心血管系统',
               '呼吸系统', '皮肤系统', '感官系统'],
    '妇产科学': ['生殖系统'],
    '儿科学': ['呼吸系统', '消化系统', '神经系统', '心血管系统', '血液系统',
              '泌尿系统', '免疫系统'],
    '传染病学': ['呼吸系统', '消化系统', '神经系统', '血液系统'],
    '人体寄生虫学': ['消化系统', '血液系统', '皮肤系统'],
    '医学微生物学': ['呼吸系统', '消化系统', '泌尿系统', '神经系统'],
    '病理学': ['心血管系统', '呼吸系统', '消化系统', '泌尿系统', '神经系统',
              '血液系统', '免疫系统'],
    '病理生理学': ['心血管系统', '呼吸系统', '泌尿系统', '神经系统', '血液系统'],
    '生理学': ['心血管系统', '呼吸系统', '消化系统', '泌尿系统', '神经系统',
              '内分泌系统'],
    '药理学': ['心血管系统', '神经系统', '内分泌系统', '呼吸系统', '消化系统'],
    '诊断学': ['心血管系统', '呼吸系统', '消化系统', '泌尿系统', '神经系统'],
    '系统解剖学': ['运动系统', '消化系统', '呼吸系统', '泌尿系统', '生殖系统',
                 '心血管系统', '感官系统', '神经系统', '内分泌系统'],
    '局部解剖学': ['运动系统', '消化系统', '呼吸系统', '泌尿系统', '生殖系统',
                 '心血管系统'],
    '组织学与胚胎学': ['生殖系统', '消化系统', '呼吸系统', '泌尿系统',
                     '心血管系统', '神经系统', '内分泌系统'],
    '生物化学与分子生物学': ['消化系统', '血液系统', '内分泌系统', '神经系统'],
}


class PdfTextbookProcessor:
    """PDF教材处理引擎 — 提取文本，解析结构，生成Markdown"""

    def __init__(self, pdf_dir=PDF_SOURCE_DIR, output_dir=OUTPUT_DIR):
        self.pdf_dir = pdf_dir
        self.output_dir = output_dir
        self.processed_files = set()
        self.extracted_pages = 0
        self.disease_count = 0

    def discover_pdfs(self):
        """扫描PDF源目录，返回教材文件列表"""
        pdfs = []
        for f in os.listdir(self.pdf_dir):
            if f.endswith('.pdf'):
                full_path = os.path.join(self.pdf_dir, f)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                # 提取教材名（去除"第10版"等）
                name = re.sub(r'\s*第\d+版\s*', '', f.replace('.pdf', '')).strip()
                name = re.sub(r'\s*目录校对版\s*', '', name).strip()
                pdfs.append({
                    'filename': f,
                    'name': name,
                    'path': full_path,
                    'size_mb': round(size_mb, 1),
                })
        return sorted(pdfs, key=lambda x: x['name'])

    def extract_text_from_pdf(self, pdf_path, max_pages=None):
        """从PDF文件提取文本内容
        Args:
            pdf_path: PDF文件路径
            max_pages: 最大提取页数（None=全部）
        Returns:
            dict: {'pages': [{'num': 1, 'text': '...'}, ...], 'total_pages': N}
        """
        reader = PdfReader(pdf_path)
        total = len(reader.pages)
        if max_pages:
            total = min(total, max_pages)

        pages = []
        for i in range(total):
            try:
                page = reader.pages[i]
                text = page.extract_text()
                if text and text.strip():
                    pages.append({
                        'num': i + 1,
                        'text': text.strip(),
                    })
            except Exception as e:
                print(f'  [WARN] 第{i+1}页提取失败: {e}')

        return {'pages': pages, 'total_pages': total}

    def find_chapter_structure(self, text):
        """识别章节标题结构"""
        chapters = []
        # 匹配"第X章"格式
        chap_pattern = re.compile(r'^第[一二三四五六七八九十百\d]+章\s+.+$', re.MULTILINE)
        for match in chap_pattern.finditer(text):
            chapters.append({
                'title': match.group().strip(),
                'position': match.start(),
            })
        return chapters

    def find_disease_sections(self, text):
        """识别疾病相关段落
        通过关键词模式识别疾病定义、病因、临床表现等段落
        """
        diseases = []
        # 扩展的疾病段落起始模式
        disease_patterns = [
            # 模式1: 疾病关键词 + 可选的定义标记
            r'(?:^|\n)([^\n]{2,30}(?:病|症|炎|瘤|癌|综合征|衰竭|梗死|出血|中毒|休克|水肿|贫血|肥大|硬化|狭窄|栓塞|感染|绞痛|麻痹|囊肿|异位|畸形))[\n\s]*(?:概述|定义|概念|是指)?',
            # 模式2: 章节节标题格式
            r'(?:^|\n)第[一二三四五六七八九十\d]+节\s+([^\n]{3,30})',
            # 模式3: "第一节 XX疾病" 格式 (PDF常见)
            r'(?:^|\n)[一二三四五六七八九十\d]+[、.]\s*(?:急性|慢性|原发|继发|先天|获得)?([^\n]{2,25}(?:病|症|炎|瘤|癌|综合征))',
            # 模式4: 明确疾病名称（含修饰词）
            r'(?:^|\n)((?:急性|慢性|原发|继发|先天|获得|弥漫|局限|全身|局部|特发)(?:性)?[^\n]{2,20}(?:病|症|炎|瘤|癌|综合征))',
        ]

        for pattern in disease_patterns:
            for match in re.finditer(pattern, text):
                disease_name = match.group(1).strip()
                # 过滤噪声
                if not self._is_valid_disease_name(disease_name):
                    continue
                if len(disease_name) < 2 or len(disease_name) > 30:
                    continue

                start = match.start()
                context = text[start:start + 8000]
                # 检测该位置是否在目录或索引区域（前200字符含"目录"/"参考文献"则跳过）
                pre_context = text[max(0, start-200):start]
                if '录' in pre_context[:50] and '录' in pre_context[:20]:
                    continue
                if '参考文献' in pre_context[:50]:
                    continue

                diseases.append({
                    'name': disease_name,
                    'position': start,
                    'context': context,
                })

        # 去重（按名称 + 相近位置合并）
        seen = {}
        for d in diseases:
            key = d['name']
            if key in seen:
                # 如果位置相近(500字符以内)则跳过
                if abs(d['position'] - seen[key]) < 500:
                    continue
            seen[key] = d['position']
        return [{'name': k, 'position': v, 'context': ''} for k, v in seen.items()]

    def extract_disease_info(self, disease_context):
        """从疾病上下文中提取结构化信息（宽松匹配）"""
        info = {
            'definition': '',
            'pathogenesis': '',
            'prevention': '',
            'treatment': '',
            'differential_diagnosis': '',
        }

        # 定义/概述 — 宽松匹配：任何描述性的句子
        # 尝试匹配"XX是XX"、"XX指XX"等定义句式
        def_patterns = [
            r'([^。\n]{2,30}(?:是|是指|指|系指|为|主要指)[^。\n]{5,400}?[。；\n])',
            r'(?:定义|概述|概念|简介)[：:]*\s*([^。\n]{5,500}?[。；\n])',
            r'(?:是一[种类][^。\n]{5,500}?[。；\n])',
        ]
        for pat in def_patterns:
            m = re.search(pat, disease_context, re.DOTALL)
            if m:
                info['definition'] = m.group(0).strip()[:500]
                break
        # Fallback: use first meaningful sentence
        if not info['definition']:
            sentences = re.findall(r'[^。\n]{10,300}[。]', disease_context[:2000])
            if sentences:
                info['definition'] = sentences[0][:300]

        # 发病机制 — 匹配包含病因/机制关键词的段落
        path_keywords = ['发病机制', '病因', '病理生理', '发病原因', '致病', '发病机理',
                         '病理改变', '机制', '病因与发病机制', '病因和发病机制']
        for kw in path_keywords:
            idx = disease_context.find(kw)
            if idx >= 0:
                # 从关键词后取500字符
                snippet = disease_context[idx:idx + 800]
                # 提取到下一个段落标记或句号群
                stop = re.search(r'\n\s*(?:第[一二三四五六七八九十\d]+节|[一二三四五六七八九十\d]+[、.]|[A-Z][A-Z])', snippet)
                end = stop.start() if stop else min(len(snippet), 500)
                info['pathogenesis'] = snippet[:end].strip()[:600]
                break

        # 治疗 — 匹配治疗相关内容
        treat_keywords = ['治疗', '处理', '疗法', '治疗方案', '处理原则']
        for kw in treat_keywords:
            idx = disease_context.find(kw)
            if idx >= 0:
                snippet = disease_context[idx:idx + 800]
                stop = re.search(r'\n\s*(?:第[一二三四五六七八九十\d]+节|[一二三四五六七八九十\d]+[、.]|预防)', snippet)
                end = stop.start() if stop else min(len(snippet), 500)
                info['treatment'] = snippet[:end].strip()[:600]
                break

        # 预防
        prevent_keywords = ['预防', '防治', '预防原则', '预防措施']
        for kw in prevent_keywords:
            idx = disease_context.find(kw)
            if idx >= 0:
                snippet = disease_context[idx:idx + 600]
                info['prevention'] = snippet[:400].strip()[:400]
                break

        # 鉴别诊断
        diff_keywords = ['鉴别诊断', '鉴别', '需与.*鉴别', '应与.*鉴别']
        for kw in diff_keywords:
            idx = disease_context.find(kw)
            if idx >= 0:
                snippet = disease_context[idx:idx + 800]
                stop = re.search(r'\n\s*(?:第[一二三四五六七八九十\d]+节|[一二三四五六七八九十\d]+[、.]|治疗)', snippet)
                end = stop.start() if stop else min(len(snippet), 500)
                info['differential_diagnosis'] = snippet[:end].strip()[:600]
                break

        return info

    def _is_valid_disease_name(self, name):
        """验证是否为有效的疾病名称（噪声过滤）"""
        if not name: return False
        # 排除纯标点/数字开头
        if name[0] in '0123456789、.·•·□■△▲○●☆★§':
            return False
        # 排除明显的编辑出版类词汇
        noise_words = ['编委', '主编', '教授', '博士生', '硕士生', '主任医师',
                       '副教授', '讲师', '助教', '编写', '修订', '校对',
                       '出版社', '印刷', '版次', '印次', 'ISBN', 'CIP',
                       '规划教材', '指导委员会', '医学院', '医科大学']
        for nw in noise_words:
            if nw in name:
                return False
        # 排除纯功能性描述
        if name in ['前言', '目录', '索引', '附录', '参考文献', '练习题',
                     '思考题', '答案', '后记', '缩略语', '符号说明']:
            return False
        # 至少包含一个医学术语特征
        medical_suffix = ['病', '症', '炎', '瘤', '癌', '综合征', '衰竭',
                          '梗死', '出血', '中毒', '休克', '水肿', '贫血',
                          '肥大', '硬化', '狭窄', '栓塞', '感染', '绞痛']
        if not any(suffix in name for suffix in medical_suffix):
            return False
        return True

    def suggest_body_system(self, textbook_name, disease_name, context):
        """根据教材名、章节内容和疾病名推荐人体系统分类
        优先使用章节标题中的系统关键词，其次用疾病名匹配
        """
        # 教材→系统映射（默认候选）
        systems = TEXTBOOK_SYSTEM_MAP.get(textbook_name, [])

        # 章节标题→系统映射（从PDF文本中读取的章节标题）
        chapter_system_map = {
            '循环系统': '心血管系统', '心血管': '心血管系统',
            '呼吸系统': '呼吸系统', '呼吸': '呼吸系统',
            '消化系统': '消化系统', '消化': '消化系统',
            '泌尿系统': '泌尿系统', '泌尿': '泌尿系统', '肾脏': '泌尿系统',
            '生殖系统': '生殖系统', '生殖': '生殖系统', '妇产': '生殖系统',
            '神经系统': '神经系统', '神经': '神经系统',
            '内分泌': '内分泌系统', '代谢': '内分泌系统',
            '血液系统': '血液系统', '血液': '血液系统', '造血': '血液系统',
            '运动系统': '运动系统', '骨': '运动系统', '关节': '运动系统',
            '免疫': '免疫系统', '风湿': '免疫系统', '自身免疫': '免疫系统',
            '皮肤': '皮肤系统', '性病': '皮肤系统',
            '眼': '感官系统', '耳鼻咽喉': '感官系统', '口腔': '感官系统',
            '感染': '呼吸系统', '传染': '呼吸系统',
        }

        # Step 1: 从疾病所在上下文检查章节标题（前800字符）
        context_preview = (context or '')[:800]
        for chapter_kw, system_name in chapter_system_map.items():
            if chapter_kw in context_preview:
                return system_name

        # Step 2: 从疾病名关键词匹配

        # 关键词→系统映射
        keyword_system_map = {
            '心': '心血管系统', '冠': '心血管系统', '高血压': '心血管系统',
            '肺': '呼吸系统', '呼吸': '呼吸系统', '咳': '呼吸系统',
            '胃': '消化系统', '肠': '消化系统', '肝': '消化系统', '胆': '消化系统',
            '肾': '泌尿系统', '膀胱': '泌尿系统', '尿': '泌尿系统',
            '子宫': '生殖系统', '卵巢': '生殖系统', '生殖': '生殖系统',
            '脑': '神经系统', '神经': '神经系统', '脊髓': '神经系统',
            '骨': '运动系统', '关节': '运动系统', '肌肉': '运动系统',
            '血': '血液系统', '贫血': '血液系统', '白血病': '血液系统',
            '免疫': '免疫系统', '过敏': '免疫系统',
            '皮肤': '皮肤系统', '皮': '皮肤系统',
            '眼': '感官系统', '耳': '感官系统', '鼻': '感官系统',
            '糖尿': '内分泌系统', '甲状腺': '内分泌系统', '激素': '内分泌系统',
        }

        for keyword, system in keyword_system_map.items():
            if keyword in disease_name or keyword in (context or '')[:200]:
                if system in systems or not systems:
                    return system

        return systems[0] if systems else '其他'

    def generate_markdown(self, textbook_name, diseases_data):
        """生成结构化的Markdown导入文件"""
        output_path = os.path.join(self.output_dir, f'{textbook_name}.md')

        lines = [
            f'## 教材: {textbook_name}',
            '作者: 人民卫生出版社',
            '版次: 第10版',
            '出版社: 人民卫生出版社',
            '年份: 2024',
            '层次: undergraduate',
            '',
        ]

        for disease in diseases_data:
            if not disease.get('name') or not disease.get('system'):
                continue

            # 构建症状列表
            symptom_str = ''
            if disease.get('symptoms'):
                symptom_parts = []
                for s in disease['symptoms']:
                    rel = s.get('relevance', 'common')
                    symptom_parts.append(f'{s["name"]}({rel})')
                symptom_str = '、'.join(symptom_parts)

            lines.append(f'### 疾病: {disease["name"]}')
            if disease.get('name_en'):
                lines.append(f'英文名: {disease["name_en"]}')
            lines.append(f'系统: {disease["system"]}')
            lines.append(f'层次: undergraduate')
            if symptom_str:
                lines.append(f'关联症状: {symptom_str}')
            if disease.get('overview'):
                lines.append(f'概述: {disease["overview"][:200]}')
            lines.append('')

            # 添加各类信息
            for info_type, label in [
                ('definition', '定义'),
                ('pathogenesis', '发病机制'),
                ('prevention', '预防原则'),
                ('treatment', '治疗方案'),
                ('differential_diagnosis', '鉴别诊断'),
            ]:
                if disease['info'].get(info_type):
                    lines.append(f'#### {label}')
                    lines.append(disease['info'][info_type][:2000])
                    lines.append(f'出处页码: 参考{textbook_name}第10版')
                    lines.append(f'出处章节: {disease.get("chapter", "相关章节")}')
                    lines.append('')

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return output_path

    def process_textbook(self, pdf_info, max_pages_per_book=50):
        """处理单本教材：提取文本 → 识别疾病 → 生成Markdown"""
        print(f'\n{"="*60}')
        print(f'处理: {pdf_info["name"]} ({pdf_info["size_mb"]}MB)')
        print(f'{"="*60}')

        # Step 1: 提取PDF文本
        print(f'  [1/4] 提取PDF文本...')
        result = self.extract_text_from_pdf(pdf_info['path'], max_pages=max_pages_per_book)
        print(f'        已提取 {len(result["pages"])}/{result["total_pages"]} 页')
        self.extracted_pages += len(result['pages'])

        # Step 2: 合并文本并查找章节结构
        print(f'  [2/4] 分析章节结构...')
        full_text = '\n'.join([p['text'] for p in result['pages']])
        chapters = self.find_chapter_structure(full_text)
        print(f'        找到 {len(chapters)} 个章节')

        # Step 3: 识别疾病段落
        print(f'  [3/4] 识别疾病内容...')
        disease_sections = self.find_disease_sections(full_text)
        print(f'        找到 {len(disease_sections)} 个疑似疾病段落')

        # Step 4: 结构化提取并分类
        print(f'  [4/4] 结构化提取信息...')
        diseases_data = []
        for d_sec in disease_sections[:30]:  # 每本教材最多提取30个疾病
            info = self.extract_disease_info(d_sec['context'])
            # 跳过没有实质内容的
            if not any(info.values()):
                continue

            system = self.suggest_body_system(
                pdf_info['name'], d_sec['name'], d_sec['context'])

            # 找到疾病所在的章节
            chapter = '相关章节'
            for ch in reversed(chapters):
                if ch['position'] < d_sec['position']:
                    chapter = ch['title']
                    break

            # 提取可能的症状关键词
            symptoms = self.extract_symptoms(d_sec['context'])

            diseases_data.append({
                'name': d_sec['name'],
                'name_en': '',
                'system': system,
                'symptoms': symptoms,
                'overview': info.get('definition', '')[:200],
                'info': info,
                'chapter': chapter,
            })
            self.disease_count += 1

        # 生成Markdown文件
        if diseases_data:
            output_path = self.generate_markdown(pdf_info['name'], diseases_data)
            print(f'        ✅ 已生成: {output_path}')
            print(f'        📊 提取了 {len(diseases_data)} 个疾病条目')
        else:
            print(f'        ⚠️ 未提取到疾病内容')

        return len(diseases_data)

    def extract_symptoms(self, text):
        """从文本中提取可能的症状关键词"""
        symptom_keywords = [
            '发热', '咳嗽', '咳痰', '胸痛', '呼吸困难', '心悸', '水肿', '头痛',
            '腹痛', '恶心', '呕吐', '腹泻', '便血', '血尿', '蛋白尿', '黄疸',
            '乏力', '消瘦', '体重减轻', '关节痛', '皮疹', '瘙痒', '麻木',
            '瘫痪', '抽搐', '昏迷', '眩晕', '耳鸣', '鼻出血', '咯血', '呕血',
            '便秘', '腹胀', '吞咽困难', '反酸', '烧心', '发绀', '苍白', '出血',
            '贫血', '淋巴结肿大', '肝脾肿大', '高血压', '低血压', '心律失常',
            '晕厥', '意识障碍', '疼痛', '肿块', '溃疡',
        ]
        found = []
        text_2000 = text[:2000]
        for kw in symptom_keywords:
            if kw in text_2000:
                # 判断关联度
                relevance = 'common'
                if kw in text_2000[:500]:  # 出现在靠前位置→可能是主要症状
                    relevance = 'main'
                found.append({'name': kw, 'relevance': relevance})

        # 去重并限制数量
        seen = set()
        unique = []
        for s in found:
            if s['name'] not in seen:
                seen.add(s['name'])
                unique.append(s)
        return unique[:8]

    def run_batch(self, max_pages_per_book=50):
        """批量处理所有教材"""
        pdfs = self.discover_pdfs()
        print(f'找到 {len(pdfs)} 本第10版教材PDF')
        print(f'输出目录: {self.output_dir}')

        results = []
        for pdf_info in pdfs:
            try:
                count = self.process_textbook(pdf_info, max_pages_per_book)
                results.append({
                    'textbook': pdf_info['name'],
                    'diseases_found': count,
                    'status': 'success',
                })
            except Exception as e:
                print(f'  ❌ 处理失败: {e}')
                results.append({
                    'textbook': pdf_info['name'],
                    'diseases_found': 0,
                    'status': f'error: {e}',
                })

        # 汇总
        print(f'\n{"="*60}')
        print(f'📊 批量处理完成')
        print(f'{"="*60}')
        print(f'总处理页数: {self.extracted_pages}')
        print(f'总提取疾病: {self.disease_count}')
        print(f'\n各教材统计:')
        for r in results:
            print(f'  {r["textbook"]}: {r["diseases_found"]} 个疾病 [{r["status"]}]')

        return results


# ============================================
# 独立运行入口
# ============================================
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PDF教材批量提取工具')
    parser.add_argument('--max-pages', type=int, default=50,
                        help='每本教材最大提取页数 (默认50)')
    parser.add_argument('--textbook', type=str, default=None,
                        help='仅处理指定教材 (如"内科学")')
    parser.add_argument('--test', action='store_true',
                        help='测试模式：仅处理1本教材的前5页')
    args = parser.parse_args()

    processor = PdfTextbookProcessor()

    if args.test:
        pdfs = processor.discover_pdfs()
        if pdfs:
            # 优先处理内科学
            internal = [p for p in pdfs if '内科学' in p['name'] and '外' not in p['name']]
            target = internal[0] if internal else pdfs[0]
            processor.process_textbook(target, max_pages_per_book=5)
    elif args.textbook:
        pdfs = processor.discover_pdfs()
        target = next((p for p in pdfs if args.textbook in p['name']), None)
        if target:
            processor.process_textbook(target, max_pages_per_book=args.max_pages)
        else:
            print(f'未找到教材: {args.textbook}')
    else:
        processor.run_batch(max_pages_per_book=args.max_pages)
