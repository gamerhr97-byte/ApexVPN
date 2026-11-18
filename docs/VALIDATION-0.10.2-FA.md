# اعتبارسنجی بازبینی 0.10.2

تاریخ: ۲۰۲۶-۱۰-۲۸. محیط Linux / Python 3.12 / PySide6 Essentials 6.8.3، QT_QPA_PLATFORM=offscreen. این گزارش جایگزین گزارش‌های تاریخی نیست.

- مجموعه انتخاب‌شده tests/test_v0102.py، test_profiles.py، test_subscriptions.py، test_settings.py، test_ui.py، test_presentation.py و test_v0100.py با کنارگذاشتن مورد نیازمند Xray واقعی: **۷۸ پاس، ۱ skip، ۱ deselected، ۱۶٫۴۹ ثانیه**. XML: test-results-v0102.xml.
- مورد skip: test_core_verified_local_install_and_rollback، به دلیل نبود آرشیو Linux هسته pinned.
- مورد deselected: test_real_default_ir_route_without_manually_enabling_exceptions. ابتدا اجرا شد و با FileNotFoundError برای core/xray شکست خورد؛ هیچ نتیجهٔ موفق اتصال واقعی برای آن ادعا نمی‌شود.
- tools/check_v0101.py: شش تست پاس. این تست‌ها mock و بدون شبکه عمومی‌اند.
- compileall برای app.py، nextapp و tests موفق.
- پنج regression جدید: تعداد/یکتایی ۲۰۰ مقصد و نام‌های درخواستی؛ امتیاز کامل ۲۰۰ سایت با proxy port ثابت و لغو؛ مرتب‌سازی/roundtrip امتیاز؛ پنجره ثابت و تغییر اندازه اختیاری همراه با نمایش ۱۰هزار پروفایل مصنوعی در صفحات ۱۰۰تایی؛ IP مستقیم، آیکون SVG و بازشدن پنل ۲۰۰سرویس.
- تست قدیمی test_ui که دریافت IP در حالت قطع را منع می‌کرد، مطابق درخواست جدید به تست صریح مسیر None و رد نتیجه VPN کهنه تبدیل شد. شبکه بیرونی در این آزمون mock است.
- بازبینی تصویری Qt offscreen: صفحه اصلی ۴۱۰×۶۵۰؛ پنل آیکونی سرویس‌ها؛ شیت ساب‌ها با quota/progress. رنگ متن انتخاب‌شده شیت پس از بازبینی اصلاح شد.
- در پایان یک جست‌وجوی خطی انتخاب بهترین نتیجه خودکار به lookup نگاشت تست تغییر یافت؛ صحت نحوی دوباره بررسی شد. این ریزتغییر پس از اجرای مجموعه بالا بود.

موارد تأییدنشده: Windows startup، WinINET واقعی، DPAPI واقعی، دقت تشخیص کشور Gemini برای حساب واردشده، زمان واقعی تست سرورها، endpointهای عمومی همه ۲۰۰ سرویس، reputation آی‌پی و پروتکل‌های بدون آداپتور. آیکون‌های جدید SVGهای اختصاصی برنامه‌اند، نه لوگوهای رسمی برندها.
