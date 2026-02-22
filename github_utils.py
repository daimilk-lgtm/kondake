import streamlit as st
import requests
import base64
import pandas as pd
import io

# ==============================================================================
# 【仕様定義書 / SPECIFICATIONS & USER REQUESTS】
# ------------------------------------------------------------------------------
# [2026/02/22] 物理分割と段階的更新ルールの導入
# - コードを app.py, auth_module.py, github_utils.py に分割。
# - 大規模な修正時は、AIが「ファイルごとの更新用プロンプト」を生成し、ユーザーが段階的に指示を出す運用をサポートする。
# - 各ファイルは、そのファイル内での「全文出力」を絶対ルールとする。
# ==============================================================================

REPO = "daimilk-lgtm/kondake"
TOKEN = st.secrets.get("GITHUB_TOKEN")

def get_github_content(filename):
    """GitHubからファイルを取得する汎用関数"""
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            return content, r.json()["sha"]
        else:
            return None, r.status_code
    except Exception as e:
        return None, str(e)

def save_to_github(content, filename, message, current_sha=None):
    """GitHubへファイルを保存する汎用関数"""
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code
