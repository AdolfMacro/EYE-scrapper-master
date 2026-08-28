# EYES Master — Business Discovery Provider Strategy

**Document Status:** Architecture Decision / Provider Strategy
**Project:** EYES-master
**Date:** 2026-08-18

---

## 1. هدف اصلی

هدف EYES صرفاً Web Scraping نیست.

هدف اصلی:

> **شناسایی Business و POI واقعی بر اساس موقعیت جغرافیایی، با الزام وجود مختصات معتبر latitude / longitude.**

نمونه دسته‌ها:

* سوپرمارکت
* دکه
* فروشگاه
* پمپ بنزین
* داروخانه
* رستوران
* مدرسه
* بانک
* تعمیرگاه
* فروشگاه زنجیره‌ای
* سایر کسب‌وکارها و POIها

بنابراین مختصات جغرافیایی یک فیلد تزئینی نیست.

### قانون بنیادی

```text
No Coordinates = No Record
```

---

# 2. معماری اصلی

معماری EYES:

```text
GUI
 ↓
GUIController
 ↓
Master / ProcessManager
 ↓
ScraperProcess
 ↓
ScraperWorker
 ↓
ScraperEngine
 ↓
Provider
 ↓
Raw Results
 ↓
ScraperPipeline
 ↓
Validation
 ↓
Deduplication
 ↓
Database
```

GUI نباید مستقیماً با ProcessManager، ScraperProcess، Worker یا Engine کار کند.

مرز GUI:

```text
GUI
 ↓
GUIController
```

---

# 3. Child Scraper Contract

یکی از تصمیم‌های اصلی معماری:

> **هر Child Scraper دقیقاً یک Provider دارد.**

بنابراین:

```text
Google      → Child Scraper
Balad       → Child Scraper
Neshan      → Child Scraper
OSM         → Child Scraper
Overture    → Child Scraper
Geoapify    → Child Scraper
Foursquare  → Child Scraper
TomTom      → Child Scraper
HERE        → Child Scraper
DuckDuckGo  → Child Scraper
```

Master این Processها را مدیریت می‌کند.

این یعنی GUI نیز باید Childها را بر اساس همین قرارداد نمایش دهد.

---

# 4. Provider Strategy

## Tier A — Core Providers

### Google Places

نقش:

**Commercial POI Discovery**

داده‌های مهم:

* Place ID
* Name
* Category
* Address
* Latitude
* Longitude
* Text Search
* Nearby Search
* Place Details

وضعیت:

```text
CORE
```

---

### Balad

نقش:

**Iranian POI Provider**

مزایا:

* پوشش ایران
* داده محلی
* نام مکان
* دسته‌بندی
* آدرس
* مختصات

وضعیت:

```text
CORE / IRAN
```

---

### Neshan

نقش:

**Iranian Location / POI Provider**

مزایا:

* داده مکانی ایران
* جستجوی مکان
* POI
* مختصات
* آدرس

وضعیت:

```text
CORE / IRAN
```

---

### OpenStreetMap / Overpass

نقش:

**Open Data POI Provider**

مزایا:

* Open Data
* مختصات
* دسته‌بندی POI
* amenity
* shop
* fuel
* office
* و سایر tagها

وضعیت:

```text
CORE / OPEN DATA
```

برای حجم بالا نباید سرویس‌های عمومی OSM را تحت فشار قرار داد. برای Long-Running و Batch Processing استفاده از دیتای محلی، سرویس مناسب OSM-derived یا زیرساخت اختصاصی ترجیح دارد.

---

### Overture Maps

نقش:

**Open Geospatial / Batch Provider**

مزایا:

* POI در مقیاس بزرگ
* مختصات
* داده استانداردشده
* مناسب Batch Processing
* مناسب Geo Deduplication

وضعیت:

```text
CORE / BATCH
```

---

# 5. Tier B — Secondary Providers

### Geoapify

نقش:

**OSM-based POI / Geocoding**

وضعیت:

```text
SECONDARY
```

نکته:

Geoapify را منبع کاملاً مستقل از OSM حساب نمی‌کنیم.

---

### Foursquare

نقش:

**Commercial POI / Enrichment / Validation**

قابلیت‌های مهم:

* Place Search
* Place Details
* Place Match
* POI Discovery
* Location Data

