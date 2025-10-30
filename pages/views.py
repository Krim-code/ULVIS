import re
from django.shortcuts import get_object_or_404, render, redirect
from django.core.mail import send_mail
from django.http import FileResponse, Http404, HttpResponseBadRequest, JsonResponse
from .models import AboutSection, Category, ContactPage, GallerySection, HeroSlide, Lead, LeadSection, OfferPage, PrivacyPage, ReviewSection, USPSection
from django.contrib import messages
from .models import ru_phone_validator, Lead, LeadSection, HeroSlide, Category, USPSection, AboutSection, GallerySection, ReviewSection
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q


def get_contact_context():
    """Возвращает первый активный контакт, если есть"""
    page = ContactPage.objects.filter(is_active=True).first()
    tel_href = None
    if page and page.phone:
        import re
        digits = re.sub(r"\D+", "", page.phone)
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        if not digits.startswith("7"):
            digits = "7" + digits
        tel_href = f"+{digits}"
    return {"contact": page, "tel_href": tel_href}

def index(request):
    slides = HeroSlide.objects.filter(is_active=True).order_by("order", "id")
    categories = Category.objects.filter(is_active=True).order_by("order", "id")[:6]
    usp = USPSection.objects.filter(is_active=True).order_by("order","id").first()
    usp_items = usp.items.filter(is_active=True).order_by("order","id") if usp else []
    about = AboutSection.objects.filter(is_active=True).order_by("order","id").first()
    gallery = GallerySection.objects.filter(is_active=True).order_by("order", "id").first()
    gallery_images = gallery.images.filter(is_active=True).order_by("order","id") if gallery else []
    rev_sec = ReviewSection.objects.filter(is_active=True).order_by("order","id").first()
    reviews = rev_sec.reviews.filter(is_active=True) if rev_sec else []
    cta = LeadSection.objects.filter(is_active=True).order_by("order","id").first()
    steps = [
        {"num": 1, "text": "Вы оставляете заявку"},
        {"num": 2, "text": "Замер и проект"},
        {"num": 3, "text": "Изготовление и сборка"},
        {"num": 4, "text": "Доставка и гарантия"},
    ]

    success = request.GET.get("success")  # <-- флаг из урла
    
    ctx = {
        'slides': slides,
        "categories_db": categories,
        "usp": usp,
        "about": about,
        "usp_items": usp_items,
        "gallery": gallery,
        "gallery_images": gallery_images,
        "rev_sec": rev_sec,
        "reviews": reviews,
        "cta": cta,
        "success": success,    
        "steps": steps,       # <-- в шаблон
    }
    ctx.update(get_contact_context())
    return render(request, 'pages/index.html', ctx)


from django.http import JsonResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib import messages

from .models import Lead, ru_phone_validator
from .bitrix import send_lead_to_bitrix, normalize_phone_ru

def _throttle_hit(key: str, limit: int, ttl: int) -> bool:
    """
    инкрементит счётчик key с TTL. True = превышено.
    """
    try:
        added = cache.add(key, 1, ttl)  # если ключа нет — создаст со значением 1
        if added:
            return False
        # если уже есть — инкрементим
        val = cache.incr(key)
        return val > limit
    except Exception:
        # на всякий пожарный — не душим юзера, если кеш лёг
        return False

def _throttle_guard(ip: str, phone: str) -> tuple[bool, str]:
    """
    True/err — троттл сработал. Лимиты: IP 3/мин, 15/час; телефон 2/мин, 6/час
    """
    ip = ip or "0.0.0.0"
    phone_key = "".join(ch for ch in (phone or "") if ch.isdigit()) or "na"

    # лимиты
    limits = [
        (f"lead:ip:{ip}:m",   3,   60,   "Слишком часто. Попробуйте через минуту."),
        (f"lead:ip:{ip}:h",   15,  3600, "Превышен лимит. Попробуйте позже."),
        (f"lead:ph:{phone_key}:m", 2,   60,   "Слишком много попыток с этого номера."),
        (f"lead:ph:{phone_key}:h", 6,   3600, "Лимит обращений по номеру исчерпан."),
    ]
    for key, limit, ttl, msg in limits:
        if _throttle_hit(key, limit, ttl):
            return True, msg
    return False, ""

