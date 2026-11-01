#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键从长龙官方服务器同步最新个人会员档案与资产信息
"""

import sys
import json
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import db
from loongair_client import fetch_full_user_profile

CRED_FILE = BACKEND_DIR / "data" / "credentials.json"

def sync_current_user_profile() -> dict:
    prof = db.get_user_profile() or {}
    token = prof.get("token") or ""
    headers = prof.get("headers") or {}
    
    if not token and not headers:
        return {"ok": False, "error": "当前未登录或数据库中缺少凭据，请先在客户端完成微信小程序嗅探登录"}
    
    if not headers and token:
        headers = {
            "Authorization": token,
            "Cookie": prof.get("cookie") or f"SESSION={token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MicroMessenger/7.0.20",
            "xweb_xhr": "1"
        }
        
    print(f"[*] 正在主动向长龙官方服务器查询会员全量档案 (Token: {token[:12]}...)...")
    try:
        remote_prof = fetch_full_user_profile(headers)
    except Exception as e:
        return {"ok": False, "error": f"请求长龙官方接口失败: {e}"}
        
    user_name = remote_prof.get('user_name') or prof.get('user_name') or "长龙会员"
    print(f"[+] 成功获取长龙会员档案: {user_name} | 等级: {remote_prof.get('member_level')} | 实名: {remote_prof.get('is_verified')}")
    
    # 彻底持久化存入 SQLite user_profile 表，废弃 credentials.json
    prof.update(remote_prof)
    prof["token"] = token
    prof["headers"] = headers
    try:
        db.save_user_profile(prof)
    except Exception as e:
        print(f"⚠️ 保存至 SQLite 失败: {e}")
    prof_db = {
        "user_name": prof.get("user_name") or "长龙会员",
        "mobile": prof.get("mobile") or "",
        "member_level": prof.get("member_level") or "乘云会员",
        "cert_number": prof.get("cert_number") or "",
        "token": token,
        "cookie": headers.get("cookie") or headers.get("Cookie") or "",
        "card_name": prof.get("card_name") or "长龙畅飞卡",
        "encrypted_user_id": prof.get("encrypted_user_id") or "",
        "sec_card_grant_tid": prof.get("sec_card_grant_tid") or "",
        "coupons_count": prof.get("coupons_count", 0),
        "cards_count": prof.get("cards_count", 0),
        "points": prof.get("points", 0),
        "is_verified": prof.get("is_verified", 0),
        "updated_at": prof.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    db.save_user_profile(prof_db)
    print("[+] 会员全量资料已成功持久化至 SQLite user_profile 表！")
    return {"ok": True, "profile": prof_db}

if __name__ == "__main__":
    res = sync_current_user_profile()
    print("Result:", json.dumps(res, ensure_ascii=False, indent=2))
