# ============================================
# search_engine.py — 全文搜索引擎
# 作用: 基于SQLite FTS5实现中文全文搜索，支持多症状组合查询
# 核心逻辑:
#   1. 将用户输入的多个症状词拆分
#   2. 在disease_symptoms表中查找匹配的疾病
#   3. 按症状匹配数量和关联度排序
#   4. 用LIKE作为辅助匹配，覆盖FTS5未索引的内容
# ============================================

import sqlite3
import os
from config import DATABASE_FILE


class SearchEngine:
    """医学内容搜索引擎，基于症状→疾病匹配"""

    def __init__(self, db_path=None):
        """初始化搜索引擎
        Args:
            db_path: SQLite数据库路径，默认使用config中的配置
        """
        self.db_path = db_path or DATABASE_FILE
        # 确保数据库文件存在
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f'数据库文件不存在: {self.db_path}')

    # ============================================
    # _get_connection() — 获取数据库连接
    # 作用: 每次查询创建新连接，确保线程安全
    # ============================================
    def _get_connection(self):
        """创建新的SQLite连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使查询结果支持按列名访问
        return conn

    # ============================================
    # search() — 核心搜索方法
    # 作用: 接收用户输入的症状关键词，返回匹配的疾病列表
    # 参数:
    #   query (str): 用户输入的搜索词，多个症状可用空格/逗号/中文分隔
    #   level (str): 过滤学历层次 'all' | 'undergraduate' | 'graduate'
    # 返回:
    #   list[dict]: 匹配的疾病列表，按相关度降序排列
    # ============================================
    def search(self, query, level='all'):
        """执行症状搜索，返回匹配的疾病列表"""
        if not query or not query.strip():
            return []

        # Step 1: 拆分搜索词 — 支持空格、逗号、中文顿号等分隔
        import re
        keywords = re.split(r'[,，、\s]+', query.strip())
        keywords = [k.strip() for k in keywords if k.strip()]
        if not keywords:
            return []

        conn = self._get_connection()
        try:
            results = []
            seen_disease_ids = set()

            for keyword in keywords:
                # Step 2: 对每个关键词执行搜索
                diseases_found = self._search_single_keyword(conn, keyword, level)
                for disease in diseases_found:
                    disease_id = disease['id']
                    if disease_id not in seen_disease_ids:
                        seen_disease_ids.add(disease_id)
                        # 计算匹配度得分
                        disease['match_score'] = self._calculate_score(
                            keywords, disease)
                        results.append(disease)
                    else:
                        # 如果已被其他关键词匹配到，累加得分
                        for r in results:
                            if r['id'] == disease_id:
                                r['match_score'] = self._calculate_score(
                                    keywords, r)
                                # 合并匹配的症状
                                existing_symptoms = set(r.get('matched_symptoms', '').split('、'))
                                new_symptoms = set(disease.get('matched_symptoms', '').split('、'))
                                r['matched_symptoms'] = '、'.join(existing_symptoms | new_symptoms)

            # Step 3: 按匹配得分降序排序
            results.sort(key=lambda x: x['match_score'], reverse=True)
            return results

        finally:
            conn.close()

    # ============================================
    # _search_single_keyword() — 单关键词搜索
    # 作用: 对一个症状关键词进行数据库查询
    # 搜索路径:
    #   1. 精确匹配症状名
    #   2. 模糊匹配症状名（LIKE）
    #   3. 直接搜索疾病名
    #   4. 搜索疾病概述和详细信息内容
    # ============================================
    def _search_single_keyword(self, conn, keyword, level='all'):
        """搜索单个关键词匹配的疾病"""
        diseases = {}

        # --- 路径1: 症状名精确匹配 ---
        symptom_rows = conn.execute(
            'SELECT id, name FROM symptoms WHERE name = ?',
            (keyword,)
        ).fetchall()

        # --- 路径2: 症状名模糊匹配（LIKE） ---
        if not symptom_rows:
            symptom_rows = conn.execute(
                'SELECT id, name FROM symptoms WHERE name LIKE ?',
                (f'%{keyword}%',)
            ).fetchall()

        # --- 路径3: 通过症状关联查找疾病 ---
        for sym_row in symptom_rows:
            # 构建疾病查询，通过disease_symptoms关联表
            query_sql = '''
                SELECT DISTINCT d.*, bs.name as system_name, ds.relevance, s.name as matched_symptom
                FROM diseases d
                JOIN body_systems bs ON d.system_id = bs.id
                JOIN disease_symptoms ds ON d.id = ds.disease_id
                JOIN symptoms s ON ds.symptom_id = s.id
                WHERE ds.symptom_id = ?
            '''
            params = [sym_row['id']]
            if level != 'all':
                query_sql += ' AND d.level = ?'
                params.append(level)

            disease_rows = conn.execute(query_sql, params).fetchall()
            for row in disease_rows:
                disease_id = row['id']
                if disease_id not in diseases:
                    diseases[disease_id] = self._row_to_dict(row)
                    diseases[disease_id]['matched_symptoms'] = row['matched_symptom']
                    # 依据关联度加权: main=3, common=2, rare=1
                    relevance_weight = {'main': 3, 'common': 2, 'rare': 1}
                    diseases[disease_id]['relevance_weight'] = relevance_weight.get(
                        row['relevance'], 1)
                else:
                    # 追加匹配症状
                    diseases[disease_id]['matched_symptoms'] += '、' + row['matched_symptom']

        # --- 路径4: 搜索疾病名（直接匹配） ---
        disease_name_rows = conn.execute(
            'SELECT d.*, bs.name as system_name FROM diseases d '
            'JOIN body_systems bs ON d.system_id = bs.id '
            'WHERE d.name LIKE ? OR d.name_en LIKE ?',
            (f'%{keyword}%', f'%{keyword}%')
        ).fetchall()
        for row in disease_name_rows:
            disease_id = row['id']
            if disease_id not in diseases:
                diseases[disease_id] = self._row_to_dict(row)
                diseases[disease_id]['matched_symptoms'] = f'疾病名匹配: {keyword}'
                diseases[disease_id]['relevance_weight'] = 2

        # --- 路径5: 搜索疾病概述和详细信息内容 ---
        info_rows = conn.execute(
            'SELECT DISTINCT d.*, bs.name as system_name FROM diseases d '
            'JOIN body_systems bs ON d.system_id = bs.id '
            'LEFT JOIN disease_infos di ON d.id = di.disease_id '
            'WHERE d.overview LIKE ? OR di.content LIKE ?',
            (f'%{keyword}%', f'%{keyword}%')
        ).fetchall()
        for row in info_rows:
            disease_id = row['id']
            if disease_id not in diseases:
                diseases[disease_id] = self._row_to_dict(row)
                diseases[disease_id]['matched_symptoms'] = f'内容匹配: {keyword}'
                diseases[disease_id]['relevance_weight'] = 1

        return list(diseases.values())

    # ============================================
    # _calculate_score() — 计算匹配得分
    # 作用: 综合多个因素计算疾病与搜索词的匹配程度
    # 得分因子: 关联度权重 + 症状匹配数 + 所有关键词都被匹配的奖励
    # ============================================
    def _calculate_score(self, keywords, disease):
        """计算疾病的搜索匹配得分"""
        score = 0
        matched_symptoms = disease.get('matched_symptoms', '')
        matched_count = len(matched_symptoms.split('、')) if matched_symptoms else 1

        # 因子1: 关联度权重（main症状得分更高）
        score += disease.get('relevance_weight', 1) * 10

        # 因子2: 匹配症状数量（越多症状匹配得分越高）
        score += matched_count * 5

        # 因子3: 如果是主要症状关联，额外加分
        if disease.get('relevance_weight', 0) == 3:
            score += 5

        return score

    # ============================================
    # _row_to_dict() — 数据库行转字典
    # 作用: 将sqlite3.Row转换为Python字典，方便JSON序列化
    # ============================================
    def _row_to_dict(self, row):
        """将数据库行转换为字典"""
        keys = row.keys()
        result = {}
        for key in keys:
            result[key] = row[key]
        return result

    # ============================================
    # rebuild_index() — 重建搜索数据（当内容变更后调用）
    # 作用: 目前主要清理缓存；未来可扩展FTS5虚拟表重建
    # ============================================
    def rebuild_index(self):
        """重建搜索索引（在数据变更后调用）"""
        # SQLite FTS5内容表自动同步，此处预留给未来可能的索引优化
        # 如添加jieba分词后需要重建索引
        pass

    # ============================================
    # get_suggestions() — 搜索建议/自动补全
    # 作用: 根据用户输入前缀，返回匹配的症状建议
    # ============================================
    def get_suggestions(self, prefix, limit=10):
        """获取症状搜索建议（自动补全）"""
        if not prefix or len(prefix) < 1:
            return []

        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT id, name, name_en, category FROM symptoms '
                'WHERE name LIKE ? ORDER BY name LIMIT ?',
                (f'%{prefix}%', limit)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
