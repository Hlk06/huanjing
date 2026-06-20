@@
-# SQLALCHEMY_DATABASE_URI: SQLAlchemy连接字符串
-SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_FILE}'
+# SQLALCHEMY_DATABASE_URI: SQLAlchemy连接字符串
+# 优先使用环境变量 DATABASE_URL（用于云平台），未设置则回退到本地 sqlite 文件
+SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{DATABASE_FILE}')
@@
