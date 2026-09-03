# MP team — Видео контент түгээх, хэмжих платформ

Эмийн бүтээгдэхүүний видео/зураг/постер контентыг Microsoft Teams-ээр дамжуулан
1000+ ажилтанд (жор баригч, эмийн мэргэжилтэн) хүргэх, хандалт үзэлтийг бодит цагт
хэмжих, санал хүсэлт цуглуулах нэгдсэн платформ.

**Технологи:** Python 3.11+ · FastAPI · SQLite · Jinja2 · Chart.js
**Архитектур:** нэг monolithic project. Бүх файл (видео, зураг, cover) app server
дотор `app/storage/` дор хадгалагдана.

---

## Ажиллуулах

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

→ http://127.0.0.1:8000

Анх ажиллуулахад `app/data/app.db` автоматаар үүсч, **demo өгөгдөл** (13 хэрэглэгч,
8 бүтээгдэхүүн, 4 Teams channel, 12 контент, ~250 үзэлт) сууна. Цэвэрлэхийн тулд
`app/data/` болон `app/storage/` фолдерыг устгаад дахин асаана.

Орчны хувьсагч: `HOST`, `PORT`, `RELOAD=0`.

### Нэвтрэх (demo)

| Хэн | Хэрхэн |
|---|---|
| **Admin / Marketing Manager** | `Sign in with Microsoft` → `admin@monos.mn`, эсвэл mock формоор Эрх = Admin |
| **Viewer (жор баригч)** | Demo account сонгох, эсвэл ямар ч `@monos.mn` хаяг оруулах |

Mock горимд ямар ч нэр/мэйлээр нэвтрэхэд хэрэглэгч автоматаар үүснэ.
`@` тэмдэггүй бичвэл `@monos.mn` нэмэгдэнэ.

---

## Хэрэглэгчийн дүрүүд

| Дүр | Эрх |
|---|---|
| **Admin / Marketing Manager** | Контент байршуулах, ангилах, Teams channel-д илгээх, бүх dashboard, тайлан татах, хэрэглэгчийн эрх солих |
| **Viewer** | Контент үзэх, сэтгэгдэл/үнэлгээ өгөх, өөрийн профайл дээр түүхээ харах |

---

## Гол функцууд

### 1. Контент удирдлага — `/admin/content`
- Drag & drop upload (MP4, WEBM, MOV, JPG, PNG, WEBP, PDF · дээд тал нь 512MB)
- Байршуулахын өмнө **preview** харах
- Контент **2 хэсэгтэй**: `Жор баригч танд зориулсан бонус идэвхтэй бүтээгдэхүүн` / `Бусад контент`
- Бүтээгдэхүүнээр ангилах + чөлөөт tag систем
- Гарчиг, тайлбар, нийтлэх огноо, статус (нийтлэгдсэн / ноорог)
- Cover зураг оруулаагүй бол автоматаар gradient poster (SVG) үүснэ

### 2. Бүтээгдэхүүний жагсаалт — `/admin/products`
- Ганцаарчлан нэмэх
- **Excel (.xlsx) / CSV файлаас нэг дор импорт хийх** — 1-р багана нэр, 2-р код, 3-р чиглэл.
  Толгой мөр автоматаар танигдана, давхардсаныг алгасна. Загвар файл татах товчтой.

### 3. Teams-руу тараах — `/admin/distribute`
- Teams channel-ийн **холбоосыг гараар оруулж** бүртгэнэ (`/admin/channels`)
- Нэг контентыг **олон channel руу нэгэн зэрэг** илгээх (Бүгдийг сонгох товчтой)
- Шууд илгээх эсвэл **товлох** (scheduled) — дараа нь "Одоо илгээх"
- Илгээсэн огноо, статус (илгээгдсэн / төлөвлөгдсөн) харагдана

### 4. Хэмжилт, Dashboard — `/dashboard`
- **KPI:** нийт үзэлт, unique viewers, хамрах хүрээ %, нийт үзсэн цаг, дуустал үзсэн %,
  илгээсэн тоо, нэг хүнд ногдох үзэлт
- **Chart-ууд:** line (цаг хугацааны трэнд), horizontal bar (бүтээгдэхүүнээр),
  doughnut (хэсгийн харьцаа), bar (channel-аар), bar (өдрийн цагийн идэвх)
