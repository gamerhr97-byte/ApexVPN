# Shadow Box — سورس اصلاحی 0.10.1

این یک **تحویل سورس اصلاح‌شده** روی مبنای ZIP نسخهٔ 0.10.0 است، نه نصب‌کنندهٔ Windows. برای مشاهده تغییرات دقیق، فایل `CHANGELOG-0.10.1-FA.md` را بخوانید؛ برای محدودیت پروتکل‌ها، `PROTOCOL-SUPPORT-FA.md` را ببینید.

اجرای توسعه با Python و PySide6 مطابق `DEVELOPMENT.md` است. این فایل‌ها فاقد Python Runtime، Qt runtime، Xray باینری و فایل اجرایی ShadowBox.exe هستند. نصب یا به‌روزرسانی مستقیم نسخهٔ نصب‌شده با کپی‌کردن این ZIP **توصیه نمی‌شود**؛ پس از آماده‌سازی وابستگی‌ها باید نسخهٔ Windows را بسازید، روی سیستم آزمایشی امتحان کنید و ابتدا بکاپ داده‌ها را نگه دارید. اسکریپت NSIS قدیمیِ 0.7.0 هنوز برای انتشار کامل قابل اعتماد نیست.

آزمون مستقل: `python tools/check_v0101.py` (بدون Qt). آزمون جامع Qt/هسته: پس از نصب بسته‌ها و آماده‌سازی fixture‌ها طبق `DEVELOPMENT.md`، دستور `python -m pytest -q` را اجرا کنید. نام `NekoRayNext` در مسیر داده و هویت محافظت‌شده عمداً حفظ شده است.

اگر سیستم ویندوز دارید، برای build قابل نصب، ابتدا فایل‌های `tools/build_installer.py` و `tools/installer.nsi` را طبق یادداشت P0 در `PROJECT_HANDOFF.md` اصلاح و payload نهایی شامل `runtime/ShadowBoxHost.exe` و `runtime/ShadowBoxHost._pth` را روی Windows 11 تأیید کنید.
