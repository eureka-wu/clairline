#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空官方接口客户端 (LoongAir Client - 官方 App 原生协议 SaleChannel: 8)
核心接口：
1. AccountService_GetPhoneVerifyCodeHandler：App 原生下发短信验证码并颁发预会话 Base64SessionID
2. sales_user_mobileLogin：App 原生短信登录，绑定长效 SESSION Cookie
3. sales_user_userDetailInfo：获取姓名、实名状态、手机号、证件号（兼作后台保活心跳）
4. cardToC_getUnionCardList：获取畅飞卡授权 ID (scgTid) 与产品名称
"""

import json
import uuid
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional
import requests

LOONGAIR_GATEWAY_URL = "https://www.loongair.cn/webhandler.ashx"

APP_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "Provider/finogeeks (iPhone; miniprogram; FinChat; runtimeSdkVersion/2.51.11)"
)

# 内存暂存手机号对应的短信预分配 SessionID（双保险配合前端 verifyId 回传）
_PENDING_SESSIONS: Dict[str, str] = {}


def get_device_info() -> str:
    """基于本机硬件特征哈希派生稳定的主流 iPhone 机型标识，兼顾一人一指纹与防风控聚集"""
    device_pool = [
        "iPhone<iPhone17,2>,ios18.4",
        "iPhone<iPhone17,1>,ios18.3",
        "iPhone<iPhone16,2>,ios18.2",
        "iPhone<iPhone16,1>,ios18.1",
        "iPhone<iPhone15,3>,ios17.6",
        "iPhone<iPhone15,2>,ios17.5",
    ]
    try:
        idx = uuid.getnode() % len(device_pool)
        return device_pool[idx]
    except Exception:
        return device_pool[0]


def build_app_headers(session_id: str = "") -> Dict[str, str]:
    """构造标准的长龙官方 iPhone App 请求头"""
    raw_token = session_id[len("SESSION="):] if session_id.startswith("SESSION=") else session_id
    cookie_val = f"SESSION={raw_token}" if raw_token else ""
    return {
        "Host": "www.loongair.cn",
        "Accept": "*/*",
        "AppVersion": "5.1.1",
        "SubVersion": "1.0.239",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "User-Agent": APP_USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_val,
        "Authorization": raw_token
    }


def _is_app_headers(headers: Dict[str, Any]) -> bool:
    if not headers or not isinstance(headers, dict):
        return True
    ua = str(headers.get("User-Agent") or headers.get("user-agent") or "")
    if "finogeeks" in ua.lower() or "iphone" in ua.lower() or any("appversion" in k.lower() for k in headers):
        return True
    return False


def _call_api(method: str, params: dict, headers: dict, timeout: float = 6.0) -> Optional[dict]:
    """统一调用长龙 webhandler.ashx 接口"""
    if _is_app_headers(headers):
        cookie = headers.get("cookie") or headers.get("Cookie") or ""
        token = headers.get("authorization") or headers.get("Authorization") or ""
        if not cookie and token:
            cookie = f"SESSION={token}" if not token.startswith("SESSION=") else token
        req_headers = {
            "Host": "www.loongair.cn",
            "Accept": "*/*",
            "AppVersion": str(headers.get("AppVersion") or "5.1.1"),
            "SubVersion": str(headers.get("SubVersion") or "1.0.239"),
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "User-Agent": headers.get("user-agent") or headers.get("User-Agent") or APP_USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Authorization": token,
            "Cookie": cookie,
        }
    else:
        token = headers.get("authorization") or headers.get("Authorization") or ""
        cookie = headers.get("cookie") or headers.get("Cookie") or (f"SESSION={token}" if token else "")
        req_headers = {
            "User-Agent": headers.get("user-agent") or headers.get("User-Agent") or APP_USER_AGENT,
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
        if resp.status_code in (200, 201):
            data = resp.json()
            if isinstance(data, dict):
                sess_cookie = resp.cookies.get("SESSION")
                if sess_cookie:
                    data["_set_cookie_session"] = sess_cookie
            return data
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
    轻量快速获取会员核心档案与畅飞卡信息 (自动适配 App 渠道 8 与旧版渠道 76)
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

    channel_id = 8 if _is_app_headers(headers) else 76
    default_params = {"SaleChannel": channel_id, "saleChannel": channel_id, "language": "zh-cn"}

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
    card_res = _call_api(
        "cardToC_getUnionCardList",
        {"cardTypes": 0, "cardStatus": [0], "SaleChannel": channel_id, "saleChannel": channel_id, "language": "zh-cn"},
        headers
    )
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
    通过长龙官方统一认证微服务 (/user/clientNoLogin/channel/getVerifyCode, SaleChannel: 8) 下发短信验证码
    """
    if not mobile or len(mobile) != 11:
        return {"ok": False, "error": "请输入正确的11位手机号"}
    if not check_param:
        return {"ok": False, "error": "请先完成安全验证（点选/滑块）"}

    if not check_param.startswith("CN"):
        check_param = f"CN31_{check_param}"

    params = {
        "checkParam": check_param,
        "verifyCodeType": 9,
        "mobile": mobile,
        "userLoginLog": {
            "channel": "APP",
            "deviceInfo": get_device_info(),
            "clientInfo": "App",
            "appVersion": "1.0.239"
        },
        "SaleChannel": 8,
        "saleChannel": 8,
        "language": "zh-cn"
    }
    headers = build_app_headers()

    res = _call_api("/user/clientNoLogin/channel/getVerifyCode", params, headers)
    if not res:
        return {"ok": False, "error": "请求长龙官方短信接口网络超时"}

    err_code = res.get("ErrorCode")
    if err_code == 0:
        result_obj = _safe_parse_result(res)
        verify_id = ""
        if isinstance(result_obj, dict):
            verify_id = result_obj.get("verifyId") or result_obj.get("Base64SessionID") or ""
        if not verify_id:
            verify_id = res.get("_set_cookie_session") or ""

        if verify_id:
            _PENDING_SESSIONS[mobile] = verify_id

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
    通过长龙官方统一认证微服务 (/user/clientNoLogin/channel/mobileCodeLogin, SaleChannel: 8) 完成验证码登录并持久化入库
    """
    if not mobile or not code:
        return {"ok": False, "error": "手机号与验证码不能为空"}

    pre_verify_id = (verify_id or _PENDING_SESSIONS.get(mobile) or "").strip()

    params = {
        "channelType": 4,
        "mobile": mobile,
        "code": code,
        "verifyId": pre_verify_id,
        "userLoginLog": {
            "channel": "APP",
            "deviceInfo": get_device_info(),
            "clientInfo": "App",
            "appVersion": "1.0.239"
        },
        "SaleChannel": 8,
        "saleChannel": 8,
        "language": "zh-cn"
    }
    headers = build_app_headers()

    res = _call_api("/user/clientNoLogin/channel/mobileCodeLogin", params, headers)
    if not res:
        return {"ok": False, "error": "登录请求超时或官方接口无响应"}

    err_code = res.get("ErrorCode")
    if err_code == 0:
        result_obj = _safe_parse_result(res) or {}
        if not isinstance(result_obj, dict):
            result_obj = {}

        base64_session_id = (
            result_obj.get("loongairToken")
            or result_obj.get("Base64SessionID")
            or res.get("_set_cookie_session")
            or ""
        )
        app_token = result_obj.get("refreshToken") or result_obj.get("token") or ""
        encrypted_user_id = result_obj.get("encryptedUserId") or ""

        if not base64_session_id:
            return {"ok": False, "error": "长龙返回登录成功但缺少 Session 凭据"}

        auth_headers = build_app_headers(base64_session_id)

        # 自动拉取会员姓名、身份证与畅飞卡资产
        remote_prof = fetch_full_user_profile(auth_headers)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        old_prof = {}
        try:
            import db
            old_prof = db.get_user_profile() or {}
        except Exception:
            pass

        scg_tid = remote_prof.get("sec_card_grant_tid") or old_prof.get("sec_card_grant_tid") or ""
        cert_num = remote_prof.get("cert_number") or old_prof.get("cert_number") or ""
        enc_uid = remote_prof.get("encrypted_user_id") or encrypted_user_id or old_prof.get("encrypted_user_id") or ""

        template = {
            "secCardGrantTid": str(scg_tid),
            "encryptedUserId": str(enc_uid),
            "certNumber": str(cert_num),
            "mobile": mobile,
            "disabilityIDType": 1,
            "ifNonCompany": False,
            "tripType": 1,
            "directionType": "",
            "bookingScenario": 1,
            "SaleChannel": 8,
            "saleChannel": 8,
            "language": "zh-cn"
        }

        profile = {
            "user_name": remote_prof.get("user_name") if remote_prof.get("user_name") != "长龙会员" else (old_prof.get("user_name") or "长龙会员"),
            "mobile": mobile,
            "member_level": remote_prof.get("member_level") or old_prof.get("member_level") or "乘云会员",
            "cert_number": cert_num,
            "token": base64_session_id,
            "cookie": f"SESSION={base64_session_id}",
            "card_name": remote_prof.get("card_name") if remote_prof.get("card_name") != "长龙畅飞卡" else (old_prof.get("card_name") or "长龙畅飞卡"),
            "encrypted_user_id": enc_uid,
            "sec_card_grant_tid": scg_tid,
            "is_verified": remote_prof.get("is_verified") or result_obj.get("IsCertified") or old_prof.get("is_verified") or 1,
            "refresh_token": app_token,
            "headers": auth_headers,
            "template": template,
            "updated_at": now_str
        }

        import db
        db.save_user_profile(profile)
        _PENDING_SESSIONS.pop(mobile, None)

        try:
            from seccard_client import SecCardClient
            SecCardClient().check_and_reload(force=True)
        except Exception as e:
            print(f"[!] 热重载客户端提示: {e}")

        masked_mobile = profile["mobile"][:3] + "****" + profile["mobile"][-4:] if len(profile["mobile"]) == 11 else profile["mobile"]
        return {
            "ok": True,
            "message": f"欢迎回来，{profile['user_name']}！已通过官方 App 协议绑定会员凭证与畅飞卡。",
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


def keepalive_session() -> dict:
    """
    向长龙网关发送轻量级心跳请求 (sales_user_userDetailInfo)，
    用于：
    1. 刷新长龙服务端 Redis Session 的闲置超时时间 (Idle Timeout)，防止因无操作被服务端踢下线；
    2. 实时探知当前 Session 在长龙服务端是否真正有效。
    """
    import db
    prof = db.get_user_profile() or {}
    token = prof.get("token") or ""
    if not token:
        return {"ok": False, "expired": False, "reason": "no_token"}

    headers = prof.get("headers") or build_app_headers(token)
    channel_id = 8 if _is_app_headers(headers) else 76
    params = {"SaleChannel": channel_id, "saleChannel": channel_id, "language": "zh-cn"}

    res = _call_api("sales_user_userDetailInfo", params, headers, timeout=6.0)
    if res is None:
        # 网络波动或超时，不误判为过期
        return {"ok": False, "expired": False, "reason": "network_timeout"}

    err_code = res.get("ErrorCode")
    if err_code == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prof["updated_at"] = now_str
        # 若服务端下发了新的 SESSION Cookie 则同步更新
        new_sess = res.get("_set_cookie_session")
        if new_sess and new_sess != token:
            prof["token"] = new_sess
            prof["cookie"] = f"SESSION={new_sess}"
            if isinstance(prof.get("headers"), dict):
                prof["headers"]["Cookie"] = f"SESSION={new_sess}"
        db.save_user_profile(prof)
        return {"ok": True, "expired": False}

    if err_code == 100001:
        ref = refresh_access_token()
        if ref.get("ok"):
            return {"ok": True, "expired": False, "refreshed": True}
        return {"ok": False, "expired": True, "error": "Session 已过期 (100001)"}

    return {"ok": False, "expired": False, "error": f"ErrorCode: {err_code}"}


def refresh_access_token(refresh_token: str = "") -> dict:
    """
    尝试使用持久化存储的 refreshToken 向长龙服务器换取新凭证
    """
    import db
    prof = db.get_user_profile() or {}
    rt = refresh_token or prof.get("refresh_token") or ""
    if not rt:
        return {"ok": False, "error": "本地数据库缺少 refreshToken，无法自动续期"}

    headers = prof.get("headers") or build_app_headers(prof.get("token") or "")
    channel_id = 8 if _is_app_headers(headers) else 76

    params = {
        "refreshToken": rt,
        "token": prof.get("token") or "",
        "userId": prof.get("user_id") or "",
        "encryptedUserId": prof.get("encrypted_user_id") or "",
        "userLoginLog": {
            "channel": "APP" if channel_id == 8 else "WECHAT_MINI_PROGRAM",
            "deviceInfo": get_device_info() if channel_id == 8 else "microsoft,windows10",
            "clientInfo": "App" if channel_id == 8 else "小程序",
            "appVersion": "1.0.239" if channel_id == 8 else "2.4.77"
        },
        "SaleChannel": channel_id,
        "saleChannel": channel_id,
        "language": "zh-cn"
    }

    for method in ["/user/clientNoLogin/channel/refreshToken", "/user/client/channel/refreshToken"]:
        res = _call_api(method, params, headers, timeout=6.0)
        if res and res.get("ErrorCode") == 0:
            result_obj = _safe_parse_result(res) or {}
            new_token = (
                result_obj.get("Base64SessionID")
                or result_obj.get("loongairToken")
                or result_obj.get("token")
                or res.get("_set_cookie_session")
            )
            new_rt = result_obj.get("refreshToken") or rt
            if new_token:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                prof["token"] = new_token
                prof["cookie"] = f"SESSION={new_token}"
                prof["refresh_token"] = new_rt
                prof["updated_at"] = now_str
                if isinstance(prof.get("headers"), dict):
                    if channel_id != 8:
                        prof["headers"]["Authorization"] = new_token
                    prof["headers"]["Cookie"] = f"SESSION={new_token}"
                db.save_user_profile(prof)
                print(f"[+] 成功通过 refreshToken 自动续期凭证: {new_token[:10]}...")
                try:
                    from seccard_client import SecCardClient
                    SecCardClient().check_and_reload(force=True)
                except Exception:
                    pass
                return {"ok": True, "token": new_token, "refreshToken": new_rt}

    return {"ok": False, "error": "refreshToken 续期未通过或已完全失效"}
