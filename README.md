# 家映合规站

这是家映的公开产品、隐私政策和技术支持站点。站点使用纯 HTML/CSS，不使用 Cookie、分析服务、远程字体或第三方脚本。

家映 App 与服务端源码位于独立的私有仓库，本仓库只包含公开站点内容。

## 公开地址

- 中文首页：<https://cc1158.github.io/jiaying-site/>
- 中文隐私政策：<https://cc1158.github.io/jiaying-site/privacy/>
- 中文技术支持：<https://cc1158.github.io/jiaying-site/support/>
- English home: <https://cc1158.github.io/jiaying-site/en/>
- English privacy policy: <https://cc1158.github.io/jiaying-site/en/privacy/>
- English support: <https://cc1158.github.io/jiaying-site/en/support/>

## 本地预览

在仓库根目录运行：

```bash
python3 scripts/validate_site.py
python3 -m http.server 8000
```

然后打开 <http://localhost:8000/>。本地预览地址仅用于开发，不会被写入公开页面。

## GitHub Pages 发布

仓库使用 `main` 分支根目录发布 GitHub Pages。推送到 `main` 后，GitHub Pages 会自动构建静态文件。`.nojekyll` 确保带点目录和其他静态资源不会经过 Jekyll 处理。

GitHub Actions 会在每次推送和 Pull Request 中运行预览模式校验，检查页面语言、内部链接、安全约束和必需的隐私声明。

## App Store 提审前配置邮箱

当前源码包含 `SUPPORT_EMAIL_PENDING`，并在页面中说明邮件支持尚未开放。此状态可以发布预览站点，但不能用于 App Store 提审。

获得真实专用邮箱后：

1. 在中英文支持页和隐私政策联系段落中替换待开放文案。
2. 在中英文支持页各加入指向同一地址的有效 `mailto:` 链接。
3. 删除仓库中的所有 `SUPPORT_EMAIL_PENDING` 标记。
4. 验证邮箱能够实际收发邮件。
5. 先运行 `python3 scripts/validate_site.py`，再运行 `python3 scripts/validate_site.py --app-store-ready`。
6. 确认线上页面已经更新后，再把 Privacy Policy URL 与 Support URL 填入 App Store Connect。

`--app-store-ready` 会拒绝待配置标记、无效或不一致的邮箱，并检查六个公开页面和 GitHub Issues 支持入口是否可访问。

## 隐私与 Issue 内容

支持 Issue 是公开内容。模板会要求报告者不要提交密码、Token、真实服务器地址、设备标识或媒体名称。维护者发现敏感内容时应尽快隐藏或删除相关内容，并提醒报告者撤销已暴露的凭证。