وضعیت:

```text
SECONDARY / VALIDATION
```

---

### TomTom

نقش:

**POI / Search Provider**

قابلیت‌ها:

* Address Search
* POI Search
* Geometry Search
* Latitude
* Longitude

وضعیت:

```text
SECONDARY
```

---

### HERE

نقش:

**Search / Geocoding / POI**

قابلیت‌ها:

* POI Search
* Geocoding
* Reverse Geocoding
* Coordinates

وضعیت:

```text
SECONDARY
```

---

# 6. Tier C — Discovery

### DuckDuckGo

نقش:

**Web Discovery**

استفاده برای:

```text
Business Discovery
Website Discovery
Contact Discovery
Web Presence Discovery
```

DuckDuckGo منبع اصلی Location نیست.

اگر نتیجه مختصات معتبر نداشته باشد:

```text
REJECT
```

---

# 7. Provider Ranking

| Rank | Provider       | Type           | Coordinates | Role      |
| ---: | -------------- | -------------- | ----------- | --------- |
|    1 | Google Places  | Commercial POI | ✅           | Core      |
|    2 | Balad          | Iranian POI    | ✅           | Core      |
|    3 | Neshan         | Iranian POI    | ✅           | Core      |
|    4 | OSM / Overpass | Open POI       | ✅           | Core      |
|    5 | Overture Maps  | Open Dataset   | ✅           | Core      |
|    6 | Foursquare     | Commercial POI | ✅           | Secondary |
|    7 | TomTom         | Commercial POI | ✅           | Secondary |
|    8 | HERE           | Commercial POI | ✅           | Secondary |
|    9 | Geoapify       | OSM-based POI  | ✅           | Secondary |
|   10 | DuckDuckGo     | Web Discovery  | ⚠️          | Discovery |

---

# 8. Provider Responsibility

Provider فقط مسئول Discovery است.

```text
Provider
 ↓
Raw Data
```

Provider نباید تصمیم نهایی درباره ذخیره Business بگیرد.

Pipeline تصمیم می‌گیرد:

```text
RAW
 ↓
VALID?
 ├── NO  → REJECT
 └── YES
       ↓
   NORMALIZE
       ↓
   DEDUPLICATE
       ↓
      SAVE
```

---

# 9. Business Domain Model

مدل canonical:

```text
Business
```

مسئولیت:

* normalization
* validation
* identity
* serialization

Business نباید:

* SQLite را بشناسد
* Query دیتابیس اجرا کند
* Provider را بشناسد
* Scraping را کنترل کند
* Worker را مدیریت کند
* GUI Logic داشته باشد

حداقل قرارداد Persistence:

```text
name
latitude
longitude
```

هر سه باید معتبر باشند.

---

# 10. Minimum Data Contract

حداقل داده قابل قبول:

```text
name
latitude
longitude
```

داده‌های ترجیحی:

```text
name
category
province
city
latitude
longitude
source
source_id
address
phone
website
```

اما:

```text
address
phone
website
```

شرط ورود نیستند.

### شرط قطعی

```text
VALID NAME
+
VALID LATITUDE
+
VALID LONGITUDE
```

---

# 11. Geo-First Policy

مختصات باید توسط Provider ارائه شده باشند.

EYES در Discovery اصلی نباید این مسیر را به‌عنوان جایگزین مختصات استفاده کند:

```text
Address
 ↓
Geocoder
 ↓
Guessed Coordinates
 ↓
Save
```

اگر Provider خودش مختصات معتبر ارائه نکرد:

```text
REJECT
```

---

# 12. Coordinate Validation

Validation مرکزی:

```python
def valid_coordinates(latitude, longitude):
    if latitude is None:
        return False

    if longitude is None:
        return False

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return False

    if not -90 <= latitude <= 90:
        return False

    if not -180 <= longitude <= 180:
        return False

    if latitude == 0 and longitude == 0:
        return False

    return True
```

این منطق باید Single Source of Truth برای اعتبار مختصات باشد.

---

# 13. Pipeline

Pipeline:

```text
RAW
 ↓
Schema Validation
 ↓
Name Validation
 ↓
Coordinate Validation
 ↓
Province/City Normalization
 ↓
Category Normalization
 ↓
Source Metadata
 ↓
Geo Deduplication
 ↓
Provider Merge
 ↓
Database
```

