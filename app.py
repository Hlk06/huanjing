# ============================================
# app.py — Flask主应用入口
# 作用:
#   1. 创建并配置Flask应用实例
#   2. 初始化数据库和扩展
#   3. 定义所有路由（页面路由 + API路由）
#   4. 应用启动时自动初始化预置数据
# 运行方式: python app.py
# ============================================

from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import db, Textbook, BodySystem, Disease, DiseaseInfo, Symptom, DiseaseSymptom
from config import (
    SECRET_KEY, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS,
    BODY_SYSTEMS_PRESET, INFO_TYPE_OPTIONS, LEVEL_OPTIONS, HOST, PORT, DEBUG
)
from search_engine import SearchEngine
from data_importer import DataImporter
from flask_frozen import Freezer
import os


# ============================================
# Flask应用工厂函数
# 作用: 创建并配置Flask应用，注册所有路由
# ============================================
def create_app():
    """创建Flask应用实例并完成所有初始化配置"""
    app = Flask(__name__)

    # --- Flask核心配置 ---
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    # JSON中文不乱码配置
    app.config['JSON_AS_ASCII'] = False

    # --- CORS支持 (uni-app HBuilderX跨域) ---
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE'
        return response

    # --- 初始化扩展 ---
    db.init_app(app)

    # --- 创建数据库表并插入预置数据 ---
    with app.app_context():
        db.create_all()               # 自动创建所有表（不会覆盖已有表）
        _init_preset_data()           # 插入人体系统等预置数据

    # --- 初始化搜索引擎 ---
    search_engine = SearchEngine()
    app.config['search_engine'] = search_engine

    # --- 初始化数据导入器 ---
    data_importer = DataImporter()
    app.config['data_importer'] = data_importer

    # ============================================
    # 页面路由（返回HTML页面）
    # ============================================

    @app.route('/')
    def index():
        """首页 - 仪表盘布局：统计+双板块+系统网格+最近知识点"""
        systems = BodySystem.query.order_by(BodySystem.sort_order).all()
        ug_count = Disease.query.filter_by(level='undergraduate').count()
        pg_count = Disease.query.filter_by(level='graduate').count()
        stats = {
            'textbook_count': Textbook.query.count(),
            'disease_count': Disease.query.count(),
            'disease_info_count': DiseaseInfo.query.count(),
            'symptom_count': Symptom.query.count(),
            'ug_count': ug_count,
            'pg_count': pg_count,
            'system_count': BodySystem.query.count(),
        }
        return render_template('index.html',
                               systems=systems,
                               ug_count=ug_count,
                               pg_count=pg_count,
                               stats=stats,
                               LEVEL_OPTIONS=LEVEL_OPTIONS)

    @app.route('/browse')
    @app.route('/browse/<int:system_id>')
    def browse(system_id=None):
        """按人体系统浏览疾病列表"""
        systems = BodySystem.query.order_by(BodySystem.sort_order).all()
        level_filter = request.args.get('level', 'all')  # all | undergraduate | graduate

        # 构建查询条件
        query = Disease.query
        if system_id:
            query = query.filter_by(system_id=system_id)
        if level_filter != 'all':
            query = query.filter_by(level=level_filter)

        diseases = query.order_by(Disease.name).all()
        current_system = BodySystem.query.get(system_id) if system_id else None

        return render_template('browse.html',
                               systems=systems,
                               diseases=diseases,
                               current_system=current_system,
                               current_level=level_filter,
                               LEVEL_OPTIONS=LEVEL_OPTIONS)

    @app.route('/disease/<int:disease_id>')
    def disease_detail(disease_id):
        """疾病详情页 - 显示完整知识体系（按K→L顺序排列: 解剖→生理→生化→病理→病生→发病机制→表现→诊断→检查→鉴别→分期→预防→治疗→预后）"""
        disease = Disease.query.get_or_404(disease_id)

        # 获取该疾病的全部info_type，按优先级排序
        type_order = {k: v['order'] for k, v in INFO_TYPE_OPTIONS.items()}

        # 从数据库获取所有info记录
        all_records = (DiseaseInfo.query
                       .filter_by(disease_id=disease_id)
                       .order_by(DiseaseInfo.id)
                       .all())

        # 按info_type分组
        infos = {}
        seen_types = set()
        for rec in all_records:
            if rec.info_type not in infos:
                infos[rec.info_type] = []
            infos[rec.info_type].append(rec)
            seen_types.add(rec.info_type)

        # 确保所有已配置类型都有条目（即使为空，用于Tab显示提示）
        for info_type in INFO_TYPE_OPTIONS:
            if info_type not in infos:
                infos[info_type] = []

        symptoms = disease.get_symptoms()
        return render_template('disease_detail.html',
                               disease=disease,
                               infos=infos,
                               symptoms=symptoms,
                               INFO_TYPE_OPTIONS=INFO_TYPE_OPTIONS,
                               LEVEL_OPTIONS=LEVEL_OPTIONS,
                               seen_types=seen_types)

    @app.route('/search')
    def search():
        """症状搜索页"""
        query = request.args.get('q', '')
        level = request.args.get('level', 'all')
        results = []
        if query:
            search_engine = app.config['search_engine']
            results = search_engine.search(query, level=level)
        return render_template('search.html',
                               query=query,
                               results=results,
                               current_level=level,
                               LEVEL_OPTIONS=LEVEL_OPTIONS)

    @app.route('/mindmap')
    @app.route('/mindmap/<int:system_id>')
    def mindmap(system_id=None):
        """思维导图页 — 系统→疾病→鉴别诊断层级可视化"""
        if system_id is None:
            system_id = request.args.get('system_id', type=int)
        systems = BodySystem.query.order_by(BodySystem.sort_order).all()
        return render_template('mindmap.html',
                               systems=systems,
                               current_system_id=system_id,
                               LEVEL_OPTIONS=LEVEL_OPTIONS,
                               INFO_TYPE_OPTIONS=INFO_TYPE_OPTIONS)

    @app.route('/literacy')
    def medical_literacy():
        """医学素养页 — 卫生法学+预防医学整合"""
        return render_template('literacy.html',
                               LEVEL_OPTIONS=LEVEL_OPTIONS)

    @app.route('/notepad')
    def notepad():
        """记事本 — 语音输入+手动记录+代办+知识点+错题"""
        return render_template('notepad.html', LEVEL_OPTIONS=LEVEL_OPTIONS)

    @app.route('/quiz')
    def quiz():
        """刷题模式 — 自组题+手动添加+答题评分"""
        return render_template('quiz.html', LEVEL_OPTIONS=LEVEL_OPTIONS)

    @app.route('/textbooks')
    def textbook_library():
        """教材图书馆 — 所有24本第10版教材展示"""
        import json, os
        lib_path = os.path.join(os.path.dirname(__file__), 'data', 'textbook_10th', 'organized', 'textbook_library.json')
        library = {'临床医学': [], '基础医学': [], '公共卫生与人文': []}
        if os.path.exists(lib_path):
            with open(lib_path, 'r', encoding='utf-8') as f:
                library = json.load(f)
        # Check which have Word/PDF
        word_dir = r"D:\第10版资料\word"
        pdf_dir = r"D:\第10版资料"
        word_files = set()
        pdf_files = set()
        if os.path.exists(word_dir):
            for f in os.listdir(word_dir):
                if f.endswith('.docx'):
                    word_files.add(f.replace('.docx','').replace('_',' '))
        for f in os.listdir(pdf_dir):
            if f.endswith('.pdf') and '目录校对' not in f:
                pdf_files.add(f.replace('.pdf',''))
        return render_template('textbooks.html',
                               library=library,
                               word_files=word_files,
                               pdf_files=pdf_files,
                               LEVEL_OPTIONS=LEVEL_OPTIONS)

    @app.route('/api/textbook/pages')
    def api_textbook_pages():
        """API: 获取教材提取页面"""
        import json, os
        name = request.args.get('name', '')
        if not name:
            return jsonify({'error': '缺少教材名参数'}), 400
        safe = name.replace(' ', '_').replace('/', '_')
        pages_dir = os.path.join(os.path.dirname(__file__), '_pages')
        # Try multiple filename patterns
        patterns = [f'{safe}_pages.json']
        for pat in [f'{safe}_.json', f'{safe}_pages.json']:
            # Check for files containing the safe name
            pass
        # Check directory for matching files
        found = None
        if os.path.exists(pages_dir):
            for f in os.listdir(pages_dir):
                if safe in f and f.endswith('_pages.json'):
                    found = os.path.join(pages_dir, f)
                    break
        if not found:
            return jsonify({'error': '未找到该教材的提取页面数据', 'pages': [], 'total': 0}), 404
        try:
            with open(found, 'r', encoding='utf-8') as f:
                pages = json.load(f)
            # Return first 50 pages as preview, rest as count
            preview = pages[:50] if len(pages) > 50 else pages
            result = {
                'total': len(pages),
                'preview': [{'n': p['n'], 't': p['t'][:500] if len(p.get('t', '')) > 500 else p.get('t', '')} for p in preview],
                'has_more': len(pages) > 50,
            }
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/differential/<int:disease_id>')
    def differential(disease_id):
        """鉴别诊断对比页 — 同系统疾病并排对比"""
        disease = Disease.query.get_or_404(disease_id)
        # 查找同系统下的兄弟疾病
        siblings = (Disease.query
                    .filter(Disease.system_id == disease.system_id)
                    .filter(Disease.id != disease_id)
                    .order_by(Disease.name)
                    .all())

        # 获取鉴别诊断内容
        diff_infos = (DiseaseInfo.query
                      .filter_by(disease_id=disease_id, info_type='differential_diagnosis')
                      .all())

        # 为每个兄弟疾病获取定义
        sibling_data = []
        for sib in siblings:
            def_info = (DiseaseInfo.query
                        .filter_by(disease_id=sib.id, info_type='definition')
                        .first())
            sibling_data.append({
                'disease': sib,
                'definition': def_info.content[:200] if def_info else '',
                'symptoms': sib.get_symptoms(),
            })

        return render_template('differential.html',
                               disease=disease,
                               siblings=sibling_data,
                               diff_infos=diff_infos,
                               LEVEL_OPTIONS=LEVEL_OPTIONS,
                               INFO_TYPE_OPTIONS=INFO_TYPE_OPTIONS)

    # ===== 新增: 原文页查看 & 最近知识点 =====
    @app.route('/page/<int:page_id>')
    def view_page(page_id):
        """查看教材原文页面"""
        from models import TextbookPage
        page = TextbookPage.query.get_or_404(page_id)
        return render_template('view_page.html', page=page)

    @app.route('/api/page/<int:page_id>')
    def api_page(page_id):
        """API: 获取单页原文"""
        from models import TextbookPage
        page = TextbookPage.query.get_or_404(page_id)
        result = page.to_dict()
        result['textbook'] = page.textbook.to_dict() if page.textbook else None
        return jsonify(result)

    @app.route('/api/recent-knowledge')
    def api_recent_knowledge():
        """API: 最近添加的知识点"""
        from models import KnowledgeRef
        limit = request.args.get('limit', 10, type=int)
        refs = (KnowledgeRef.query
                .order_by(KnowledgeRef.id.desc())
                .limit(limit)
                .all())
        return jsonify([r.to_dict() for r in refs])

    @app.route('/admin')
    def admin():
        """管理后台页"""
        return render_template('admin.html',
                               LEVEL_OPTIONS=LEVEL_OPTIONS,
                               INFO_TYPE_OPTIONS=INFO_TYPE_OPTIONS)

    # ============================================
    # API路由（返回JSON数据，供前端AJAX调用）
    # ============================================

    @app.route('/api/search')
    def api_search():
        """症状搜索API - 返回JSON格式的搜索结果"""
        query = request.args.get('q', '')
        level = request.args.get('level', 'all')
        if not query:
            return jsonify({'results': [], 'count': 0})
        search_engine = app.config['search_engine']
        results = search_engine.search(query, level=level)
        return jsonify({'results': results, 'count': len(results), 'query': query})

    @app.route('/api/symptoms')
    def api_symptoms():
        """获取所有症状列表 - 供搜索自动补全使用"""
        symptoms = Symptom.query.order_by(Symptom.name).all()
        return jsonify([s.to_dict() for s in symptoms])

    @app.route('/api/symptoms/search')
    def api_symptoms_search():
        """症状模糊搜索 - 供自动补全下拉框"""
        q = request.args.get('q', '')
        if not q:
            return jsonify([])
        symptoms = Symptom.query.filter(Symptom.name.like(f'%{q}%')).limit(10).all()
        return jsonify([s.to_dict() for s in symptoms])

    @app.route('/api/systems')
    def api_systems():
        """获取所有人体系统列表"""
        systems = BodySystem.query.order_by(BodySystem.sort_order).all()
        return jsonify([s.to_dict() for s in systems])

    @app.route('/api/systems/<int:system_id>/diseases')
    def api_system_diseases(system_id):
        """获取指定系统下所有疾病"""
        level = request.args.get('level', 'all')
        query = Disease.query.filter_by(system_id=system_id)
        if level != 'all':
            query = query.filter_by(level=level)
        diseases = query.order_by(Disease.name).all()
        result = []
        for d in diseases:
            item = d.to_dict()
            item['symptoms'] = d.get_symptoms()
            result.append(item)
        return jsonify(result)

    @app.route('/api/diseases/<int:disease_id>')
    def api_disease_detail(disease_id):
        """获取指定疾病的完整信息"""
        disease = Disease.query.get_or_404(disease_id)
        result = disease.to_dict()
        result['system'] = disease.system.to_dict() if disease.system else None
        result['symptoms'] = disease.get_symptoms()

        # 获取所有类型的信息条目
        infos = {}
        for info_type in INFO_TYPE_OPTIONS:
            records = (DiseaseInfo.query
                       .filter_by(disease_id=disease_id, info_type=info_type)
                       .all())
            infos[info_type] = [r.to_dict() for r in records]
        result['infos'] = infos
        return jsonify(result)

    # --- 管理后台API ---

    @app.route('/api/textbooks', methods=['GET', 'POST'])
    def api_textbooks():
        """教材管理API"""
        if request.method == 'POST':
            data = request.get_json()
            textbook = Textbook(**data)
            db.session.add(textbook)
            db.session.commit()
            return jsonify(textbook.to_dict()), 201
        textbooks = Textbook.query.order_by(Textbook.title).all()
        return jsonify([t.to_dict() for t in textbooks])

    @app.route('/api/textbooks/<int:book_id>', methods=['PUT', 'DELETE'])
    def api_textbook_manage(book_id):
        """单个教材的修改和删除"""
        textbook = Textbook.query.get_or_404(book_id)
        if request.method == 'PUT':
            data = request.get_json()
            for key, value in data.items():
                if hasattr(textbook, key):
                    setattr(textbook, key, value)
            db.session.commit()
            return jsonify(textbook.to_dict())
        elif request.method == 'DELETE':
            db.session.delete(textbook)
            db.session.commit()
            return jsonify({'message': '已删除'})

    @app.route('/api/diseases', methods=['GET', 'POST'])
    def api_diseases():
        """疾病管理API"""
        if request.method == 'POST':
            data = request.get_json()
            # 提取症状数据（从请求中分离）
            symptom_data = data.pop('symptoms', [])
            disease = Disease(**data)
            db.session.add(disease)
            db.session.flush()  # 获取disease.id

            # 创建疾病-症状关联
            for s in symptom_data:
                link = DiseaseSymptom(
                    disease_id=disease.id,
                    symptom_id=s['symptom_id'],
                    relevance=s.get('relevance', 'common')
                )
                db.session.add(link)
            db.session.commit()
            return jsonify(disease.to_dict()), 201

        system_id = request.args.get('system_id')
        level = request.args.get('level', 'all')
        query = Disease.query
        if system_id:
            query = query.filter_by(system_id=system_id)
        if level != 'all':
            query = query.filter_by(level=level)
        diseases = query.order_by(Disease.name).all()
        return jsonify([d.to_dict() for d in diseases])

    @app.route('/api/diseases/<int:disease_id>', methods=['PUT', 'DELETE'])
    def api_disease_manage(disease_id):
        """单个疾病的修改和删除"""
        disease = Disease.query.get_or_404(disease_id)
        if request.method == 'PUT':
            data = request.get_json()
            symptom_data = data.pop('symptoms', None)
            for key, value in data.items():
                if hasattr(disease, key):
                    setattr(disease, key, value)
            # 更新症状关联
            if symptom_data is not None:
                DiseaseSymptom.query.filter_by(disease_id=disease_id).delete()
                for s in symptom_data:
                    link = DiseaseSymptom(
                        disease_id=disease_id,
                        symptom_id=s['symptom_id'],
                        relevance=s.get('relevance', 'common')
                    )
                    db.session.add(link)
            db.session.commit()
            return jsonify(disease.to_dict())
        elif request.method == 'DELETE':
            db.session.delete(disease)
            db.session.commit()
            return jsonify({'message': '已删除'})

    @app.route('/api/disease-infos', methods=['GET', 'POST'])
    def api_disease_infos():
        """疾病详细信息管理API"""
        if request.method == 'POST':
            data = request.get_json()
            info = DiseaseInfo(**data)
            db.session.add(info)
            db.session.commit()
            # 重建搜索索引
            search_engine = app.config['search_engine']
            search_engine.rebuild_index()
            return jsonify(info.to_dict()), 201

        disease_id = request.args.get('disease_id')
        info_type = request.args.get('info_type')
        query = DiseaseInfo.query
        if disease_id:
            query = query.filter_by(disease_id=disease_id)
        if info_type:
            query = query.filter_by(info_type=info_type)
        infos = query.all()
        return jsonify([i.to_dict() for i in infos])

    @app.route('/api/disease-infos/<int:info_id>', methods=['PUT', 'DELETE'])
    def api_disease_info_manage(info_id):
        """单条疾病信息的修改和删除"""
        info = DiseaseInfo.query.get_or_404(info_id)
        if request.method == 'PUT':
            data = request.get_json()
            for key, value in data.items():
                if hasattr(info, key):
                    setattr(info, key, value)
            db.session.commit()
            search_engine = app.config['search_engine']
            search_engine.rebuild_index()
            return jsonify(info.to_dict())
        elif request.method == 'DELETE':
            db.session.delete(info)
            db.session.commit()
            search_engine = app.config['search_engine']
            search_engine.rebuild_index()
            return jsonify({'message': '已删除'})

    @app.route('/api/symptoms/manage', methods=['GET', 'POST'])
    def api_symptoms_manage():
        """症状管理API"""
        if request.method == 'POST':
            data = request.get_json()
            symptom = Symptom(**data)
            db.session.add(symptom)
            db.session.commit()
            return jsonify(symptom.to_dict()), 201
        symptoms = Symptom.query.order_by(Symptom.name).all()
        return jsonify([s.to_dict() for s in symptoms])

    @app.route('/api/symptoms/manage/<int:symptom_id>', methods=['PUT', 'DELETE'])
    def api_symptom_manage_single(symptom_id):
        """单个症状的修改和删除"""
        symptom = Symptom.query.get_or_404(symptom_id)
        if request.method == 'PUT':
            data = request.get_json()
            for key, value in data.items():
                if hasattr(symptom, key):
                    setattr(symptom, key, value)
            db.session.commit()
            return jsonify(symptom.to_dict())
        elif request.method == 'DELETE':
            db.session.delete(symptom)
            db.session.commit()
            return jsonify({'message': '已删除'})

    @app.route('/api/import', methods=['POST'])
    def api_import():
        """触发数据导入API"""
        importer = app.config['data_importer']
        try:
            result = importer.import_from_data_dir()
            # 导入后重建索引
            search_engine = app.config['search_engine']
            search_engine.rebuild_index()
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/upload-textbook', methods=['POST'])
    def api_upload_textbook():
        """上传电子书或Word文档，自动提取文本并导入。
        支持: PDF (.pdf) / Word (.docx)
        可选: 追加到已有教材 (append_to_existing)"""
        import re, os
        from werkzeug.utils import secure_filename

        UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        if 'file' not in request.files:
            return jsonify({'error': '未选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        # 检查文件类型
        allowed = {'.pdf', '.docx'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed:
            return jsonify({'error': f'不支持的文件类型: {ext}，仅支持PDF和Word文档'}), 400

        # 检查追加模式
        append_to = request.form.get('append_to_existing', '').strip()

        # 保存文件
        safe_name = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_DIR, safe_name)
        file.save(save_path)

        result = {
            'filename': safe_name,
            'file_size': os.path.getsize(save_path),
            'status': 'uploaded',
            'pages_extracted': 0,
            'textbook': None,
            'message': '',
        }

        # 提取文本
        import fitz  # pymupdf
        from docx import Document as DocxDocument

        extracted_text = []
        page_count = 0

        try:
            if ext == '.pdf':
                doc = fitz.open(save_path)
                page_count = len(doc)
                for i in range(page_count):
                    try:
                        txt = doc[i].get_text()
                        if txt and txt.strip():
                            extracted_text.append(f"## Page {i+1}\n\n{txt.strip()}")
                    except:
                        pass
                doc.close()
            elif ext == '.docx':
                doc = DocxDocument(save_path)
                for para in doc.paragraphs:
                    if para.text.strip():
                        extracted_text.append(para.text.strip())
                page_count = len(extracted_text)

            result['pages_extracted'] = page_count
        except Exception as e:
            result['status'] = 'extraction_failed'
            result['message'] = f'文本提取失败: {str(e)}'
            return jsonify(result), 422

        # 确定教材名
        textbook_name = append_to if append_to else re.sub(r'\s*第\d+版\s*', '', os.path.splitext(safe_name)[0]).strip()

        # 查找或创建教材
        existing = Textbook.query.filter_by(title=textbook_name).first()
        if not existing:
            textbook = Textbook(
                title=textbook_name,
                author=request.form.get('author', '').strip() or '待补充',
                edition=request.form.get('edition', '').strip() or '第10版',
                publisher='人民卫生出版社',
                level=request.form.get('level', 'undergraduate'),
            )
            db.session.add(textbook)
            db.session.commit()
            result['textbook'] = textbook.to_dict()
            result['message'] = f'已创建新教材: {textbook_name}'
        else:
            textbook = existing
            result['textbook'] = textbook.to_dict()
            result['message'] = f'已追加到已有教材: {textbook_name}'

        # 将提取的文本写入markdown文件供导入器使用
        md_path = os.path.join(UPLOAD_DIR, f"{safe_name}.md")
        md_content = f"""## 教材: {textbook_name}
作者: {textbook.author or '待补充'}
版次: {textbook.edition or '第10版'}
出版社: {textbook.publisher or '人民卫生出版社'}
年份: 2024
层次: undergraduate

## 上传内容 ({os.path.splitext(safe_name)[0]})

"""
        md_content += '\n\n'.join(extracted_text)

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # 自动导入内容
        try:
            importer = app.config['data_importer']
            importer.import_from_data_dir()
            search_engine = app.config['search_engine']
            search_engine.rebuild_index()
            result['message'] += ' | 已自动导入'
            result['status'] = 'imported'
        except Exception as e:
            result['message'] += f' | 导入失败: {str(e)}'
            result['status'] = 'extracted'

        return jsonify(result)

    @app.route('/api/stats')
    def api_stats():
        """获取统计数据"""
        return jsonify({
            'textbook_count': Textbook.query.count(),
            'system_count': BodySystem.query.count(),
            'disease_count': Disease.query.count(),
            'disease_info_count': DiseaseInfo.query.count(),
            'symptom_count': Symptom.query.count(),
            'ug_count': Disease.query.filter_by(level='undergraduate').count(),
            'pg_count': Disease.query.filter_by(level='graduate').count(),
        })

    @app.route('/api/mindmap-data')
    def api_mindmap_data():
        """思维导图数据API — 返回层级结构的JSON节点树
        支持参数: system_id (指定系统) 或 root=all (全部系统)
        节点层级: 人体系统 → 疾病 → 5类信息卡片
        """
        root = request.args.get('root', 'all')
        level = request.args.get('level', 'all')

        # 查询人体系统
        query = BodySystem.query.order_by(BodySystem.sort_order)
        if root != 'all':
            query = query.filter(BodySystem.id == int(root))
        systems = query.all()

        # 构建MindElixir格式的节点树
        root_node = {
            'id': 'root',
            'topic': '📚 人体系统',
            'expanded': True,
            'children': [],
        }

        for sys in systems:
            disease_query = Disease.query.filter_by(system_id=sys.id)
            if level != 'all':
                disease_query = disease_query.filter_by(level=level)
            diseases = disease_query.order_by(Disease.name).limit(30).all()

            sys_node = {
                'id': f'sys_{sys.id}',
                'topic': f'{sys.icon or "📋"} {sys.name}',
                'expanded': True,
                'direction': 'right',
                'children': [],
            }

            for dis in diseases:
                # 获取症状标签
                symptoms = dis.get_symptoms()
                symptom_tags = '、'.join([s['name'] for s in symptoms[:5]]) if symptoms else '暂无'

                # 获取定义摘要
                def_info = (DiseaseInfo.query
                            .filter_by(disease_id=dis.id, info_type='definition')
                            .first())

                # 获取鉴别诊断摘要
                diff_info = (DiseaseInfo.query
                             .filter_by(disease_id=dis.id, info_type='differential_diagnosis')
                             .first())

                overview = ''
                if def_info:
                    overview = def_info.content[:80]
                elif dis.overview:
                    overview = dis.overview[:80]

                dis_children = []
                # 添加5类信息作为子节点
                if def_info:
                    dis_children.append({
                        'id': f'def_{dis.id}',
                        'topic': f'📖 定义: {def_info.content[:50]}...',
                    })
                dis_children.append({
                    'id': f'sym_{dis.id}',
                    'topic': f'🏷️ 症状: {symptom_tags}',
                })
                if diff_info:
                    dis_children.append({
                        'id': f'diff_{dis.id}',
                        'topic': f'🔍 鉴别: {diff_info.content[:50]}...',
                    })

                dis_node = {
                    'id': f'dis_{dis.id}',
                    'topic': f'🏥 {dis.name}',
                    'expanded': False,
                    'href': f'/disease/{dis.id}',
                    'direction': 'right',
                    'children': dis_children,
                }

                if overview:
                    dis_node['topic'] += f'\n{overview[:60]}...'

                sys_node['children'].append(dis_node)

            root_node['children'].append(sys_node)

        return jsonify({'nodeData': root_node})

    return app


# ============================================
# _init_preset_data() — 预置数据初始化
# 作用: 应用首次启动或数据缺失时，自动插入人体系统等预置数据
# 使用"存在则跳过"策略，不会重复插入
# ============================================
def _init_preset_data():
    """初始化预置数据（仅在数据不存在时插入）"""
    # 插入人体系统
    for sys_data in BODY_SYSTEMS_PRESET:
        existing = BodySystem.query.filter_by(name=sys_data['name']).first()
        if not existing:
            db.session.add(BodySystem(**sys_data))
    db.session.commit()
    print(f'[初始化] 人体系统预置数据已就绪，共 {BodySystem.query.count()} 个系统')


# ============================================
# 应用启动入口
# ============================================

# 顶层 app 实例 — 供 Gunicorn / Vercel / 云部署使用
app = create_app()

if __name__ == '__main__':
    # 打印启动信息
    import socket
    lan_ip = '未知'
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except:
        pass
    print('=' * 60)
    print('  临床医学学习与复习软件 v1.0')
    print(f'  本地访问: http://127.0.0.1:{PORT}')
    if lan_ip != '未知':
        print(f'  手机访问: http://{lan_ip}:{PORT}')
    print(f'  数据库位置: {app.config["SQLALCHEMY_DATABASE_URI"]}')
    print('=' * 60)

    # 启动Flask开发服务器
    app.run(host=HOST, port=PORT, debug=DEBUG)