def lead_submit(request):
    if request.method != "POST":
        return redirect(reverse("index") + "#lead")

    # honeypot
    if (request.POST.get("website") or "").strip():
        # молча прикидываемся успехом
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        messages.success(request, "Заявка принята.")
        return redirect(reverse("index") + "?success=1#lead")

    name = (request.POST.get("name") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    message = (request.POST.get("message") or "").strip()
    src = (request.POST.get("source") or "").strip()

    # троттлинг
    ip = request.META.get("REMOTE_ADDR")
    throttled, tmsg = _throttle_guard(ip, phone)
    if throttled:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": tmsg}, status=429)
        messages.error(request, tmsg)
        return redirect(reverse("index") + "#lead")

    # валидация телефона
    try:
        ru_phone_validator(phone)
    except ValidationError as e:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": e.message}, status=400)
        messages.error(request, "Неверный номер: " + e.message)
        return redirect(reverse("index") + "#lead")

    # собираем utm
    utm = {
        "utm_source":   request.GET.get("utm_source","")   or request.COOKIES.get("utm_source",""),
        "utm_medium":   request.GET.get("utm_medium","")   or request.COOKIES.get("utm_medium",""),
        "utm_campaign": request.GET.get("utm_campaign","") or request.COOKIES.get("utm_campaign",""),
        "utm_content":  request.GET.get("utm_content","")  or request.COOKIES.get("utm_content",""),
        "utm_term":     request.GET.get("utm_term","")     or request.COOKIES.get("utm_term",""),
    }

    # пишем в БД
    lead = Lead.objects.create(
        name=name,
        phone=phone,
        message=message,
        utm_source=utm["utm_source"],
        utm_medium=utm["utm_medium"],
        utm_campaign=utm["utm_campaign"],
        referer=request.META.get("HTTP_REFERER",""),
        ip=ip,
        source=src,
    )

    # пушим в битрикс (не роняем UX, если битра офнулась)
    ok, err = send_lead_to_bitrix(
        name=name,
        phone=phone,
        message=message,
        utm=utm,
        source=src or f"site:{request.get_host()}",
        referer=request.META.get("HTTP_REFERER",""),
    )
    if not ok:
        # добавим отметку в заметку лида (если есть поле)
        try:
            lead.admin_note = (lead.admin_note or "") + f"\n[BITRIX FAIL] {err}"
            lead.save(update_fields=["admin_note"])
        except Exception:
            pass

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    messages.success(request, "Заявка принята. Перезвоним.")
    return redirect(reverse("index") + "?success=1#lead")


def catalog(request):
    q = (request.GET.get("q") or "").strip()
    qs = Category.objects.filter(is_active=True)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(slug__icontains=q))

    qs = qs.order_by("order", "id")
    paginator = Paginator(qs, 12)  # по 12 категорий на страницу
    page_obj = paginator.get_page(request.GET.get("page"))
    cta = LeadSection.objects.filter(is_active=True).order_by("order","id").first()
    ctx = {
        "cta": cta,
        "q": q,
        "page_obj": page_obj,
        "categories": page_obj.object_list,
        "meta_title": "Каталог — ULVIS",
        "meta_description": "Каталог категорий: кухни, шкафы, гардеробные, столы и другое. Индивидуальные проекты ULVIS.",
    }
    ctx.update(get_contact_context())
    return render(request, "pages/catalog_list.html", ctx)

def category_detail(request, slug):
    cta = LeadSection.objects.filter(is_active=True).order_by("order","id").first()
    category = get_object_or_404(Category, slug=slug, is_active=True)
    photos = category.photos.filter(is_active=True).order_by("order","id")
    ctx = {
        "cta": cta,
        "category": category,
        "photos": photos,
        "meta_title": category.meta_title or f"{category.title} — Каталог",
        "meta_description": category.meta_description or (category.description[:150] if category.description else ""),
    }
    ctx.update(get_contact_context())
    return render(request, "pages/category_detail.html", ctx)


def contacts(request):
    cta = LeadSection.objects.filter(is_active=True).order_by("order","id").first()
    page = ContactPage.objects.filter(is_active=True).first()

    tel_href = None
    if page and page.phone:
        # выкинуть всё кроме цифр
        digits = re.sub(r"\D+", "", page.phone)
        # нормализуем под РФ
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        if not digits.startswith("7"):
            # если как-то вообще без кода — принудительно +7
            digits = "7" + digits
        tel_href = f"+{digits}"
    ctx = {
        "cta": cta,
        "page": page,
        "tel_href": tel_href,
    }
    ctx.update(get_contact_context())
    return render(request, "pages/contacts.html", ctx)



def offer_page(request):
    offer = OfferPage.objects.filter(is_active=True).first()
    if not offer or not offer.file:
        raise Http404("Файл оферты не найден")

    return FileResponse(
        offer.file.open("rb"),
        as_attachment=False,  # если хочешь — True, чтобы сразу скачивался
        filename=offer.file.name.split("/")[-1],
    )


def privacy_page(request, slug="privacy"):
    page = PrivacyPage.objects.filter(is_active=True, slug=slug).first()
    if not page:
        raise Http404("Политика не найдена")
    ctx = {"page": page}
    ctx.update(get_contact_context())
    return render(request, "pages/privacy.html", ctx)