Engine تصمیم نهایی Business را نمی‌گیرد.

---

# 14. Engine Responsibility

Engine مسئول:

```text
Query
Fetch
Provider Interaction
Raw Results
Extraction
```

Engine نباید تصمیم بگیرد:

```text
Business is valid
```

این تصمیم متعلق به Pipeline است.

---

# 15. Query Space

Query Generator باید بتواند:

```text
Province
 ↓
City
 ↓
Category
 ↓
Provider
```

را مدیریت کند.

مثال:

```text
آذربایجان شرقی
تبریز
سوپرمارکت
```

یا:

```text
تهران
تهران
پمپ بنزین
```

ساختار مفهومی:

```text
for province in provinces:

    for city in cities(province):

        for category in categories:

            run provider
```

---

# 16. Category Registry

دسته‌ها باید از Query Generator جدا باشند.

نمونه:

```text
سوپرمارکت
دکه
فروشگاه
پمپ بنزین
داروخانه
رستوران
کافه
نانوایی
بانک
خودپرداز
مدرسه
دانشگاه
بیمارستان
درمانگاه
تعمیرگاه
فروشگاه موبایل
فروشگاه پوشاک
فروشگاه مواد غذایی
```

Category Registry در آینده می‌تواند JSON/YAML شود.

---

# 17. Geo Deduplication

Deduplication نباید فقط بر اساس Name باشد.

ترکیب پیشنهادی:

```text
normalized_name
category
latitude
longitude
address
phone
source_id
```

Location Signature:

```text
normalized_name
+
rounded_latitude
+
rounded_longitude
```

برای تشخیص دقیق‌تر باید distance calculation نیز استفاده شود.

---

# 18. Multi-Provider Merge

هدف Providerهای متعدد تولید رکورد تکراری نیست.

هدف:

```text
Google ───┐
Balad ────┤
Neshan ───┤
OSM ──────┤
Overture ─┤
HERE ─────┤
TomTom ───┤
FSQ ──────┤
Geoapify ─┤
DDG ──────┘
           ↓
      SAME BUSINESS?
           ↓
       MERGE / SCORE
```

---

# 19. Provider Agreement

اگر چند Provider یک Business را تأیید کنند:

```text
Google
 +
Balad
 +
OSM
```

و مختصات نزدیک باشند:

```text
35.721230, 51.334560
35.721234, 51.334567
35.721228, 51.334574
```

Confidence افزایش پیدا می‌کند.

---

# 20. Confidence Metadata

برای آینده:

```text
source
source_id
provider_confidence
coordinate_confidence
match_confidence
```

مثلاً:

```text
source = google
coordinate_confidence = high
```

یا:

```text
source = osm
coordinate_confidence = medium
```

---

# 21. Data Quality Score

در آینده:

```text
Score =
    coordinate
    +
    name
    +
    category
    +
    address
    +
    phone
    +
    website
    +
    source agreement
```

اما Coordinate امتیاز اختیاری نیست.

```text
NO COORDINATE
    ↓
REJECT
```

---

# 22. Long-Running Scraper

EYES برای اجرای طولانی طراحی می‌شود:

```text
Province
 ↓
City
 ↓
Category
 ↓
Provider
 ↓
Pages / Queries
 ↓
Validation
 ↓
Deduplication
 ↓
Database
```

بنابراین این قابلیت‌ها ضروری هستند:

* Process isolation
* Monitor
* Graceful Stop
* Kill
* Restart
* Persistent Registry
* Per-scraper Database
* Per-scraper Log

---

# 23. Runtime Architecture

```text
Master
    ↓
ProcessManager
    ↓
ScraperProcess
    ↓
ScraperWorker
    ↓
ScraperEngine
    ↓
Provider
    ↓
ScraperPipeline
    ↓
Deduplication
    ↓
Database
```

---

# 24. ProcessManager

ProcessManager فقط مسئول:

```text
Lifecycle
Process
Restart
Stop
Kill
Join
Monitor
Registry Sync
```

---

# 25. ScraperProcess

مسئول:

```text
multiprocessing.Process
Bootstrap
PID
Exit Code
Start
Stop
Kill
Join
```

---

# 26. ScraperWorker

مسئول:

