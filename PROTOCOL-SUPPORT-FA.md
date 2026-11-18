> Current: Apex VPN 0.10.6. Installer EXE is the delivery; read README-0.10.6-FA.md and docs/VALIDATION-0.10.6-FA.md. Older sections are historical.

> Current: Apex VPN 0.10.5. Read README-0.10.5-FA.md and docs/VALIDATION-0.10.5-FA.md. Older sections are historical.

> Current release: Apex VPN 0.10.4. Read README-0.10.4-FA.md and docs/VALIDATION-0.10.4-FA.md first. Older sections below are historical.

# ماتریس پروتکل‌ها — 0.10.3

پشتیبانی در این سند به معنی مسیر parser/config/lifecycle است، نه تضمین کارکرد هر کانفیگ یا سرور. هسته sing-box 1.14.4 جدید است؛ فایل‌های آن با SHA-256 مشخص بسته‌بندی شده‌اند. بررسی کانفیگ‌های Hysteria2/TUIC/AnyTLS/SOCKS4 با خود هسته موفق بوده، ولی اجرای شبکه sing-box در میزبان آزمایش به دلیل محدودیت netlink ممکن نشده است. اتصال واقعی Xray با fixtureهای محلی آزموده شده است. اجرای Windows تأیید نشده است.

| ورودی/پروتکل | وضعیت فعلی |
|---|---|
| VLESS، VMess، Trojan، Shadowsocks | مسیر Xray موجود؛ زیرمجموعه پارامترهای شناخته‌شده، بدون حذف پنهانی فیلدهای URI |
| SOCKS5، HTTP Proxy، HTTPS Proxy | مسیر Xray موجود |
| SOCKS4 / SOCKS4a | مسیر جدید sing-box؛ کانفیگ با هسته بررسی شده |
| Hysteria2 / hy2 | مسیر اتصال sing-box اضافه شده؛ URI، TLS، SNI، ALPN، Salamander و up/down Mbps مشخص پشتیبانی می‌شوند؛ کانفیگ با هسته بررسی شده |
| Hysteria | مسیر sing-box؛ UDP، auth، obfs و upmbps/downmbps؛ بررسی واقعی ترافیک انجام نشده |
| TUIC | مسیر sing-box؛ UUID/password، TLS و گزینه‌های congestion/relay مشخص؛ کانفیگ با هسته بررسی شده |
| AnyTLS | مسیر sing-box برای password/TLS؛ کانفیگ با هسته بررسی شده |
| SSH Tunnel | مسیر sing-box؛ username/password و الزام host_key سنجاق‌شده؛ کلید/گزینه‌های پیچیده فقط در JSON مجازِ بررسی‌شده؛ ترافیک واقعی تست نشده |
| NaiveProxy | URIهای naive+https و naive+quic از مسیر sing-box؛ محدودیت‌های نسخه هسته اعمال می‌شوند؛ ترافیک واقعی تست نشده |
| WireGuard | فقط مسیر outbound در Xray JSON محدود و پارامترهای مورد قبول Xray؛ واردسازی عمومی wg:// و فایل WireGuard نداریم؛ ترافیک واقعی تست نشده |
| XHTTP، REALITY، gRPC، WS | انتقال/امنیت روی پروتکل‌های سازگار Xray، مطابق محدودیت‌های serializer موجود؛ VPN مستقل نیستند |
| Clash YAML | استخراج زیرمجموعه proxies به پروفایل مجزا؛ منبع کامل نگه داشته می‌شود. rules، listeners، scripts و alias/anchor اجرا نمی‌شوند. گزینه ناشناخته باعث رد واردسازی می‌شود |
| sing-box JSON | استخراج outbounds شناخته‌شده به پروفایل مستقل؛ source کامل حفظ می‌شود؛ مسیرهای فایل، detour و resolver سفارشی نیازمند بازبینی‌اند. routing/listeners فایل اجرا نمی‌شوند. endpointهای جدید OpenVPN/WireGuard در این مسیر تبدیل نشده‌اند |
| Xray JSON | JSON فقط با outbounds و log و یک proxy outbound مجاز، در wrapper امن اجرا می‌شود؛ فایل دارای routing/listeners سفارشی برای بازبینی نگه داشته شده و مستقیم اجرا نمی‌شود |
| HTTP/2 Proxy / QUIC Proxy | نام کلی کافی نیست؛ Naive+QUIC فقط مسیر خاص خودش را دارد. پشتیبانی عمومی این نام‌ها ادعا نمی‌شود |
| ShadowsocksR، Brook | آداپتور ندارند |
| OpenVPN، IKEv2/IPsec، L2TP/IPsec، SSTP، PPTP | آداپتور/یکپارچگی سیستم‌عامل و بازیابی مسیر ندارند؛ گزینه نمایشی «پشتیبانی‌شده» اضافه نشده است |
| NPV2 / NPV4 | فرمت رمزگذاری‌شده/وابسته به برنامه؛ decoder و مشخصات معتبر در پروژه نداریم |

## نکته لینک Hysteria2 ارسالی

لینک دارای `insecure=1` درخواست می‌کند گواهی سرور بررسی نشود. برنامه برای اینکه صرفاً «وصل شود» این کار را پنهانی انجام نمی‌دهد. تنظیم صریح **Allow insecure TLS profiles (unsafe)** در Security & Privacy پیش‌فرض خاموش است. با فعال‌کردن آگاهانه آن، آداپتور این درخواست را برای Hysteria2 اعمال می‌کند. روش بهتر، گواهی معتبر و SNI صحیح است. راز و نشانی خصوصی نمونه کاربر داخل سورس یا تست‌ها کپی نشده‌اند.

تست TCP برای Hysteria/TUIC/Hysteria2 که UDP هستند، نتیجه «UDP · HTTPS» نشان می‌دهد؛ به معنی نبود آداپتور نیست. برای آن‌ها تست HTTPS/کیفیت را انتخاب کنید.
