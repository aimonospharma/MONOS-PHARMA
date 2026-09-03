# Засварлах жагсаалтын хариу — MP team

Аудитын жагсаалтын дагуу хийгдсэн зүйлс, үлдсэн ажил, тодруулга шаардсан
асуултууд. Код талын өөрчлөлт бүр commit-той холбоотой.

---

## 1. Аюулгүй байдал

### 1.1 Нэвтрэлт нээлттэй байсан ✅ ЗАССАН

| Хийсэн | Хаана |
|---|---|
| Формын `role` сонголтыг **бүрмөсөн устгасан**. Эрх нь DB + `ADMIN_EMAILS`-аас л тодорхойлогдоно | [app/auth.py](app/auth.py) `_resolve_role()`, [login.html](app/templates/login.html) |
| `/auth/microsoft` нь `DEMO_MODE=0` үед **404** буцаана | [app/auth.py](app/auth.py) `require_demo_mode()` |
| `DEMO_MS_ACCOUNTS` нь `DEMO_MODE=0` үед login дэлгэцэд **огт харагдахгүй** | [app/auth.py](app/auth.py) `demo_accounts()` |
| `DEMO_MODE` default нь **0** — аюулгүй тал руугаа | [app/config.py](app/config.py) |
| Production-д нэвтрэхэд `LOGIN_PASSWORD` шаардана (SSO хүртэлх түр хамгаалалт) | [app/auth.py](app/auth.py) `check_password()` |
| Нэвтрэх бүрд сесс цэвэрлэгддэг (session fixation) | `login_session()` |
| Нууц үгийг `hmac.compare_digest`-ээр харьцуулна (timing attack) | `check_password()` |

> **Анхаарах:** `LOGIN_PASSWORD` нь бүх хүнд нэг ижил нууц үг — түр арга хэмжээ.
> Хүн бүрийг ялгаж таних, гарсан ажилтны эрхийг хаах боломж Entra ID SSO
> залгагдсаны дараа л бүрдэнэ. Үүнийг эрэмбийн дараагийн ажил гэж үзэж байна.

### 1.2 SECRET_KEY ✅ КОД ТАЛААС ЗАССАН — тохиргоо танай талд

Апп нь одоо production дээр `SECRET_KEY`, `LOGIN_PASSWORD`, `ADMIN_EMAILS`
дутуу бол **зориудаар эхлэхгүй** ба шалтгааныг лог дээр бичнэ. Чимээгүй
эмзэг байдалтай ажиллахаас сэргийлсэн.

Dokploy → Environment:
```
SECRET_KEY=<openssl rand -hex 32>
SESSION_HTTPS_ONLY=1
DEMO_MODE=0
LOGIN_PASSWORD=<нууц үг>
ADMIN_EMAILS=<admin хаягууд, таслалаар>
PUBLIC_BASE_URL=https://mpteam.lab.coremind.mn
```

### 1.3 Бодит webhook оруулахгүй ✅ ОЙЛГОСОН

Одоогийн кодод бодит webhook URL байхгүй. Дээрх аюулгүй байдлын тохиргоо
хийгдэж, та нар зөвшөөрсний дараа л оруулна.

---

## 2. Өгөгдөл устах эрсдэл

### 2.1 Volume ⚠️ КОД БЭЛЭН — **үйлдэл танай талд**

`MP_DATA_DIR` / `MP_STORAGE_DIR`-г [config.py](app/config.py) аль хэдийн уншдаг.
Код өөрчлөх шаардлагагүй. Дараах дарааллаар хийнэ үү:

1. **Backup эхлээд гаргах** (одоогийн DB + видеонууд)
2. Dokploy → Volumes → mount path `/data`
3. Environment: `MP_DATA_DIR=/data/db`, `MP_STORAGE_DIR=/data/storage`
4. Deploy → өгөгдөл үлдэж байгааг шалгах

> Энэ хийгдэх хүртэл **git push хийхээс татгалзана уу** — одоогийн ~207MB
> видео устана.

### 2.2 Видеог git-д оруулахгүй ✅ БАТАЛГААЖСАН

`.gitignore` дээр `app/storage/`, `app/data/` байгаа. `git ls-files`-аар
шалгахад аль нь ч tracked биш.

### 2.3 PostgreSQL 📋 ТӨЛӨВЛӨГДСӨН

Бүх SQL нь [app/repo.py](app/repo.py) + [app/database.py](app/database.py)-д
төвлөрсөн. Шилжихэд `connect()`, placeholder (`?`→`%s`), `AUTOINCREMENT`,
`date('now',…)` гэсэн 4 зүйл л өөрчлөгдөнө. 1000+ хэрэглэгчтэй болохоос өмнө
хийхийг зөвшөөрч байна.

---

## 3. Teams интеграц ✅ БИЧИГДСЭН

### 3.1 Бодитоор илгээдэг болсон

| Өмнө | Одоо |
|---|---|
| Зөвхөн DB-д "илгээсэн" гэж тэмдэглэдэг | Power Automate Workflow руу Adaptive Card **бодитоор POST** хийнэ |
| `webhook_url` хадгалагддаг ч уншигддаггүй | Илгээх бүрд уншиж ашиглана |
| HTTP client байхгүй | `httpx==0.28.1` нэмэгдсэн |

