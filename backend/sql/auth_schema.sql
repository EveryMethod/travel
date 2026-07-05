CREATE TABLE users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  display_name VARCHAR(80) NOT NULL COMMENT '用户展示名称',
  avatar_url VARCHAR(512) NULL COMMENT '用户头像地址',
  status ENUM('active', 'disabled') NOT NULL DEFAULT 'active' COMMENT '用户状态：active 正常，disabled 禁用',
  last_login_at DATETIME NULL COMMENT '最后登录时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  INDEX idx_users_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户主表';

CREATE TABLE user_password_credentials (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '账号密码凭据ID',
  user_id BIGINT UNSIGNED NOT NULL COMMENT '关联用户ID',
  email VARCHAR(255) NULL COMMENT '登录邮箱',
  username VARCHAR(64) NULL COMMENT '登录用户名',
  password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希值',
  password_algo VARCHAR(32) NOT NULL DEFAULT 'bcrypt' COMMENT '密码哈希算法',
  password_updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '密码更新时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_password_user_id (user_id),
  UNIQUE KEY uq_password_email (email),
  UNIQUE KEY uq_password_username (username),
  CONSTRAINT ck_password_email_or_username CHECK (email IS NOT NULL OR username IS NOT NULL),
  CONSTRAINT fk_password_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账号密码登录凭据表';

CREATE TABLE user_oauth_accounts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '第三方账号绑定ID',
  user_id BIGINT UNSIGNED NOT NULL COMMENT '关联用户ID',
  provider ENUM('qq', 'wechat') NOT NULL COMMENT '第三方登录平台：qq QQ，wechat 微信',
  provider_open_id VARCHAR(128) NOT NULL COMMENT '第三方平台 OpenID',
  provider_union_id VARCHAR(128) NULL COMMENT '第三方平台 UnionID',
  nickname VARCHAR(80) NULL COMMENT '第三方平台昵称',
  avatar_url VARCHAR(512) NULL COMMENT '第三方平台头像地址',
  raw_profile JSON NULL COMMENT '第三方平台原始用户资料',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_oauth_provider_open_id (provider, provider_open_id),
  KEY idx_oauth_user_id (user_id),
  KEY idx_oauth_provider_union_id (provider, provider_union_id),
  CONSTRAINT fk_oauth_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='第三方登录账号绑定表';

CREATE TABLE auth_sessions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '登录会话ID',
  user_id BIGINT UNSIGNED NOT NULL COMMENT '关联用户ID',
  refresh_token_hash VARCHAR(255) NOT NULL COMMENT '刷新令牌哈希值',
  user_agent VARCHAR(512) NULL COMMENT '登录设备 User-Agent',
  ip_address VARCHAR(45) NULL COMMENT '登录IP地址',
  expires_at DATETIME NOT NULL COMMENT '会话过期时间',
  revoked_at DATETIME NULL COMMENT '会话撤销时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_session_refresh_token_hash (refresh_token_hash),
  KEY idx_sessions_user_id (user_id),
  KEY idx_sessions_expires_at (expires_at),
  CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='登录会话表';

CREATE TABLE oauth_provider_configs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '第三方登录配置ID',
  provider ENUM('qq', 'wechat') NOT NULL COMMENT '第三方登录平台：qq QQ，wechat 微信',
  app_id VARCHAR(128) NOT NULL COMMENT '应用ID',
  app_secret VARCHAR(255) NOT NULL COMMENT '应用密钥',
  redirect_uri VARCHAR(512) NOT NULL COMMENT 'OAuth回调地址',
  enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用：1 启用，0 停用',
  scope VARCHAR(255) NULL COMMENT '授权范围',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_oauth_config_provider (provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='第三方登录应用配置表';
