-- Portfolio Backend Database Schema
-- Run this against fundmaster_db before starting the service

CREATE TABLE IF NOT EXISTS user_profile (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    phone           VARCHAR(20)   DEFAULT NULL COMMENT '手机号',
    email           VARCHAR(100)  DEFAULT NULL COMMENT '邮箱',
    phone_verified  TINYINT(1)    DEFAULT 0 COMMENT '手机已验证',
    email_verified  TINYINT(1)    DEFAULT 0 COMMENT '邮箱已验证',
    created_at      DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transactions (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    asset_type    VARCHAR(16)   NOT NULL COMMENT '资产类型: stock/fund/bond/crypto',
    asset_code    VARCHAR(20)   NOT NULL COMMENT '资产代码',
    asset_name    VARCHAR(100)  DEFAULT NULL COMMENT '资产名称(冗余,方便展示)',
    trans_type    VARCHAR(8)    NOT NULL COMMENT '交易方向: buy/sell',
    price         DECIMAL(16,8) NOT NULL COMMENT '成交单价',
    quantity      DECIMAL(16,4) NOT NULL COMMENT '数量(股/份/个)',
    fee           DECIMAL(12,2) DEFAULT 0.00 COMMENT '手续费',
    trans_date    DATE          NOT NULL COMMENT '交易日期',
    portfolio_tag VARCHAR(50)   DEFAULT NULL COMMENT '组合标签: 长线/短线/网格/定投',
    notes         TEXT          DEFAULT NULL COMMENT '用户备注',
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_asset (asset_type, asset_code),
    INDEX idx_date (trans_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS price_alert (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    asset_type          VARCHAR(16)   NOT NULL COMMENT 'stock/fund/bond/crypto',
    asset_code          VARCHAR(20)   NOT NULL COMMENT '资产代码',
    alert_type          VARCHAR(16)   NOT NULL COMMENT 'stop_profit/stop_loss/price_above/price_below',
    trigger_mode        VARCHAR(8)    NOT NULL COMMENT '触发模式: price(绝对值) / pct(百分比)',
    trigger_price       DECIMAL(16,8) DEFAULT NULL COMMENT '触发价格(trigger_mode=price)',
    trigger_pct         DECIMAL(8,4)  DEFAULT NULL COMMENT '触发百分比(trigger_mode=pct, 0.15=15%)',
    reference_trans_id  BIGINT        DEFAULT NULL COMMENT '关联买入交易ID,为空则基于加权均价',
    notify_phone        TINYINT(1)    DEFAULT 0 COMMENT '电话通知',
    notify_email        TINYINT(1)    DEFAULT 0 COMMENT '邮件通知',
    is_enabled          TINYINT(1)    DEFAULT 1 COMMENT '是否启用',
    notified_at         DATETIME      DEFAULT NULL COMMENT '上次触发通知时间',
    notes               TEXT          DEFAULT NULL,
    created_at          DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_asset (asset_type, asset_code),
    INDEX idx_enabled (is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS watchlist (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    asset_type    VARCHAR(16)   NOT NULL COMMENT 'stock/fund/bond/crypto',
    asset_code    VARCHAR(20)   NOT NULL COMMENT '资产代码',
    asset_name    VARCHAR(100)  DEFAULT NULL COMMENT '资产名称',
    target_price  DECIMAL(16,8) DEFAULT NULL COMMENT '目标买入价',
    priority      TINYINT       DEFAULT 0 COMMENT '优先级 0-5',
    notes         TEXT          DEFAULT NULL,
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_asset (asset_type, asset_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS allocation_target (
    asset_type  VARCHAR(16)   NOT NULL COMMENT '资产大类: stock/fund/bond/crypto',
    target_pct  DECIMAL(5,2)  NOT NULL COMMENT '目标占比(%)',
    updated_at  DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (asset_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
