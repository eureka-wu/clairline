#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空官方接口精简客户端 (LoongAir Client)
在获取到长龙 Authorization 后，主动轻量请求核心接口：
1. sales_user_userDetailInfo：获取姓名、实名状态、手机号、证件号
2. cardToC_getUnionCardList：获取畅飞卡授权 ID (scgTid) 与产品名称
(已根据用户需求彻底省略积分、卡包数、券包数等无关接口，极速完成)
"""

import json
import urllib.parse
from typing import Dict, Any, Optional
import requests

LOONGAIR_GATEWAY_URL = "https://www.loongair.cn/webhandler.ashx"

def _call_api(method: str, params: dict, headers: dict, timeout: float = 5.0) -> Optional[dict]:
    """统一调用长龙 webhandler.ashx 接口"""
    token = headers.get("authorization") or headers.get("Authorization") or ""
    cookie = headers.get("cookie") or headers.get("Cookie") or (f"SESSION={token}" if token else "")
    
    req_headers = {
        "User-Agent": headers.get("user-agent") or headers.get("User-Agent") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MicroMessenger/7.0.20",
        "Authorization": token,
        "Cookie": cookie,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": headers.get("referer") or headers.get("Referer") or "https://servicewechat.com/wx0a991d42d653886e/605/page-frame.html",
        "xweb_xhr": "1"
    }
    if "NESign" in headers:
        req_headers["NESign"] = headers["NESign"]
    if "X-App-Version" in headers:
        req_headers["X-App-Version"] = headers["X-App-Version"]
    
    payload = {
        "AppID": "ClientService",
        "MethodName": method,
        "Parameters": json.dumps(params, ensure_ascii=False)
    }
    body = "paras=" + urllib.parse.quote(json.dumps(payload, ensure_ascii=False))
    
    try:
        resp = requests.post(
            LOONGAIR_GATEWAY_URL,
            headers=req_headers,
            data=body,
            timeout=timeout,
            proxies={"http": None, "https": None}
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[LoongAirClient] 请求 {method} 提示: {e}")
    return None

def _safe_parse_result(res: Optional[dict]) -> Any:
    """安全解析长龙返回的 Result 字段 (转义 JSON 字符串)"""
    if not res or not isinstance(res, dict):
        return None
    raw_res = res.get("Result")
    if raw_res is None:
        return None
    if isinstance(raw_res, (dict, list)):
        return raw_res
    if isinstance(raw_res, str):
        raw_res = raw_res.strip()
        if (raw_res.startswith("{") and raw_res.endswith("}")) or (raw_res.startswith("[") and raw_res.endswith("]")):
            try:
                return json.loads(raw_res)
            except Exception:
                pass
        return raw_res
    return raw_res

def fetch_full_user_profile(headers: Dict[str, str]) -> Dict[str, Any]:
    """
    轻量快速获取会员核心档案与畅飞卡信息 (极速精简版)
    """
    profile: Dict[str, Any] = {
        "user_name": "长龙会员",
        "mobile": "",
        "member_level": "乘云会员",
        "cert_number": "",
        "card_name": "长龙畅飞卡",
        "encrypted_user_id": "",
        "sec_card_grant_tid": "",
        "is_verified": 0
    }
    
    default_params = {"SaleChannel": 76, "saleChannel": 76, "language": "zh-cn"}
    
    # 1. 核心接口：查询用户基本信息与实名认证状态
    detail_res = _call_api("sales_user_userDetailInfo", default_params, headers)
    detail_data = _safe_parse_result(detail_res)
    if isinstance(detail_data, dict):
        name = detail_data.get("Name") or detail_data.get("aliasName")
        if name:
            profile["user_name"] = str(name).strip()
            
        mobile = detail_data.get("Mobile")
        if mobile:
            profile["mobile"] = str(mobile).strip()
            
        foid = detail_data.get("Foid")
        if foid:
            profile["cert_number"] = str(foid).strip()
        elif detail_data.get("IDInfoList") and isinstance(detail_data["IDInfoList"], list) and len(detail_data["IDInfoList"]) > 0:
            profile["cert_number"] = detail_data["IDInfoList"][0].get("foid", "")
            
        enc_id = detail_data.get("encryptedUserId")
        if enc_id:
            profile["encrypted_user_id"] = str(enc_id).strip()
            
        if detail_data.get("ifReal") is True or detail_data.get("IsCertified") == 1 or detail_data.get("authFlg") is True:
            profile["is_verified"] = 1

        lvl = str(detail_data.get("Level", "1"))
        level_map = {"1": "乘云会员 (菁英卡)", "2": "银卡会员", "3": "金卡会员", "4": "白金卡会员"}
        profile["member_level"] = level_map.get(lvl, "乘云会员")

    # 2. 核心接口：查询畅飞卡授权 ID 与卡信息
    card_res = _call_api("cardToC_getUnionCardList", {"cardTypes": 0, "cardStatus": [0], "SaleChannel": 76, "saleChannel": 76, "language": "zh-cn"}, headers)
    card_data = _safe_parse_result(card_res)
    if isinstance(card_data, dict):
        cards = card_data.get("cardInfoList", [])
        if isinstance(cards, list) and len(cards) > 0:
            plus_info = cards[0].get("plusCard", {})
            if plus_info:
                p_name = plus_info.get("ppoPlusProductName")
                if p_name:
                    profile["card_name"] = str(p_name).strip()
                scg = plus_info.get("scgTid") or plus_info.get("ppgTid")
                if scg:
                    profile["sec_card_grant_tid"] = str(scg)
                if plus_info.get("psgName") and profile["user_name"] == "长龙会员":
                    profile["user_name"] = str(plus_info["psgName"]).strip()

    return profile


def send_sms_verify_code(mobile: str, check_param: str) -> dict:
    """
    请求长龙官方下发短信验证码
    :param mobile: 11位手机号
    :param check_param: 网易易盾验证通过后的 validate 凭据 (如带或不带 CN31_ 前缀)
    """
    if not mobile or len(mobile) != 11:
        return {"ok": False, "error": "请输入正确的11位手机号"}
    if not check_param:
        return {"ok": False, "error": "请先完成安全验证（点选/滑块）"}

    # 如果 validate 没有带 CN 区域前缀，自动补全长龙网易易盾的 CN31_ 区域标识
    if not check_param.startswith("CN"):
        check_param = f"CN31_{check_param}"

    params = {
        "checkParam": check_param,
        "verifyCodeType": 9,
        "mobile": mobile,
        "userLoginLog": {
            "channel": "WECHAT_MINI_PROGRAM",
            "deviceInfo": "microsoft,windows10",
            "clientInfo": "小程序",
            "appVersion": "2.4.77"
        },
        "SaleChannel": 76,
        "saleChannel": 76,
        "language": "zh-cn"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541721) XWEB/19027",
        "Referer": "https://servicewechat.com/wx0a991d42d653886e/605/page-frame.html",
        "X-App-Version": "2.4.77",
        "NESign": "[object Null]"
    }

    res = _call_api("/user/clientNoLogin/channel/getVerifyCode", params, headers)
    if not res:
        return {"ok": False, "error": "请求长龙官方短信接口网络超时"}

    err_code = res.get("ErrorCode")
    if err_code == 0:
        result_obj = _safe_parse_result(res)
        verify_id = ""
        if isinstance(result_obj, dict):
            verify_id = result_obj.get("verifyId", "")
        return {
            "ok": True,
            "message": "验证码已成功发送，请注意查收短信",
            "verifyId": verify_id
        }
    else:
        msg = res.get("message") or "发送验证码失败"
        return {"ok": False, "error": f"{msg} (代码: {err_code})"}


def login_by_mobile_code(mobile: str, code: str, verify_id: str) -> dict:
    """
    提交短信验证码完成登录，获取 loongairToken 并持久化入库
    """
    if not mobile or not code:
        return {"ok": False, "error": "手机号与验证码不能为空"}

    params = {
        "channelType": 4,
        "mobile": mobile,
        "code": code,
        "verifyId": verify_id or "",
        "userLoginLog": {
            "channel": "WECHAT_MINI_PROGRAM",
            "deviceInfo": "microsoft,windows10",
            "clientInfo": "小程序",
            "appVersion": "2.4.77"
        },
        "SaleChannel": 76,
        "saleChannel": 76,
        "language": "zh-cn"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541721) XWEB/19027",
        "Referer": "https://servicewechat.com/wx0a991d42d653886e/605/page-frame.html",
        "X-App-Version": "2.4.77",
        "NESign": "[object Null]"
    }

    res = _call_api("/user/clientNoLogin/channel/mobileCodeLogin", params, headers)
    if not res:
        return {"ok": False, "error": "登录请求超时或官方接口无响应"}

    err_code = res.get("ErrorCode")
    if err_code == 0:
        result_obj = _safe_parse_result(res) or {}
        loongair_token = result_obj.get("loongairToken", "")
        refresh_token = result_obj.get("refreshToken", "")
        encrypted_user_id = result_obj.get("encryptedUserId", "")

        if not loongair_token:
            return {"ok": False, "error": "长龙返回登录成功但缺少 loongairToken 凭据"}

        # 构造标准的会员请求 Header
        auth_headers = {
            "Authorization": loongair_token,
            "Cookie": f"SESSION={loongair_token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MicroMessenger/7.0.20",
            "xweb_xhr": "1",
            "Referer": "https://servicewechat.com/wx0a991d42d653886e/605/page-frame.html"
        }

        # 自动拉取会员姓名、身份证与卡资产
        remote_prof = fetch_full_user_profile(auth_headers)
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        profile = {
            "user_name": remote_prof.get("user_name") or "长龙会员",
            "mobile": mobile,
            "member_level": remote_prof.get("member_level") or "乘云会员",
            "cert_number": remote_prof.get("cert_number") or "",
            "token": loongair_token,
            "cookie": f"SESSION={loongair_token}",
            "card_name": remote_prof.get("card_name") or "长龙畅飞卡",
            "encrypted_user_id": remote_prof.get("encrypted_user_id") or encrypted_user_id,
            "sec_card_grant_tid": remote_prof.get("sec_card_grant_tid") or "",
            "is_verified": remote_prof.get("is_verified", 0),
            "refresh_token": refresh_token,
            "headers": auth_headers,
            "updated_at": now_str
        }

        import db
        db.save_user_profile(profile)

        try:
            from seccard_client import SecCardClient
            SecCardClient().check_and_reload()
        except Exception as e:
            print(f"[!] 热重载客户端提示: {e}")

        masked_mobile = profile["mobile"][:3] + "****" + profile["mobile"][-4:] if len(profile["mobile"]) == 11 else profile["mobile"]
        return {
            "ok": True,
            "message": f"欢迎回来，{profile['user_name']}！已自动绑定会员凭证与畅飞卡。",
            "user": {
                "user_name": profile["user_name"],
                "mobile": masked_mobile,
                "member_level": profile["member_level"],
                "card_name": profile["card_name"],
                "is_verified": profile["is_verified"],
                "update_time": now_str
            }
        }
    else:
        msg = res.get("message") or "验证码错误或已过期"
        return {"ok": False, "error": f"{msg} (代码: {err_code})"}


def refresh_access_token(refresh_token: str = "") -> dict:
    """
    使用持久化存储的 refreshToken 向长龙服务器无感换取新 loongairToken，
    实现“登录一次，长期有效”的自动续期机制。
    """
    import db
    from datetime import datetime
    prof = db.get_user_profile() or {}
    rt = refresh_token or prof.get("refresh_token") or ""
    if not rt:
        return {"ok": False, "error": "本地数据库缺少 refreshToken，无法自动续期"}

    params = {
        "refreshToken": rt,
        "token": prof.get("token") or "",
        "userId": prof.get("user_id") or "",
        "encryptedUserId": prof.get("encrypted_user_id") or "",
        "userLoginLog": {
            "channel": "WECHAT_MINI_PROGRAM",
            "deviceInfo": "microsoft,windows10",
            "clientInfo": "小程序",
            "appVersion": "2.4.77"
        },
        "SaleChannel": 76,
        "saleChannel": 76,
        "language": "zh-cn"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541721) XWEB/19027",
        "Referer": "https://servicewechat.com/wx0a991d42d653886e/605/page-frame.html",
        "X-App-Version": "2.4.77",
        "NESign": "[object Null]"
    }

    for method in ["/user/clientNoLogin/channel/refreshToken", "/user/client/channel/refreshToken"]:
        res = _call_api(method, params, headers, timeout=6.0)
        if res and res.get("ErrorCode") == 0:
            result_obj = _safe_parse_result(res) or {}
            new_token = result_obj.get("loongairToken") or result_obj.get("token")
            new_rt = result_obj.get("refreshToken") or rt
            if new_token:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                prof["token"] = new_token
                prof["cookie"] = f"SESSION={new_token}"
                prof["refresh_token"] = new_rt
                prof["updated_at"] = now_str
                if isinstance(prof.get("headers"), dict):
                    prof["headers"]["Authorization"] = new_token
                    prof["headers"]["Cookie"] = f"SESSION={new_token}"
                db.save_user_profile(prof)
                print(f"[+] 成功通过 refreshToken 自动续期 Token: {new_token[:10]}...")
                try:
                    from seccard_client import SecCardClient
                    SecCardClient().check_and_reload()
                except Exception:
                    pass
                return {"ok": True, "token": new_token, "refreshToken": new_rt}

    return {"ok": False, "error": "refreshToken 续期未通过或已完全失效"}