- **Хэрэглэгч × бүтээгдэхүүн матриц** — аль хэрэглэгч алийг их үзсэн (heat-cell)
- ТОП контент, ТОП идэвхтэй хэрэглэгчид
- **Filter:** огнооны хязгаар, бүтээгдэхүүн, Teams channel, хэсэг, трэндийн урт
- **CSV тайлан татах** (Excel-д кирилл зөв нээгддэг BOM-той)

### 5. Profile — `/profile`
- Үзсэн контентын түүх (огноо, нэр, хэдэн удаа, үзсэн хугацаа)
- Нийт үзэлт, үзсэн контент, сэтгэгдэл, минут
- 30 хоногийн хувийн идэвхийн график
- **Tier badge:** Starter → Bronze (10) → Silver (25) → Gold (50 үзэлт)
- Албан тушаал / салбар / хэлтэс / утсаа засах

### Үзэлт хэмжих механизм
- Контент нээх бүрд `views` хүснэгтэд мөр бичигдэнэ (хэн, юуг, хэзээ, ямар channel-аас, төхөөрөмж)
- Видеонд `timeupdate` бүр 10 секунд тутам үзсэн хугацаа, дууссан эсэх нь `/api/view/{id}/progress`-руу илгээгдэнэ
- Зураг/постерт хуудас хаагдах үед `sendBeacon`-оор үзсэн хугацаа бичигдэнэ
- Видео нь HTTP **Range** дэмждэг тул seek хийх боломжтой

---

## Нэвтрэлт: prototype → production

Одоо: `Sign in with Microsoft` товч demo Microsoft account сонгуулж нэвтрүүлнэ
(`/auth/microsoft`), эсвэл email + нэрээр mock login.

Production (Azure AD / Microsoft Entra ID) руу шилжихэд:

1. `app/auth.py` дээрх `MICROSOFT_SSO` тэмдэглэлийн блокт tenant/client утгаа бөглөнө.
2. `/auth/microsoft` route-ыг Azure authorize URL руу redirect болгож,
   `/auth/microsoft/callback` дээр код солилцоно (OAuth2 authorization code flow).
3. `resolve_microsoft_user()` дотор Graph `/me`-ээс ирсэн профайлыг буулгана —
   `displayName`, `mail`, `jobTitle` (албан тушаал), `officeLocation` (салбар), `department`.
4. Teams tab дотор: `microsoftTeams.authentication.getAuthToken()` → on-behalf-of flow.

Route болон template-үүд өөрчлөгдөхгүй — зөвхөн эдгээр функцийн дотор талыг сольно.

Teams-руу message бодитоор илгээхэд:
`POST /teams/{team-id}/channels/{channel-id}/messages` (Graph API) — `repo.distribute()`
дотор нэмнэ.

---

## Файлын бүтэц

```
run.py                    # хөгжүүлэлтийн сервер эхлүүлэх цэг
requirements.txt
app/
  config.py               # бүх зам, тогтмол, tier тохиргоо
  database.py             # SQLite схем + demo seed
  repo.py                 # бүх SQL нэг дор (PostgreSQL руу шилжихэд энэ давхарга л өөрчлөгдөнө)
  auth.py                 # session, mock login, Microsoft SSO цэг
  storage.py              # файл хадгалалт, Range стриминг, placeholder poster
  main.py                 # FastAPI route-ууд
  templates/              # Jinja2 (base, login, library, content, dashboard, profile, admin_*)
  static/css/style.css    # dark / neon design system
  static/js/app.js        # count-up, drag&drop, үзэлтийн явц бичих
  static/js/charts.js     # Chart.js тохиргоо
  storage/uploads/        # байршуулсан файлууд   (автоматаар үүснэ)
  storage/thumbs/         # cover зурагнууд        (автоматаар үүснэ)
  data/app.db             # SQLite                 (автоматаар үүснэ)
```

---

## Дараагийн түвшин (PostgreSQL)

Бүх SQL нь `app/repo.py` + `app/database.py`-д төвлөрсөн. Шилжихэд:

1. `database.py::connect()`-ыг `psycopg`-оор солино
2. Схемийн `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL/IDENTITY`,
   `?` placeholder → `%s`, `date('now', ...)` → `now() - interval '...'`
3. Файл хадгалалтыг S3 / Azure Blob руу гаргах бол `app/storage.py`-г л сольно

## UI

Dark gradient background, neon акцент (brand `#00e0a4`, cyan, violet, pink),
hover дээр өсдөг картууд, stat-д count-up анимаци, glow эффект.
Teams tab-аар нээгдэхийг тооцож бүрэн responsive (sidebar → burger цэс).