```text
Child Runtime
Provider Loading
RunContext
Health
Engine
Pipeline
```

---

# 27. ScraperEngine

مسئول:

```text
Query
Fetch
Provider Interaction
Raw Results
Extraction
Legacy / Current Scraping Flow
```

---

# 28. ScraperPipeline

مسئول:

```text
Validation
Normalization
Deduplication
Persistence
```

---

# 29. GUI Boundary

GUI نباید مستقیماً با Master internals کار کند.

Boundary رسمی:

```text
PyQt GUI
    ↓
GUIController
    ↓
ProcessManager
```

GUIController مسئول ارائه API ساده برای:

```text
Create
Start
Stop
Kill
Restart
Force Restart
Join
Wait
Status
Snapshot
List
Remove
Shutdown
```

همچنین:

```text
available_actions()
status_role()
status_text()
is_running()
is_starting()
is_stopping()
is_finished()
has_failed()
```

در اختیار GUI قرار می‌گیرد.

---

# 30. GUI Child Model

هر Child در GUI باید نماینده یک Provider باشد:

```text
Scraper #01
Provider: Google

Scraper #02
Provider: Balad

Scraper #03
Provider: Neshan
```

GUI نباید یک Child را با چند Provider نمایش دهد.

---

# 31. Provider Execution Model

اگر 10 Provider فعال باشند:

```text
10 Providers
     ↓
10 Child Scrapers
     ↓
ProcessManager
     ↓
Master
```

این مدل isolation، restart و monitoring مستقل برای هر Provider فراهم می‌کند.

---

# 32. Phase 1

```text
Provider Contract
 ↓
Business Model
 ↓
Coordinate Validator
 ↓
Pipeline Validation
```

---

# 33. Phase 2

```text
OSM
Balad
Neshan
```

---

# 34. Phase 3

```text
Google Places
Overture
Geoapify
```

---

# 35. Phase 4

```text
Foursquare
TomTom
HERE
```

---

# 36. Phase 5

```text
DuckDuckGo
```

---

# 37. Phase 6

```text
Geo Deduplication
Provider Agreement
Confidence Scoring
Provider Merge
```

---

# 38. Provider Strategy نهایی

Providerها صرفاً برای افزایش تعداد اضافه نمی‌شوند.

هر Provider باید حداقل یکی از این ارزش‌ها را داشته باشد:

1. POI Discovery
2. مختصات معتبر
3. پوشش جغرافیایی
4. پوشش کسب‌وکار
5. داده محلی ایران
6. منبع مستقل برای Cross-Validation

Providerهای هدف:

```text
01 Google Places
02 Balad
03 Neshan
04 OpenStreetMap / Overpass
05 Overture Maps
06 Geoapify
07 Foursquare
08 TomTom
09 HERE
10 DuckDuckGo
```

---

# 39. Architecture Decision

```text
10 Providers
+
1 Provider / Child Scraper
+
GUIController Boundary
+
Geo-First Pipeline
+
Coordinate Required
+
Central Validation
+
Geo Deduplication
+
Provider Cross-Validation
+
Persistent Per-Scraper Runtime
```

---

# 40. قانون نهایی EYES

```text
                 RAW RESULT
                     │
                     ▼
              Has X / Y ?
                /       \
              NO         YES
              │           │
            REJECT        ▼
                    Valid Range?
                     /       \
                   NO         YES
                   │           │
                 REJECT        ▼
                          NORMALIZE
                              ↓
                         DEDUPLICATE
                              ↓
                       PROVIDER MERGE
                              ↓
                           DATABASE
```

## EYES GEO-FIRST POLICY

> **No Coordinates = No Record**

بدون `latitude` و `longitude` معتبر، Business وارد دیتابیس نهایی EYES نمی‌شود.

---

## وضعیت معماری فعلی

**APPROVED / READY FOR NEXT IMPLEMENTATION PHASE**

```text
Business Model       → APPROVED
Provider Strategy    → APPROVED
Geo-First Policy     → APPROVED
Pipeline Direction   → APPROVED
Child/Provider Rule  → APPROVED
GUI Boundary         → APPROVED
GUIController        → READY
```

مرحله بعدی باید روی **Provider Contract + Pipeline Validation** برود، نه اضافه‌کردن بی‌قاعده Providerهای جدید.