Шинэ файл: [app/teams.py](app/teams.py)

### 3.2 Webhook placeholder ✅ ЗАССАН

- Буруу `outlook.office.com/webhook/…` placeholder-г устгасан
- Power Automate Workflow URL-ийн жишээгээр солив
- Хуучин O365 Connector URL оруулбал систем **таньж татгалзана**
  (`teams.is_legacy_webhook()`), алдааны мессежээр шалтгааныг хэлнэ
- Channel формын дор 4 алхамт заавар нэмсэн
- Channel жагсаалтад **Webhook** багана нэмсэн: Тохирсон / Хуучин O365 / Оруулаагүй

### 3.3 Илгээх код

| Шаардлага | Хэрэгжилт |
|---|---|
| a) `httpx` | ✅ requirements.txt |
| b) Adaptive Card POST | ✅ `teams.build_card()` + `teams.send()` |
| c) `?channel=<id>` заавал | ✅ `teams.content_url()`. `/content/{cid}` route үүнийг уншиж `views.channel_id`-д бичдэг байсан — өөрчлөх шаардлагагүй байв |
| d) Үр дүн хадгалах, дахин оролдох | ✅ `distributions` дээр `error`, `attempts`, `last_try_at` багана нэмэгдсэн. "Дахин илгээх" товч |

Статусууд: `pending` → `sent` эсвэл `failed` (алдааны текстийг UI дээр
харуулна). Товлосон нь `scheduled` → "Болсон товлолтуудыг илгээх" товчоор.

> **Үлдсэн ажил:** товлосон илгээлтийг автоматаар явуулах scheduler одоогоор
> байхгүй — гараар товч дарж явуулна. Cron/APScheduler нэмэх эсэхийг
> шийдвэрлэнэ үү.

### 3.4 Хэмжилтийн хязгаарлалт ✅ ОЙЛГОСОН, УГ ЗАГВАРТ ТУСГАСАН

Карт дээр видео **тавихгүй** — зөвхөн "Үзэх" товч. Тайлбарыг түгээх хуудсан
дээр анхааруулга болгож харуулсан.

---

## 4. Техникийн цэвэрлэгээ

| # | Байдал |
|---|---|
| 4.1 GitHub token | Repo болон git remote дотор token **алга** (шалгасан). Dokploy-ийн clone-д шигдсэн байсан бол тэр нь платформын талын зүйл — цаашид `git remote set-url`-ээр token-гүй URL ашиглахыг анхаарна |
| 4.2 `.env.example` | ✅ [үүсгэсэн](.env.example) — бүх хувьсагч тайлбартай |
| 4.3 Upload хязгаар | ✅ `MAX_UPLOAD_MB` env-ээр тохируулдаг болсон. **Proxy талын `client_max_body_size`-г ижил утгаар тохируулна уу** — эсэхгүй бол хэрэглэгч шалтгаангүй 413 алдаа харна |

---

## 5. Бидний хариу / тодруулга шаардсан зүйлс

| # | Асуулт | Хариу |
|---|---|---|
| 5.1 | Production домэйн | Одоогоор `mpteam.lab.coremind.mn`. Эцсийн домэйныг та нар баталсны дараа `PUBLIC_BASE_URL` болон Entra redirect URI-д бичнэ. **Танай шийдвэр хүлээж байна** |
| 5.2 | Dev tenant | Бидэнд байхгүй. Entra SSO-г эхлүүлэхэд dev tenant эсвэл test app registration хэрэгтэй. **Танай талаас** |
| 5.3 | Аль channel-ууд | Одоогийн 4 channel нь demo өгөгдөл. Бодит жагсаалт **танай талаас** |
| 5.4 | Workflow үүсгэх ажилтан | Workflow нь үүсгэсэн хүний эрхээр ажилладаг тул **албаны нэгдсэн бүртгэл** ашиглахыг зөвлөж, UI дээр ч тайлбарласан. Хэн болохыг **та нар шийднэ** |

---

## Deploy хийхийн өмнөх шалгах хуудас

- [ ] Backup гаргасан (DB + видео)
- [ ] Volume `/data` үүсгэсэн
- [ ] `MP_DATA_DIR`, `MP_STORAGE_DIR` тохируулсан
- [ ] `SECRET_KEY` (64 тэмдэгт) тохируулсан
- [ ] `LOGIN_PASSWORD` тохируулсан
- [ ] `ADMIN_EMAILS` тохируулсан
- [ ] `DEMO_MODE=0`, `SESSION_HTTPS_ONLY=1`
- [ ] `PUBLIC_BASE_URL` тохируулсан
- [ ] Proxy-ийн upload хязгаар `MAX_UPLOAD_MB`-тай таарсан
- [ ] Deploy хийсний дараа өгөгдөл үлдсэнийг шалгасан
- [ ] Нэвтрэхэд нууц үг шаардаж байгааг шалгасан
- [ ] `/auth/microsoft` нь 404 буцааж байгааг шалгасан
